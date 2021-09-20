# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""

import time
import logging
import math
from threading import Lock

import numpy
import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, AttributeInfoEx
from tango.server import Device, attribute, command, pipe, device_property

from ET7000 import FakeET7000 as ET7000
# from ET7000 import ET7000
from TangoServerPrototype import TangoServerPrototype
from TangoUtils import config_logger

NaN = float('nan')

class ET7000_Server(TangoServerPrototype):
    server_version = '3.0'
    server_name = 'Tango Server for ICP DAS ET-7000 Series Devices'

    device_type = attribute(label="device_type", dtype=str,
                            display_level=DispLevel.OPERATOR,
                            access=AttrWriteType.READ,
                            unit="", format="%s",
                            doc="ET7000 device type. 0x0000 - unknown or offline")

    IP = attribute(label="IP", dtype=str,
                   display_level=DispLevel.OPERATOR,
                   access=AttrWriteType.READ,
                   unit="", format="%s",
                   doc="ET7000 device IP address")

    # all_ao = attribute(label="all_ao", dtype=float,
    #                    dformat=tango._tango.AttrDataFormat.SPECTRUM,
    #                    display_level=DispLevel.OPERATOR,
    #                    access=AttrWriteType.READ,
    #                    max_dim_x=256,
    #                    fget='read_all',
    #                    unit="", format="%f",
    #                    doc="Read all analog outputs")

    @command(dtype_in=(float,), dtype_out=(float,))
    def read_modbus(self, data):
        n = 1
        try:
            n = int(data[1])
            result = self.et.read_modbus(int(data[0]), n)
            # self.logger.debug('%s', result)
            if result:
                return result
            return [float('nan')] * n
        except:
            self.log_exception('read_modbus exception')
            return [float('nan')] * n

    @command(dtype_in=[float], dtype_out=bool)
    def write_modbus(self, data):
        self.logger.debug('%s', data)
        v = [0]
        a = 0
        try:
            a = int(data[0])
            v = [int(d) for d in data[1:]]
            result = self.et.write_modbus(a, v)
            # self.logger.debug('%s %s %s ', a, v, result)
            if result:
                return result
            return False
        except:
            # self.logger.debug('%s %s', a, v)
            self.log_exception('write_modbus exception')
            return False

    @command
    def reconnect(self):
        self.delete_device()
        self.init_device()
        self.add_io()
        msg = '%s Reconnected' % self.get_name()
        self.logger.info(msg)
        self.info_stream(msg)

    def init_device(self):
        if self in ET7000_Server.device_list:
            ET7000_Server.device_list.remove(self)
            self.delete_device()
        super().init_device()
        self.lock = Lock
        self.io_que = []
        self.async_time_limit = 0.2

    def set_config(self):
        super().set_config()
        self.attributes = {}
        self.et = None
        self.ip = None
        self.error_count = 0
        self.time = None
        self.reconnect_timeout = self.config.get('reconnect_timeout', 5000.0)
        self.show_disabled_channels = self.config.get('show_disabled_channels', False)
        self.set_state(DevState.INIT)
        # get ip from property
        ip = self.config.get('ip', '192.168.1.122')
        # check if ip is in use
        for d in ET7000_Server.device_list:
            if d.ip == ip:
                msg = '%s IP address %s is in use' % (self.get_name(), ip)
                self.logger.error(msg)
                self.set_state(DevState.FAULT)
                return
        self.ip = ip
        try:
            # create ICP DAS device
            self.et = ET7000(ip, logger=self.logger)
            self.et.client.auto_close(False)
            # wait for device initiate after possible reboot
            t0 = time.time()
            while self.et.read_module_type() == 0:
                if time.time() - t0 > 5.0:
                    self.logger.error('Device %s is not ready' % self.get_name())
                    self.set_state(DevState.FAULT)
                    return
            # add device to list
            ET7000_Server.device_list.append(self)
            msg = '%s ET-%s at %s has been created' % (self.get_name(), self.et.type_str, ip)
            self.logger.info(msg)
            self.info_stream(msg)
            # check if device type_str is recognized
            if self.et.type != 0:
                # set state to running
                self.set_state(DevState.RUNNING)
            else:
                # unknown device type_str
                msg = '%s ET-%s ERROR - unknown device type' % (self.get_name(), self.et.type_str)
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
        except:
            self.et = None
            self.ip = None
            msg = '%s ERROR init device' % self.get_name()
            self.log_exception(msg)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)

    def delete_device(self):
        self.remove_io()
        try:
            self.et.client.close()
        except:
            pass
        self.et = None
        self.ip = None
        super().delete_device()
        if self in ET7000_Server.device_list:
            ET7000_Server.device_list.remove(self)
        msg = '%s Device has been deleted' % self.get_name()
        self.logger.info(msg)

    def read_device_type(self):
        return self.et.type_str

    def read_IP(self):
        return self.ip

    def _read_attribute(self, attr: tango.Attribute):
        attr_name = attr.get_name()
        chan = int(attr_name[-2:])
        ad = attr_name[:2]
        mask = True
        if ad == 'ai':
            val = self.et.ai_read_channel(chan)
            mask = self.et.ai_masks[chan]
        elif ad == 'di':
            val = self.et.di_read_channel(chan)
        elif ad == 'do':
            val = self.et.do_read_channel(chan)
        elif ad == 'ao':
            val = self.et.ao_read_channel(chan)
            mask = self.et.ao_masks[chan]
        else:
            return float('nan')
        if val is not None and not math.isnan(val):
            return val
        if mask:
            msg = "%s Error reading %s %s" % (self.get_name(), attr_name, val)
            self.logger.error(msg)
        return float('nan')

    def read_general_async(self, attr: tango.Attribute):
        t = self.attributes[attr.get_name()].get_date().to_time()
        if time.time() - t >= self.async_time_limit:
            with self.lock:
                self.io_que.append(attr)
        return self.attributes[attr.get_name()].get_value()

    def read_general(self, attr: tango.Attribute):
        # attr_name = attr.get_name()
        # self.logger.debug('entry %s %s', self.get_name(), attr_name)
        if self.is_connected():
            val = self._read_attribute(attr)
        else:
            val = None
            msg = '%s %s Waiting for reconnect' % (self.get_name(), attr.get_name())
            self.logger.debug(msg)
        return self.set_attribute_value(attr, val)



    def write_general(self, attr: tango.WAttribute):
        attr_name = attr.get_name()
        if not self.is_connected():
            self.set_error_attribute_value(attr)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            msg = '%s %s Waiting for reconnect' % (self.get_name(), attr_name)
            self.logger.debug(msg)
            self.debug_stream(msg)
            return
        value = attr.get_write_value()
        chan = int(attr_name[-2:])
        ad = attr_name[:2]
        mask = True
        if ad == 'ao':
            result = self.et.ao_write_channel(chan, value)
            mask = self.et.ao_masks[chan]
        elif ad == 'do':
            result = self.et.do_write_channel(chan, value)
        else:
            msg = "%s Write to unknown attribute %s" % (self.get_name(), attr_name)
            self.logger.error(msg)
            self.error_stream(msg)
            self.set_error_attribute_value(attr)
            # attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            return
        if result:
            self.time = None
            self.error_count = 0
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            if mask:
                msg = "%s Error writing %s" % (self.get_name(), attr_name)
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_error_attribute_value(attr)
                # attr.set_quality(tango.AttrQuality.ATTR_INVALID)

    def read_all(self, attr: tango.Attribute):
        attr_name = attr.get_name()
        if not self.is_connected():
            msg = '%s %s Waiting for reconnect' % (self.get_name(), attr_name)
            self.logger.debug(msg)
            return self.set_error_attribute_value(attr)
        ad = attr_name[-2:]
        if ad == 'ai':
            val = self.et.ai_read()
        elif ad == 'di':
            val = self.et.di_read()
        elif ad == 'do':
            val = self.et.do_read()
        elif ad == 'ao':
            val = self.et.ao_read()
        else:
            msg = "%s Read for unknown attribute %s" % (self.get_name(), attr_name)
            self.logger.error(msg)
            return self.set_error_attribute_value(attr)
        if val is not None:
            self.time = 0.0
            self.error_count = 0
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
            return val
        else:
            return self.set_error_attribute_value(attr)

    def add_io(self):
        try:
            if self.et.type == 0:
                msg = '%s No IO attributes added for unknown device' % self.get_name()
                self.logger.warning(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
                return
            self.set_state(DevState.INIT)
            attr_name = ''
            # ai
            nai = 0
            if self.et.ai_n > 0:
                for k in range(self.et.ai_n):
                    try:
                        attr_name = 'ai%02d' % k
                        if self.et.ai_masks[k] or self.show_disabled_channels:
                            attr = tango.server.attribute(name=attr_name, dtype=float,
                                                          dformat=tango.AttrDataFormat.SCALAR,
                                                          access=tango.AttrWriteType.READ,
                                                          max_dim_x=1, max_dim_y=0,
                                                          fget=self.read_general,
                                                          label=attr_name,
                                                          doc='Analog input %s' % k,
                                                          unit=self.et.ai_units[k],
                                                          display_unit=1.0,
                                                          format='%f',
                                                          min_value=self.et.ai_min[k],
                                                          max_value=self.et.ai_max[k])
                            # add attr to device
                            self.add_attribute(attr)
                            self.attributes[attr_name] = attr
                            # self.restore_polling(attr_name)
                            nai += 1
                        else:
                            self.logger.info('%s is disabled', attr_name)
                    except:
                        msg = '%s Exception adding AI %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                attr = tango.server.attribute(name='all_ai', dtype=float,
                                              dformat=tango.AttrDataFormat.SPECTRUM,
                                              access=tango.AttrWriteType.READ,
                                              max_dim_x=self.et.ai_n, max_dim_y=0,
                                              fget=self.read_all,
                                              label=attr_name,
                                              doc='All analog inputs',
                                              unit='',
                                              display_unit=1.0,
                                              format='%f')
                # add attr to device
                self.add_attribute(attr)
                self.attributes[attr_name] = attr
                msg = '%d of %d analog inputs initialized' % (nai, self.et.ai_n)
                self.logger.info(msg)
                self.info_stream(msg)
            # ao
            nao = 0
            if self.et.ao_n > 0:
                for k in range(self.et.ao_n):
                    try:
                        attr_name = 'ao%02d' % k
                        if self.et.ao_masks[k] or self.show_disabled_channels:
                            attr = tango.server.attribute(name=attr_name, dtype=float,
                                                          dformat=tango.AttrDataFormat.SCALAR,
                                                          access=tango.AttrWriteType.READ_WRITE,
                                                          max_dim_x=1, max_dim_y=0,
                                                          fget=self.read_general,
                                                          fset=self.write_general,
                                                          label=attr_name,
                                                          doc='Analog output %s' % k,
                                                          unit=self.et.ao_units[k],
                                                          display_unit=1.0,
                                                          format='%f',
                                                          min_value=self.et.ao_min[k],
                                                          max_value=self.et.ao_max[k])
                            self.add_attribute(attr)
                            self.attributes[attr_name] = attr
                            # self.restore_polling(attr_name)
                            nao += 1
                        else:
                            self.logger.info('%s is disabled', attr_name)
                    except:
                        msg = '%s Exception adding AO %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                attr = tango.server.attribute(name='all_ao', dtype=float,
                                              dformat=tango.AttrDataFormat.SPECTRUM,
                                              access=tango.AttrWriteType.READ,
                                              max_dim_x=self.et.ao_n, max_dim_y=0,
                                              fget=self.read_all,
                                              label=attr_name,
                                              doc='All analog outputs. ONLY FOR READ',
                                              unit='',
                                              display_unit=1.0,
                                              format='%f')
                # add attr to device
                self.add_attribute(attr)
                self.attributes[attr_name] = attr
                msg = '%d of %d analog outputs initialized' % (nao, self.et.ao_n)
                self.logger.info(msg)
                self.info_stream(msg)
            # di
            ndi = 0
            if self.et.di_n > 0:
                for k in range(self.et.di_n):
                    try:
                        attr_name = 'di%02d' % k
                        attr = tango.server.attribute(name=attr_name, dtype=tango.DevBoolean,
                                                      dformat=tango.AttrDataFormat.SCALAR,
                                                      access=tango.AttrWriteType.READ,
                                                      max_dim_x=1, max_dim_y=0,
                                                      fget=self.read_general,
                                                      label=attr_name,
                                                      doc='Digital input %s' % k,
                                                      unit='',
                                                      display_unit=1.0,
                                                      format='')
                        self.add_attribute(attr)
                        self.attributes[attr_name] = attr
                        # self.restore_polling(attr_name)
                        ndi += 1
                    except:
                        msg = '%s Exception adding IO channel %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                attr = tango.server.attribute(name='all_di', dtype=bool,
                                              dformat=tango.AttrDataFormat.SPECTRUM,
                                              access=tango.AttrWriteType.READ,
                                              max_dim_x=self.et.di_n, max_dim_y=0,
                                              fget=self.read_all,
                                              label=attr_name,
                                              doc='All digital inputs. ONLY FOR READ',
                                              unit='',
                                              display_unit=1.0,
                                              format='%s')
                # add attr to device
                self.add_attribute(attr)
                self.attributes[attr_name] = attr
                msg = '%d digital inputs initialized' % ndi
                self.logger.info(msg)
                self.info_stream(msg)
            # do
            ndo = 0
            if self.et.do_n > 0:
                for k in range(self.et.do_n):
                    try:
                        attr_name = 'do%02d' % k
                        attr = tango.server.attribute(name=attr_name, dtype=tango.DevBoolean,
                                                      dformat=tango.AttrDataFormat.SCALAR,
                                                      access=tango.AttrWriteType.READ_WRITE,
                                                      max_dim_x=1, max_dim_y=0,
                                                      fget=self.read_general,
                                                      fset=self.write_general,
                                                      label=attr_name,
                                                      doc='Digital output %s' % k,
                                                      unit='',
                                                      display_unit=1.0,
                                                      format='')
                        self.add_attribute(attr)
                        self.attributes[attr_name] = attr
                        # self.restore_polling(attr_name)
                        ndo += 1
                    except:
                        msg = '%s Exception adding IO channel %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                attr = tango.server.attribute(name='all_do', dtype=bool,
                                              dformat=tango.AttrDataFormat.SPECTRUM,
                                              access=tango.AttrWriteType.READ,
                                              max_dim_x=self.et.do_n, max_dim_y=0,
                                              fget=self.read_all,
                                              label=attr_name,
                                              doc='All digital outputs. ONLY FOR READ',
                                              unit='',
                                              display_unit=1.0,
                                              format='%s')
                # add attr to device
                self.add_attribute(attr)
                self.attributes[attr_name] = attr
                msg = '%d digital outputs initialized' % ndo
                self.logger.info(msg)
                self.info_stream(msg)
            self.set_state(DevState.RUNNING)
        except:
            msg = '%s Error adding IO channels' % self.get_name()
            self.logger.error(msg)
            self.logger.debug('', exc_info=True)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)
            return

    def remove_io(self):
        try:
            for attr_name in self.attributes:
                self.remove_attribute(attr_name)
                self.logger.debug('%s attribute %s removed' % (self.get_name(), attr_name))
            self.attributes = {}
            self.set_state(DevState.UNKNOWN)
        except:
            msg = '%s Error deleting IO channels' % self.get_name()
            self.logger.error(msg)
            self.logger.debug('', exc_info=True)
            self.error_stream(msg)
            # self.set_state(DevState.FAULT)

    def is_connected(self):
        if self.et is None or self.et.type == 0:
            return False
        return True

    def set_error_attribute_value(self, attr: tango.Attribute):
        attr.set_quality(tango.AttrQuality.ATTR_INVALID)
        v = None
        if attr.get_data_format() == tango.DevBoolean:
            v = False
        elif attr.get_data_format() == tango.DevDouble:
            v = float('nan')
        if attr.get_data_type() == tango.SPECTRUM:
            v = [v]
        attr.set_value(v)
        return v

    def set_attribute_value(self, attr: tango.Attribute, value=None):
        if value is not None and not math.isnan(value):
            self.time = None
            self.error_count = 0
            attr.set_value(value)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
            return value
        else:
            v = None
            if attr.get_data_format() == tango.DevBoolean:
                v = False
            elif attr.get_data_format() == tango.DevDouble:
                v = float('nan')
            if attr.get_data_type() == tango.SPECTRUM:
                v = [v]
            attr.set_value(v)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            return v

    # def get_attribute_property(self, attr_name: str, prop_name: str):
    #     device_name = self.get_name()
    #     database = self.database
    #     all_attr_prop = database.get_device_attribute_property(device_name, attr_name)
    #     all_prop = all_attr_prop[attr_name]
    #     if prop_name in all_prop:
    #         prop = all_prop[prop_name][0]
    #     else:
    #         prop = ''
    #     return prop

    # def restore_polling(self, attr_name: str):
    #     try:
    #         p = self.get_attribute_property(attr_name, 'polling')
    #         pn = int(p)
    #         self.dp.poll_attribute(attr_name, pn)
    #     except:
    #         #self.logger.warning('', exc_info=True)
    #         pass

    def initialize_dynamic_attributes(self):
        # self.logger.error('-------- entry -----')
        self.add_io()


if __name__ == "__main__":
    ET7000_Server.run_server()
