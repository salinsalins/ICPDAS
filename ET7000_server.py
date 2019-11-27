#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""

import sys
import time
import numpy
import traceback

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
                        doc="ET7000 device type")

    def read_devicetype(self):
        t = hex(self.et._name)[-4:]
        return t

    def read_general(self, attr: tango.Attribute):
        #print("Reading attribute %s %s" % (self.ip, attr.get_name()))
        #self.info_stream("Reading attribute %s", attr.get_name())
        if self.et is None:
            return
        name = attr.get_name()
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
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            self.error_stream("Read for unknown attribute %s", name)
            return
        if val is not None:
            self.time = None
            self.error_count = 0
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            self.error_count += 1
            self.error_stream("Error reading %s", name)
            if ad == 'ai':
                attr.set_value(float('nan'))
            elif ad == 'ao':
                attr.set_value(float('nan'))
            elif ad == 'di':
                attr.set_value(False)
            elif ad == 'do':
                attr.set_value(False)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            if self.time is None:
                self.time = time.time()
            else:
                if time.time() - self.time > self.reconnect_timeout/1000.0:
                    self.error_stream("Reconnect timeout exceeded for %s", name)
                    self.Reconnect()
                    self.time = None

    def write_general(self, attr: tango.WAttribute):
        #print("Writing attribute %s %s" % (self.ip, attr.get_name()))
        #self.info_stream("Writing attribute %s", attr.get_name())
        if self.et is None:
            return
        #attr.set_quality(tango.AttrQuality.ATTR_CHANGING)
        #lst = []
        value = attr.get_write_value()
        #print(value, lst)
        name = attr.get_name()
        chan = int(name[-2:])
        ad = name[:2]
        if ad  == 'ao':
            #print(chan, value)
            result = self.et.write_AO_channel(chan, value)
        elif ad == 'do':
            result = self.et.write_DO_channel(chan, value)
        else:
            print("Write to unknown attribute %s" % name)
            self.error_stream("Write to unknown attribute %s", name)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            return
        if result:
            self.time = None
            self.error_count = 0
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            self.error_count += 1
            self.error_stream("Error writing %s", name)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            if self.time is None:
                self.time = time.time()
            else:
                if time.time() - self.time > self.reconnect_timeout/1000.0:
                    self.error_stream("Reconnect timeout exceeded for %s", name)
                    self.Reconnect()
                    self.time = None

    @command
    def Reconnect(self):
        self.info_stream(self, 'Reconnect')
        if self.et is None:
            self.init_device()
            if self.et is None:
                return
        self.remove_io()
        self.add_io()
        # if device type is recognized
        if self.et._name != 0:
            # set state to running
            self.set_state(DevState.RUNNING)
        else:
            # unknown device type
            self.set_state(DevState.FAULT)

    def add_io(self):
        #self.info_stream(self, 'ddd_io')
        if self.et is None:
            return
        self.info_stream('%s at %s initialization' % (hex(self.et._name), self.ip))
        print(self, hex(self.et._name), 'at %s initialization' % self.ip)
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
            print('%d analog inputs initialized' % self.et.AI_n)
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
            print('%d analog outputs initialized' % self.et.AO_n)
            self.info_stream('%d analog outputs initialized' % self.et.AO_n)
        # di
        if self.et.DI_n > 0:
            for k in range(self.et.DI_n):
                attr_name = 'di%02d'%k
                attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ)
                self.add_attribute(attr, self.read_general, w_meth=self.write_general)
            print('%d digital inputs initialized' % self.et.DI_n)
            self.info_stream('%d digital inputs initialized' % self.et.DI_n)
        # do
        if self.et.DO_n > 0:
            for k in range(self.et.DO_n):
                attr_name = 'do%02d'%k
                attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ_WRITE)
                self.add_attribute(attr, self.read_general, self.write_general)
            print('%d digital outputs initialized' % self.et.DO_n)
            self.info_stream('%d digital outputs initialized' % self.et.DO_n)
        self.set_state(DevState.RUNNING)

    def remove_io(self):
        #self.info_stream(self, 'remove_io')
        #print(self, 'remove_io')
        if self.et is None:
            return
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
            return result

    def init_device(self):
        if hasattr(self, 'et') and self.et is not None:
            self.et._client.close()
            self.et = None
            self.ip = None
            #return
        self.set_state(DevState.INIT)
        Device.init_device(self)
        # get ip from property
        ip = self.get_device_property('ip', '192.168.1.122')
        # check if ip is in use
        for d in ET7000_Server.devices:
            if d.ip == ip:
                print('IP address %s is in use' % ip)
                self.error_stream('IP address %s is in use' % ip)
                self.et = None
                self.ip = None
                self.set_state(DevState.FAULT)
                return
        # create ICP DAS device
        et = ET7000(ip)
        self.et = et
        self.ip = ip
        # create variables
        self.error_count = 0
        self.time = None
        self.reconnect_timeout = int(self.get_device_property('reconnect_timeout', 5000))
        # add device to list
        ET7000_Server.devices.append(self)
        msg = 'ET7000 device type %s at %s has been created' % (hex(self.et._name), ip)
        print(msg)
        self.info_stream(msg)
        # if device type is recognized
        if self.et._name != 0:
            # set state to running
            self.set_state(DevState.RUNNING)
        else:
            # unknown device type
            self.set_state(DevState.FAULT)

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
            print(' ')

if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)
    ET7000_Server.run_server(post_init_callback=post_init_callback)
