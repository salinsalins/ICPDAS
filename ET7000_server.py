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

    def read_general(self, attr):
        #self.info_stream("Reading attribute %s", attr.get_name())
        try:
            if self.et is None:
                return
            name = attr.get_name()
            chan = int(name[-2:])
            if name[:2] == 'ai':
                val = self.et.read_AI_channel(chan)
            elif name[:2] == 'di':
                val = self.et.read_DI_channel(chan)
            elif name[:2] == 'do':
                val = self.et.read_DO_channel(chan)
            elif name[:2] == 'ao':
                val = self.et.read_AO_channel(chan)
            else:
                self.error_stream("Read for unknown attribute %s", name)
                return
            attr.set_value(val)
        except Exception as err:
            #print(sys.exc_info())
            #traceback.print_tb(err.__traceback__)
            pass

    def write_general(self, attr, *args, **kwargs):
        #self.info_stream("Writting attribute %s", attr.get_name())
        value = attr.get_write_value()
        if self.et is None:
            return
        name = attr.get_name()
        chan = int(name[-2:])
        if name[:2] == 'ao':
            self.et.write_AO_channel(chan, value)
        elif name[:2] == 'do':
            self.et.write_DO_channel(chan, value)
            #print("Write to %s %s" % (name, str(value)))
        else:
            #print("Write to unknown attribute %s" % name)
            self.error_stream("Write to unknown attribute %s", name)
            return


    def init_device(self):
        print(self)
        Device.init_device(self)
        # build dev proxy
        name = self.get_name()
        dp = tango.DeviceProxy(name)
        self.dev_proxy = dp
        # determine ip address
        pr = dp.get_property('ip')['ip']
        ip = None
        if len(pr) > 0:
            ip = pr[0]
        if ip is None or ip == '':
            ip = '192.168.1.122'
        # check if ip is in use
        for d in ET7000_Server.devices:
            if d.ip == ip:
                print('IP address %s is in use' % ip)
                self.et = None
                self.ip = None
                self.set_state(DevState.DISABLE)
                return
        # create ICP DAS device
        et = ET7000(ip)
        self.et = et
        self.ip = ip
        print('ET%s at %s detected' % (hex(self.et._name)[-4:], ip))
        # initialize ai, ao, di, do attributes
        # ai
        if self.et.AI_n > 0:
            for k in range(self.et.AI_n):
                attr_name = 'ai%02d'%k
                attr = tango.Attr(attr_name, tango.DevDouble, tango.AttrWriteType.READ)
                prop = tango.UserDefaultAttrProp()
                prop.set_unit(self.et.AI_units[k])
                prop.set_display_unit(self.et.AI_units[k])
                prop.set_standard_unit(self.et.AI_units[k])
                prop.set_format('%6.3f')
                rng = ET7000.AI_ranges[self.et.AI_ranges[k]]
                prop.set_min_value(str(rng['min']))
                prop.set_max_value(str(rng['max']))
                attr.set_default_properties(prop)
                self.add_attribute(attr, self.read_general)
            print('%d analog inputs initialized' % self.et.AI_n)
        # ao
        if self.et.AO_n > 0:
            for k in range(self.et.AO_n):
                attr_name = 'ao%02d'%k
                attr = tango.Attr(attr_name, tango.DevDouble, tango.AttrWriteType.READ_WRITE)
                prop = tango.UserDefaultAttrProp()
                prop.set_unit(self.et.AO_units[k])
                prop.set_display_unit(self.et.AO_units[k])
                prop.set_standard_unit(self.et.AO_units[k])
                rng = ET7000.AI_ranges[self.et.AO_ranges[k]]
                prop.set_min_value(str(rng['min']))
                prop.set_max_value(str(rng['max']))
                attr.set_default_properties(prop)
                self.add_attribute(attr, self.read_general, self.write_general)
            print('%d analog inputs initialized' % self.et.AO_n)
        # di
        if self.et.DI_n > 0:
            for k in range(self.et.DI_n):
                attr_name = 'di%02d'%k
                attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ)
                self.add_attribute(attr, self.read_general, w_meth=self.write_general)
            print('%d digital inputs initialized' % self.et.DI_n)
        # do
        if self.et.DO_n > 0:
            for k in range(self.et.DO_n):
                attr_name = 'do%02d'%k
                attr = tango.Attr(attr_name, tango.DevBoolean, tango.AttrWriteType.READ_WRITE)
                self.add_attribute(attr, self.read_general, self.write_general)
            print('%d digital outputs initialized' % self.et.DO_n)

        ET7000_Server.devices.append(self)
        self.set_state(DevState.RUNNING)


if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)

    ET7000_Server.run_server()
