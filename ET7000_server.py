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
            self.error_stream("Read for unknown attribute %s", name)
            return
        attr.set_quality(tango.AttrQuality.ATTR_INVALID)
        if val is not None:
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)

    def write_general(self, attr: tango.WAttribute):
        #self.info_stream("Writting attribute %s", attr.get_name())
        if self.et is None:
            return
        attr.set_quality(tango.AttrQuality.ATTR_CHANGING)
        value = attr.get_write_value()
        name = attr.get_name()
        chan = int(name[-2:])
        ad = name[:2]
        if ad  == 'ao':
            self.et.write_AO_channel(chan, value)
        elif ad == 'do':
            self.et.write_DO_channel(chan, value)
        else:
            #print("Write to unknown attribute %s" % name)
            self.error_stream("Write to unknown attribute %s", name)
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)
            return
        attr.set_quality(tango.AttrQuality.ATTR_VALID)

    def write_ao(self, attr):
        if self.et is None:
            return
        value = attr.get_write_value()
        name = attr.get_name()
        chan = int(name[-2:])
        self.et.write_AO_channel(chan, value)

    @command
    def Init(self):
        #self.set_state(DevState.OFF)
        print(self, ' Initialization')
        if self.et is None:
            return
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

    def init_device(self):
        print(self, 'init_device')
        if hasattr(self, 'et') and self.et is not None:
            print('skip')
            return
        Device.init_device(self)
        # build dev proxy
        name = self.get_name()
        dp = tango.DeviceProxy(name)
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
                self.error_stream('IP address %s is in use' % ip)
                self.et = None
                self.ip = None
                self.set_state(DevState.DISABLE)
                return
        # create ICP DAS device
        et = ET7000(ip)
        self.et = et
        self.ip = ip
        print('ET%s at %s detected' % (hex(self.et._name)[-4:], ip))
        # da = self.get_device_attr()
        # print(da)
        # n = da.get_attr_nb()
        # print(n)
        # for k in range(n):
        #     a = da.get_attr_by_ind(k)
        #     an = a.get_name()
        #     print(an)
        #     if an[:2] == 'ai' or an[:2] == 'ao' or an[:2] == 'di' or an[:2] == 'do':
        #         print('removing ', an)
        #         try:
        #             self.remove_attribute(an)
        #         except Exception as exc:
        #             print(str(exc))
        #             self.__class__.remove_attribute(self.__class__, an)
        #             print('ok')
        # cl = self.get_device_class()
        # print(cl)
        # am = cl.dyn_att_added_methods
        # print(am)


        # initialize ai, ao, di, do attributes

        ET7000_Server.devices.append(self)
        self.set_state(DevState.RUNNING)


if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)

    ET7000_Server.run_server()
