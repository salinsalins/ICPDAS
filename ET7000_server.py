#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""

import sys
import time
import logging
import numpy
import traceback
import math
from threading import Thread, Lock

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property

#from FakeET7000 import ET7000
from ET7000 import ET7000


class ET7000_Server(Device):
    devices = []

    devicetype = attribute(label="type", dtype=str,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%s",
                        doc="ET7000 device type. 0x0 - unknown or offline")

    def read_devicetype(self):
        with self._lock:
            return self.device_type_str

    def read_general(self, attr: tango.Attribute):
        with self._lock:
            name = attr.get_name()
            if not self.is_connected():
                self.reconnect()
                if not self.is_connected():
                    self.set_error_attribute_value(attr)
                    attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                    msg = '%s %s Device is not connected' % (self.device_name, name)
                    self.logger.debug(msg)
                    self.debug_stream(msg)
                    return
            chan = int(name[-2:])
            ad = name[:2]
            if ad == 'ai':
                val = self.et.read_AI_channel(chan)
            elif ad == 'di':
                val = self.et.read_DI_channel(chan)
            elif ad == 'do':
                val = self.et.read_DO_channel(chan)
            elif ad == 'ao':
                val = self.et.read_AO_channel(chan)
            else:
                self.set_error_attribute_value(attr)
                attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                msg = "%s Read unknown attribute %s" % (self.device_name, name)
                self.logger.error(msg)
                self.error_stream(msg)
                return
            if val is not None and not math.isnan(val):
                self.time = None
                self.error_count = 0
                attr.set_value(val)
                attr.set_quality(tango.AttrQuality.ATTR_VALID)
            else:
                msg = "%s Error reading %s" % (self.device_name, name)
                self.logger.error(msg)
                self.error_stream(msg)
                if ad == 'ai':
                    attr.set_value(float('nan'))
                elif ad == 'ao':
                    attr.set_value(float('nan'))
                elif ad == 'di':
                    attr.set_value(False)
                elif ad == 'do':
                    attr.set_value(False)
                attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                self.disconnect()

    def set_error_attribute_value(self, attr: tango.Attribute):
        if attr.get_data_format() == tango.DevBoolean:
            attr.attr.set_value(False)
        elif attr.get_data_format() == tango.DevDouble:
            attr.set_value(float('nan'))

    def write_general(self, attr: tango.WAttribute):
        with self._lock:
            name = attr.get_name()
            if not self.is_connected():
                self.reconnect()
                if not self.is_connected():
                    self.set_error_attribute_value(attr)
                    attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                    msg = '%s %s Device is not connected' % (self.device_name, name)
                    self.logger.debug(msg)
                    self.debug_stream(msg)
                    return
            value = attr.get_write_value()
            chan = int(name[-2:])
            ad = name[:2]
            if ad  == 'ao':
                result = self.et.write_AO_channel(chan, value)
            elif ad == 'do':
                result = self.et.write_DO_channel(chan, value)
            else:
                msg = "%s Write to unknown attribute %s" % (self.device_name, name)
                self.logger.error(msg)
                self.error_stream(msg)
                attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                return
            if result:
                self.time = None
                self.error_count = 0
                attr.set_quality(tango.AttrQuality.ATTR_VALID)
            else:
                self.error_count += 1
                msg = "%s Error writing %s" % (self.device_name, name)
                self.logger.error(msg)
                self.error_stream(msg)
                attr.set_quality(tango.AttrQuality.ATTR_INVALID)
                self.disconnect()

    def reconnect(self, force=False):
        print(1, self.time, self.is_connected())
        if not force and self.is_connected():
            return
        if self.time is None:
            self.time = time.time()
        print(2, self.time, self.is_connected())
        if force or time.time() - self.time > self.reconnect_timeout / 1000.0:
            self.Reconnect()
            if not self.is_connected():
                self.time = time.time()
                self.et = None
                self.error_count = 0
                msg = '%s Reconnection error' % self.device_name
                self.logger.info(msg)
                self.info_stream(msg)
                return
            msg = '%s Reconnected sucessfully' % self.device_name
            self.logger.debug(msg)
            self.debug_stream(msg)

    def is_connected(self):
        if self.device_type == 0 or self.time is not None or self.et is None:
            return False
        return True

    def disconnect(self):
        self.error_count += 1
        if self.error_count <3:
            return
        self.time = time.time()
        try:
            self.et._client.close()
        except:
            pass
        self.et = None
        self.error_count = 0
        return

    @command
    def Reconnect(self):
        msg = '%s Reconnecting ...' % self.device_name
        self.logger.info(msg)
        self.info_stream(msg)
        self.remove_io()
        self.init_device()
        self.add_io()

    @command(dtype_in=int)
    def SetLogLevel(self, level):
        with self._lock:
            self.logger.setLevel(level)
            msg = '%s Log level set to %d' % (self.device_name, level)
            self.logger.info(msg)
            self.info_stream(msg)

    def add_io(self):
        with self._lock:
            try:
                if self.device_type == 0:
                    msg = '%s No IO attributes added for unknown device' % self.device_name
                    self.logger.debug(msg)
                    self.debug_stream(msg)
                    self.set_state(DevState.FAULT)
                    return
                msg = '%s ET%s at %s initialization' % (self.device_name, self.device_type_str, self.ip)
                self.info_stream(msg)
                self.logger.info(msg)
                self.set_state(DevState.INIT)
                # device proxy
                name = self.get_name()
                dp = tango.DeviceProxy(name)
                # initialize ai, ao, di, do attributes
                # ai
                if self.et.AI_n > 0:
                    for k in range(self.et.AI_n):
                        attr_name = 'ai%02d'%k
                        attr = tango.Attr(attr_name, tango.DevDouble, tango.AttrWriteType.READ)
                        self.add_attribute(attr, self.read_general)
                        # configure attribute properties
                        rng = self.et.range(self.et.AI_ranges[k])
                        ac = dp.get_attribute_config(attr_name)
                        if ac.unit is None or '' == ac.unit:
                            ac.unit = str(rng['units'])
                        ac.min_value = str(rng['min'])
                        ac.max_value = str(rng['max'])
                        dp.set_attribute_config(ac)
                    self.logger.info('%d analog inputs initialized' % self.et.AI_n)
                    self.info_stream('%d analog inputs initialized' % self.et.AI_n)
                # ao
                if self.et.AO_n > 0:
                    for k in range(self.et.AO_n):
                        attr_name = 'ao%02d'%k
                        attr = tango.Attr(attr_name, tango.DevDouble, tango.AttrWriteType.READ_WRITE)
                        self.add_attribute(attr, self.read_general, self.write_general)
                        # configure attribute properties
                        rng = self.et.range(self.et.AO_ranges[k])
                        ac = dp.get_attribute_config(attr_name)
                        if ac.unit is None or '' == ac.unit:
                            ac.unit = str(rng['units'])
                        ac.min_value = str(rng['min'])
                        ac.max_value = str(rng['max'])
                        dp.set_attribute_config(ac)
                    self.logger.info('%d analog outputs initialized' % self.et.AO_n)
                    self.info_stream('%d analog outputs initialized' % self.et.AO_n)
                # di
                if self.et.DI_n > 0:
                    for k in range(self.et.DI_n):
                        attr_name = 'di%02d'%k
                        attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ)
                        self.add_attribute(attr, self.read_general, w_meth=self.write_general)
                    self.logger.info('%d digital inputs initialized' % self.et.DI_n)
                    self.info_stream('%d digital inputs initialized' % self.et.DI_n)
                # do
                if self.et.DO_n > 0:
                    for k in range(self.et.DO_n):
                        attr_name = 'do%02d'%k
                        attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ_WRITE)
                        self.add_attribute(attr, self.read_general, self.write_general)
                    self.logger.info('%d digital outputs initialized' % self.et.DO_n)
                    self.info_stream('%d digital outputs initialized' % self.et.DO_n)
                self.set_state(DevState.RUNNING)
            except:
                msg = '%s Error adding IO channels' % self.device_name
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)

    def remove_io(self):
        with self._lock:
            try:
                atts = self.get_device_attr()
                n = atts.get_attr_nb()
                for k in range(n):
                    at = atts.get_attr_by_ind(k)
                    attr_name = at.get_name()
                    io = attr_name[-4:-2]
                    #print(io)
                    if io == 'ai' or io == 'ao' or io == 'di' or io == 'do':
                        #print('Removing', attr_name)
                        self.remove_attribute(attr_name)
                self.set_state(DevState.UNKNOWN)
            except:
                msg = '%s Error deleting IO channels' % self.device_name
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)

    def get_device_property(self, prop: str, default=None):
        name = self.get_name()
        # device proxy
        dp = tango.DeviceProxy(name)
        # read property
        pr = dp.get_property(prop)[prop]
        result = None
        if len(pr) > 0:
            result = pr[0]
        if default is None:
            return result
        try:
            if result is None or result == '':
                result = default
            else:
                result = type(default)(result)
        except:
            pass
        return result

    def init_device(self):
        # init a thread lock
        if not hasattr(self, '_lock'):
            self._lock = Lock()
        with self._lock:
            try:
                self.et._client.close()
            except:
                pass
            self.logger = config_logger()
            self.et = None
            self.ip = None
            self.error_count = 0
            self.time = None
            self.reconnect_timeout = int(self.get_device_property('reconnect_timeout', 5000))
            self.device_type = 0
            self.device_type_str = '0000'
            self.device_name = self.get_name()
            self.set_state(DevState.INIT)
            Device.init_device(self)
            # get ip from property
            ip = self.get_device_property('ip', '192.168.1.122')
            # check if ip is in use
            for d in ET7000_Server.devices:
                if d.ip == ip:
                    msg = '%s IP address %s is in use' % (self, ip)
                    self.logger.error(msg)
                    self.error_stream(msg)
                    self.set_state(DevState.FAULT)
                    return
            self.ip = ip
            try:
                # create ICP DAS device
                et = ET7000(ip, logger=self.logger)
                self.et = et
                self.device_type = self.et._name
                self.device_type_str = self.et.type
                # add device to list
                ET7000_Server.devices.append(self)
                msg = '%s ET%s at %s has been created' % (self.device_name, self.device_type_str, ip)
                self.logger.info(msg)
                self.info_stream(msg)
                # check if device type is recognized
                if self.device_type != 0:
                    # set state to running
                    self.set_state(DevState.RUNNING)
                else:
                    # unknown device type
                    msg = '%s ET%s ERROR - unknown device type' % (self.device_name, self.device_type_str)
                    self.logger.error(msg)
                    self.error_stream(msg)
                    self.set_state(DevState.FAULT)
            except:
                self.et = None
                self.ip = None
                self.device_type = 0
                msg = '%s ERROR init device' % self.device_name
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)

    def delete_device(self):
        with self._lock:
            try:
                self.et._client.close()
            except:
                pass
            self.et = None
            self.ip = None
            if self in ET7000_Server.devices:
                ET7000_Server.devices.remove(self)
            msg = '%s Device has been deleted' % self.device_name
            self.logger.info(msg)
            self.info_stream(msg)


def post_init_callback():
    #util = tango.Util.instance()
    #devices = util.get_device_list('*')
    for dev in ET7000_Server.devices:
        #print(dev)
        #if hasattr(dev, 'add_io'):
        dev.add_io()
            #print(' ')

def config_logger(name: str=__name__, level: int=logging.DEBUG):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.propagate = False
        logger.setLevel(level)
        f_str = '%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s'
        log_formatter = logging.Formatter(f_str, datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)
    return logger

def test():
    time.sleep(0.5)
    print('test')

def looping():
    time.sleep(1.5)
    all_connected = True
    for dev in ET7000_Server.devices:
        #dev.reconnect()
        all_connected = all_connected and dev.is_connected()
        #print(dev, all_connected)

if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)
    ET7000_Server.run_server(post_init_callback=post_init_callback, event_loop=looping)
    #ET7000_Server.run_server(post_init_callback=post_init_callback)
