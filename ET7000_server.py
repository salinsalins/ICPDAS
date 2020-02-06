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

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property

from ET7000 import ET7000


class ET7000_Server(Device):
    devices = []

    devicetype = attribute(label="type", dtype=str,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%s",
                        doc="ET7000 device type. 0x0 - unknown or offline")

#    def __init__(self, *args, **kwargs):
#        print(args, kwargs)
#        self.logger = config_logger()
#        self.et = None

    def read_devicetype(self):
        if self.et is None:
            self._reconnect()
            return '0000'
        try:
            t = hex(self.et._name)[-4:]
        except:
            self._reconnect()
            return '0000'
        return t

    def read_general(self, attr: tango.Attribute):
        name = attr.get_name()
        #print("Reading attribute %s %s" % (self.ip, name))
        if self.et is None:
            self.set_error_attribute_value(attr)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            msg = "Read from non initialized device" % self
            self.logger.error(msg)
            self.error_stream(msg)
            self._reconnect()
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
            msg = "%s Read unknown attribute %s" % (self, name)
            self.logger.error(msg)
            self.error_stream(msg)
            return
        if val is not None and not math.isnan(val):
            self.time = None
            self.error_count = 0
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            self.error_count += 1
            msg = "%s Error reading %s" % (self, name)
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
            self._reconnect()

    def set_error_attribute_value(self, attr: tango.Attribute):
        if attr.get_data_format() == tango.DevBoolean:
            attr.attr.set_value(False)
        elif attr.get_data_format() == tango.DevDouble:
            attr.set_value(float('nan'))

    def write_general(self, attr: tango.WAttribute):
        name = attr.get_name()
        if self.et is None:
            msg = "Write to non initialized device" % self
            self.error_stream(msg)
            self.logger.error(msg)
            #self._reconnect()
            return
        value = attr.get_write_value()
        chan = int(name[-2:])
        ad = name[:2]
        if ad  == 'ao':
            result = self.et.write_AO_channel(chan, value)
        elif ad == 'do':
            result = self.et.write_DO_channel(chan, value)
        else:
            msg = "Write to unknown attribute %s" % name
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
            msg = "Error writing %s" % name
            self.logger.error(msg)
            self.error_stream(msg)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            self._reconnect()

    def _reconnect(self):
        #self.error_count += 1
        if self.time is None:
            self.time = time.time()
        else:
            if time.time() - self.time > self.reconnect_timeout / 1000.0:
                self.error_stream("%s Reconnect timeout exceeded", self)
                self.Reconnect()
                self.time = None

    @command
    def Reconnect(self):
        msg = '%s Reconnecting ...' % self
        self.logger.info(msg)
        self.info_stream(msg)
        self.remove_io()
        self.init_device()
        self.add_io()

    def add_io(self):
        try:
            if self.type == 0:
                msg = '%s Unknown device type' % self
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
                return
            self.info_stream('%s at %s initialization' % (self.et.type, self.ip))
            self.logger.info('%s %s at %s initialization' % (self.get_name(), self.et.type, self.ip))
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
            msg = '%s Error adding IO channels' % self
            self.logger.error(msg)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)

    def remove_io(self):
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
            msg = '%s Error deleting IO channels' % self
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
        try:
            if hasattr(self, 'et') and self.et is not None:
                self.et._client.close()
        except:
            pass
        self.logger = config_logger()
        self.et = None
        self.ip = None
        self.error_count = 0
        self.time = None
        self.reconnect_timeout = int(self.get_device_property('reconnect_timeout', 5000))
        self.type = 0
        self.set_state(DevState.INIT)
        Device.init_device(self)
        # get ip from property
        ip = self.get_device_property('ip', '192.168.1.122')
        # check if ip is in use
        for d in ET7000_Server.devices:
            if d.ip == ip:
                msg = 'ET7000 %s IP address %s is in use' % (hex(self.et._name), ip)
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
                return
        self.ip = ip
        try:
            # create ICP DAS device
            et = ET7000(ip, logger=self.logger)
            self.et = et
            # add device to list
            ET7000_Server.devices.append(self)
            self.type = self.et._name
            msg = 'ET7000 %s at %s has been created' % (self.et.type, ip)
            self.logger.info(msg)
            self.info_stream(msg)
            # check if device type is recognized
            if self.type != 0:
                # set state to running
                self.set_state(DevState.RUNNING)
            else:
                # unknown device type
                msg = 'ET7000 at %s ERROR - unknown device type' % ip
                self.logger.error(msg)
                self.error_stream(msg)
                self.set_state(DevState.FAULT)
        except:
            self.et = None
            self.ip = None
            self.type = 0
            msg = 'ET7000 %s ERROR init device' % self
            self.logger.error(msg)
            self.error_stream(msg)
            self.set_state(DevState.FAULT)

    def delete_device(self):
        try:
            self.et._client.close()
        except:
            pass
        self.et = None
        self.ip = None
        if self in ET7000_Server.devices:
            ET7000_Server.devices.remove(self)
        msg = 'ET7000 %s device has been deleted' % self
        self.logger.info(msg)
        self.info_stream(msg)


def post_init_callback():
    #print('post_init')
    #for dev in ET7000_Server.devices:
    #    if hasattr(dev, 'add_io'):
    #        dev.add_io()
    util = tango.Util.instance()
    devices = util.get_device_list('*')
    for dev in devices:
        #print(dev)
        if hasattr(dev, 'add_io'):
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

if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)
    ET7000_Server.run_server(post_init_callback=post_init_callback)
