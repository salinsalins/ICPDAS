# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""
# noinspection PyTrailingSemicolon
import sys; sys.path.append('../TangoUtils')

import time
import math
from threading import Lock, RLock

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, AttributeInfoEx, Attr
from tango.server import Device, attribute, command
from ET7000 import FakeET7000
from ET7000 import ET7000
from TangoServerPrototype import TangoServerPrototype
from log_exception import log_exception

NaN = float('nan')
DEFAULT_IP = '192.168.1.122'
DEFAULT_RECONNECT_TIMEOUT = 10000.0


class ET7000_Server(TangoServerPrototype):
    server_version_value = '6.1'
    server_name_value = 'Tango Server for ICP DAS ET-7000 Series Devices'

    device_type = attribute(label="device_type", dtype=str,
                            display_level=DispLevel.OPERATOR,
                            access=AttrWriteType.READ,
                            unit="", format="%4s",
                            doc="ET7000 device type. '0000' - unknown or offline")

    IP = attribute(label="IP", dtype=str,
                   display_level=DispLevel.OPERATOR,
                   access=AttrWriteType.READ,
                   unit="", format="%s",
                   doc="ET7000 device IP address")

    # ******** init_device ***********
    def init_device(self):
        if self.get_name() in ET7000_Server.devices:
            ET7000_Server.devices.pop(self.get_name(), None)
            self.delete_device()
        super().init_device()
        # self.configure_tango_logging()
        msg = f'{self.get_name()} ET7000_Server Initialization'
        self.logger.debug(msg)
        self.set_state(DevState.INIT, msg)
        self.init_io = True
        self.init_po = False
        self.et = None
        self.ip = None
        self.error_time = 0.0
        self.emulate = self.config.get('emulate', False)
        self.reconnect_timeout = self.config.get('reconnect_timeout', DEFAULT_RECONNECT_TIMEOUT)
        self.show_disabled_channels = self.config.get('show_disabled_channels', False)
        # get ip from property
        ip = self.config.get('IP', DEFAULT_IP)
        # check if ip is in use
        for d in ET7000_Server.devices:
            v = ET7000_Server.devices[d]
            if not v.emulate and v.ip == ip:
                msg = '%s IP address %s is in use' % (self.get_name(), ip)
                self.logger.error(msg)
                self.set_state(DevState.FAULT, msg)
                self.error_time = time.time()
                return
        self.ip = ip
        # create ICP DAS device
        try:
            if self.emulate:
                self.et = FakeET7000(ip, logger=self.logger)
            else:
                self.et = ET7000(ip, logger=self.logger)
            self.et.client.auto_close(False)
            # wait for device initiate after possible reboot
            t0 = time.time()
            while self.et.read_module_type() == 0:
                if time.time() - t0 > 5.0:
                    self.logger.error('Device %s is not ready' % self.get_name())
                    self.set_state(DevState.FAULT, 'Device %s is not ready' % self.get_name())
                    self.error_time = time.time()
                    return
            # # add device to list
            # ET7000_Server.devices[self.get_name()] = self
            # check if device type is recognized
            if self.et and self.et.type != 0:
                # device is recognized
                msg = '%s PET-%s at %s has been created' % (self.get_name(), self.et.type_str, ip)
                self.logger.info(msg)
                self.set_state(DevState.RUNNING, msg)
                # if device was initiated before
                if hasattr(self, 'deleted') and self.deleted:
                    self.add_io()
                    self.restore_polling()
                    self.init_io = False
                    self.init_po = False
                    self.deleted = False
            else:
                # unknown device
                msg = '%s Unknown PET device' % self.get_name()
                self.logger.error(msg)
                self.set_state(DevState.FAULT, msg)
        except KeyboardInterrupt:
            raise
        except:
            self.et = None
            self.ip = None
            self.error_time = time.time()
            msg = '%s init exception' % self.get_name()
            self.log_exception(msg)
            self.set_state(DevState.FAULT, msg)

    def delete_device(self):
        self.save_polling_state()
        self.stop_polling()
        self.remove_io()
        del self.et
        self.init_io = True
        self.et = None
        self.ip = None
        super().delete_device()
        ET7000_Server.devices.pop(self.get_name(), None)
        tango.Database().delete_device_property(self.get_name(), 'polled_attr')
        self.deleted = True
        msg = '%s Device has been deleted' % self.get_name()
        self.logger.info(msg)

    # ************* Attribute R/W routines *****************
    def read_device_type(self):
        if self.et:
            return self.et.type_str
        else:
            return 'OFFLINE'

    def read_IP(self):
        return self.ip

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
            self.error_time = 0.0
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
            return val
        else:
            return self.set_error_attribute_value(attr)

    def read_general(self, attr: tango.Attribute):
        if self.is_connected():
            val = self._read_io(attr)
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
            self.set_error_attribute_value(attr)
            return
        if result:
            self.error_time = 0.0
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            if mask:
                self.error_time = time.time()
                msg = "%s Write to disabled attribute %s" % (self.get_name(), attr_name)
                self.logger.error(msg)
                self.set_error_attribute_value(attr)

    def _read_io(self, attr: tango.Attribute):
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
            self.error_time = time.time()
            msg = "%s I/O channel %s disabled" % (self.get_name(), attr_name)
            self.logger.error(msg)
        return float('nan')

    # *************   Commands   *****************
    @command(dtype_in=(float,), dtype_out=(float,))
    def read_modbus(self, data):
        n = 1
        try:
            n = int(data[1])
            result = self.et.read_modbus(int(data[0]), n)
            # self.LOGGER.debug('%s', result)
            if result:
                return result
            return [float('nan')] * n
        except KeyboardInterrupt:
            raise
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
            # self.LOGGER.debug('%s %s %s ', a, v, result)
            if result:
                return result
            return False
        except KeyboardInterrupt:
            raise
        except:
            # self.LOGGER.debug('%s %s', a, v)
            self.log_exception('write_modbus exception')
            return False

    @command
    def reconnect(self):
        self.delete_device()
        self.init_device()
        self.add_io()
        self.restore_polling()
        self.init_po = False
        msg = '%s Reconnected' % self.get_name()
        self.logger.info(msg)

    # ******** additional helper functions ***********
    def add_io(self):
        nai = 0
        nao = 0
        ndi = 0
        ndo = 0
        try:
            if self.et is None or self.et.type == 0:
                self.error_time = time.time()
                msg = '%s No IO attributes added for unknown device' % self.get_name()
                self.logger.warning(msg)
                self.set_state(DevState.FAULT, msg)
                self.init_io = False
                self.init_po = False
                return
            self.error_time = 0.0
            self.set_state(DevState.INIT, 'Attributes creation started')
            attr_name = ''
        # ai
            nai = 0
            try:
                if self.et.ai_n > 0:
                    for k in range(self.et.ai_n):
                        attr_name = 'ai%02d' % k
                        if hasattr(self, attr_name):
                            continue
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
                            self.created_attributes[attr_name] = attr
                            nai += 1
                        else:
                            self.logger.info('%s is disabled', attr_name)
                    msg = '%s %d of %d analog inputs initialized' % (self.get_name(), nai, self.et.ai_n)
                    self.logger.info(msg)
            except KeyboardInterrupt:
                raise
            except:
                msg = '%s Exception adding AI %s' % (self.get_name(), attr_name)
                self.log_exception(self.logger, msg)
        # ao
            nao = 0
            try:
                if self.et.ao_n > 0:
                    for k in range(self.et.ao_n):
                        attr_name = 'ao%02d' % k
                        if hasattr(self, attr_name):
                            continue
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
                            self.created_attributes[attr_name] = attr
                            v = self.et.ao_read(k)
                            attr.get_attribute(self).set_write_value(v)
                            nao += 1
                        else:
                            self.logger.debug('%s is disabled', attr_name)
                    msg = '%s %d of %d analog outputs initialized' % (self.get_name(), nao, self.et.ao_n)
                    self.logger.info(msg)
            except KeyboardInterrupt:
                raise
            except:
                msg = '%s Exception adding AO %s' % (self.get_name(), attr_name)
                log_exception(self.logger, msg)
        # di
            ndi = 0
            try:
                if self.et.di_n > 0:
                    for k in range(self.et.di_n):
                        attr_name = 'di%02d' % k
                        if hasattr(self, attr_name):
                            continue
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
                        self.created_attributes[attr_name] = attr
                        ndi += 1
                    msg = '%s %d digital inputs initialized' % (self.get_name(), ndi)
                    self.logger.info(msg)
            except KeyboardInterrupt:
                raise
            except:
                msg = '%s Exception adding DI %s' % (self.get_name(), attr_name)
                log_exception(self.logger, msg)
        # do
            ndo = 0
            try:
                if self.et.do_n > 0:
                    for k in range(self.et.do_n):
                        attr_name = 'do%02d' % k
                        if hasattr(self, attr_name):
                            continue
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
                        self.created_attributes[attr_name] = attr
                        v = self.et.do_read(k)
                        attr.get_attribute(self).set_write_value(v)
                        ndo += 1
                    msg = '%s %d digital outputs initialized' % (self.get_name(), ndo)
                    self.logger.info(msg)
            except KeyboardInterrupt:
                raise
            except:
                msg = '%s Exception adding DO %s' % (self.get_name(), attr_name)
                log_exception(self.logger, msg)
            self.set_state(DevState.RUNNING, 'Attributes creation finished')
        except KeyboardInterrupt:
            raise
        except:
            self.error_time = time.time()
            msg = '%s Error adding IO attributes' % self.get_name()
            log_exception(self.logger, msg)
            self.set_state(DevState.FAULT, msg)
            return
        self.init_io = False
        self.init_po = True
        return nai + nao + ndi + ndo

    def remove_io(self):
        # with self.lock:
        removed = []
        for attr_name in self.created_attributes:
            try:
                self.remove_attribute(attr_name)
                self.logger.debug('%s attribute %s removed' % (self.get_name(), attr_name))
                removed.append(attr_name)
            except KeyboardInterrupt:
                raise
            except:
                log_exception(self.logger, '%s Error deleting attribute' % self.get_name())
        # for attr_name in removed:
        #     self.created_attributes.pop(attr_name, None)
        self.created_attributes = {}
        self.set_state(DevState.UNKNOWN)
        self.init_io = True
        self.init_po = False

    def is_connected(self):
        if self.et is None or self.et.type == 0:
            if self.error_time > 0.0 and self.error_time - time.time() > self.reconnect_timeout:
                self.reconnect()
            return False
        return True

    def set_error_attribute_value(self, attr: tango.Attribute):
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

    def set_attribute_value(self, attr: tango.Attribute, value=None):
        if value is not None and not math.isnan(value):
            self.error_time = 0.0
            attr.set_value(value)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
            return value
        else:
            return self.set_error_attribute_value(attr)


def looping():
    # ET7000_Server.LOGGER.debug('loop entry')
    post_init_callback()
    # for dev in ET7000_Server.devices:
    #     if dev.init_io:
    #         dev.add_io()
    #     if dev.error_time > 0.0 and dev.error_time - time.time() > dev.reconnect_timeout:
    #         dev.reconnect()
    time.sleep(1.0)
    # ET7000_Server.LOGGER.debug('loop exit')


def post_init_callback():
    # called once at server initiation
    for dev in ET7000_Server.devices:
        v = ET7000_Server.devices[dev]
        if v.init_io:
            v.add_io()
    for dev in ET7000_Server.devices:
        v = ET7000_Server.devices[dev]
        if v.init_po:
            v.restore_polling()
            v.init_po = False


if __name__ == "__main__":
    ET7000_Server.run_server(post_init_callback=post_init_callback)
    # ET7000_Server.run_server(event_loop=looping, post_init_callback=post_init_callback)
    # ET7000_Server.run_server()
