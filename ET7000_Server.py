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
        super().init_device()
        self.time = None

    def set_config(self):
        super().set_config()
        self.attributes = {}
        self.et = None
        self.ip = None
        self.error_count = 0
        self.time = time.time()
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
                self.disconnect(True)
        except:
            self.et = None
            self.ip = None
            self.disconnect(True)
            msg = '%s ERROR init device' % self.get_name()
            self.log_exception(msg)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)

    def delete_device(self):
        try:
            self.et.client.close()
        except:
            pass
        self.et = None
        self.ip = None
        if self in ET7000_Server.devices:
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
                self.disconnect()
            return float('nan')

    def write_general(self, attr: tango.WAttribute):
        attr_name = attr.get_name()
        if not self.is_connected():
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
                self.disconnect()

    @command
    def Reconnect(self):
        msg = '%s Reconnecting ...' % self.get_name()
        self.logger.info(msg)
        self.info_stream(msg)
        # self.remove_io()
        self.init_device()
        self.add_io()

    def add_attribute_2(self, attr, r_meth=None, w_meth=None):
        # try:
        if r_meth is None:
            r_meth = self.read_general
        if w_meth is None:
            w_meth = self.write_general
        attr_name = attr.get_name()
        mattrib = self.get_device_attr()
        try:
            mattrib.get_attr_by_name(attr_name)
            self.logger.debug('%s attribute %s exists' % (self.get_name(), attr_name))
            return
        except:
            self.logger.debug("Exception:", exc_info=True)
        self.add_attribute(attr, r_meth, w_meth=w_meth)
        self.attributes[attr.get_name()] = attr
        self.logger.debug('%s attribute %s has been created' % (self.get_name(), attr_name))

    # except:
    #     msg = '%s Exception creating attribute %s' % (self.get_name(), attr_name)
    #     self.logger.info(msg)
    #     self.logger.debug('', exc_info=True)
    #     self.info_stream(msg)

    def configure_attribute(self, attr_name, rng):
        ac_old = None
        if hasattr(self, 'old_config') and attr_name in self.old_config:
            ac_old = self.old_config[attr_name]
        elif hasattr(self, 'config') and attr_name in self.config:
            ac_old = self.config[attr_name]
        ac = self.dp.get_attribute_config_ex(attr_name)[0]
        if ac.unit is None or '' == ac.unit:
            ac.unit = str(rng['units'])
        ac.min_value = str(rng['min'])
        ac.max_value = str(rng['max'])
        if ac_old is not None:
            if ac.label is None or '' == ac.label:
                ac.label = ac_old.label
            if ac.display_unit is None or '' == ac.display_unit:
                ac.display_unit = ac_old.display_unit
            if ac.format is None or '' == ac.format:
                ac.format = ac_old.format
        if ac.display_unit is None or '' == ac.display_unit:
            msg = '%s %s display_units is empty' % (self, attr_name)
            self.debug_stream(msg)
            self.logger.warning(msg)
        self.dp.set_attribute_config(ac)
        self.config[attr_name] = ac

    def add_io(self):
        try:
            if self.device_type == 0:
                msg = '%s No IO attributes added for unknown device' % self.get_name()
                self.logger.warning(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
                self.disconnect(force=True)
                return
            msg = '%s ET%s at %s IO initialization' % (self.get_name(), self.et.type_str, self.ip)
            self.debug_stream(msg)
            self.logger.debug(msg)
            self.set_state(DevState.INIT)
            # device proxy
            name = self.get_name()
            # dp = tango.DeviceProxy(type)
            # initialize ai, ao, di, do attributes
            # ai
            nai = 0
            if self.et.ai_n > 0:
                for k in range(self.et.ai_n):
                    try:
                        print(self.et.ai_units[k], self.et.ai_max[k])
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
                            self.logger.info('%s is switched off', attr_name)
                    except:
                        msg = '%s Exception adding IO channel %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                        self.disconnect(force=True)
                        return
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
                            self.logger.info('%s is switched off', attr_name)
                    except:
                        msg = '%s Exception adding IO channel %s' % (self.get_name(), attr_name)
                        self.logger.warning(msg)
                        self.logger.debug('', exc_info=True)
                        self.disconnect(force=True)
                        return
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
                        self.disconnect(force=True)
                        return
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
                        self.disconnect(force=True)
                        return
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
            self.disconnect(force=True)
            return

    def remove_io(self):
        try:
            atts = self.get_device_attr()
            n = atts.get_attr_nb()
            for k in range(n):
                at = atts.get_attr_by_ind(k)
                attr_name = at.get_name()
                io = attr_name[-4:-2]
                # print(io)
                if io == 'ai' or io == 'ao' or io == 'di' or io == 'do':
                    # print('Removing', attr_name)
                    self.remove_attribute(attr_name)
                    self.logger.debug('%s attribute %s removed' % (self.get_name(), attr_name))
            self.set_state(DevState.UNKNOWN)
        except:
            msg = '%s Error deleting IO channels' % self.get_name()
            self.logger.error(msg)
            self.logger.debug('', exc_info=True)
            self.error_stream(msg)
            # self.set_state(DevState.FAULT)

    def is_connected(self):
        if self.device_type == 0 or self.time is not None or self.et is None:
            return False
        return True

    def reconnect(self, force=False):
        # with self._lock:
        # self.logger.debug('reconnect entry')
        if not force and self.is_connected():
            self.logger.debug('%s already connected' % self.get_name())
            return
        if self.time is None:
            self.time = time.time()
        if force or ((time.time() - self.time) > self.reconnect_timeout / 1000.0):
            self.Reconnect()
            if not self.is_connected():
                self.time = time.time()
                self.et = None
                self.error_count = 0
                msg = '%s Reconnection error' % self.get_name()
                self.logger.info(msg)
                self.info_stream(msg)
                return
            msg = '%s Reconnected successfully' % self.get_name()
            self.logger.debug(msg)
            self.debug_stream(msg)

    def disconnect(self, force=False):
        if not force and self.time is not None:
            msg = "%s already disconnected" % self.get_name()
            self.logger.debug(msg)
            return
        self.error_count += 1
        if not force and self.error_count < 3:
            return
        try:
            self.et.client.close()
        except:
            pass
        self.time = time.time()
        self.et = None
        self.error_count = 0
        msg = "%s Disconnected" % self.get_name()
        self.logger.debug(msg)
        self.debug_stream(msg)
        return

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
