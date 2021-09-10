# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""

import time
import logging
import math
from threading import Lock

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, AttributeInfoEx
from tango.server import Device, attribute, command, pipe, device_property

from ET7000 import FakeET7000 as ET7000
# from ET7000 import ET7000
from TangoServerPrototype import TangoServerPrototype
from TangoUtils import config_logger


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

    def init_device(self):
        if self in ET7000_Server.device_list:
            self.logger.info('delete')
            self.delete_device()
        super().init_device()
        self.time = None

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
                msg = '%s IP address %s is in use' % (self, ip)
                self.logger.error(msg)
                self.error_stream(msg)
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
        self.info_stream(msg)

    def read_device_type(self):
        return self.et.type_str

    def read_IP(self):
        return self.ip

    def read_general(self, attr: tango.Attribute):
        # self.logger.debug('entry %s %s', self.get_name(), attr_name)
        attr_name = attr.get_name()
        if not self.is_connected():
            self.set_error_attribute_value(attr)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            msg = '%s %s Waiting for reconnect' % (self.get_name(), attr_name)
            self.logger.debug(msg)
            self.debug_stream(msg)
            return float('nan')
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
            msg = "%s Read unknown attribute %s" % (self.get_name(), attr_name)
            self.logger.error(msg)
            self.error_stream(msg)
            self.set_error_attribute_value(attr)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            return float('nan')
        if val is not None and not math.isnan(val):
            self.time = None
            self.error_count = 0
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
            return val
        else:
            self.set_error_attribute_value(attr)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            if mask:
                msg = "%s Error reading %s %s" % (self.get_name(), attr_name, val)
                self.logger.error(msg)
                self.error_stream(msg)
            return float('nan')

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

    @command
    def reconnect(self):
        self.delete_device()
        self.init_device()
        self.add_io()
        msg = '%s Reconnected' % self.get_name()
        self.logger.info(msg)
        self.info_stream(msg)

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
                                                          fread=self.read_general,
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
                                                          fread=self.read_general,
                                                          fwrite=self.write_general,
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
                                                      fread=self.read_general,
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
                                                      fread=self.read_general,
                                                      fwrite=self.write_general,
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
        if attr.get_data_format() == tango.DevBoolean:
            attr.attr.set_value(False)
        elif attr.get_data_format() == tango.DevDouble:
            attr.set_value(float('nan'))

    # def get_attribute_property(self, attr_name: str, prop_name: str):
    #     device_name = self.get_name()
    #     databse = self.database
    #     all_attr_prop = databse.get_device_attribute_property(device_name, attr_name)
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
