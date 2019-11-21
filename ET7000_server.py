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
            self.error_stream("Read for unknown attribute %s", name)
            return
        attr.set_quality(tango.AttrQuality.ATTR_INVALID)
        if val is not None:
            attr.set_value(val)
            attr.set_quality(tango.AttrQuality.ATTR_VALID)
        else:
            attr.set_quality(tango.AttrQuality.ATTR_INVALID)

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
            self.et.write_AO_channel(chan, value)
        elif ad == 'do':
            self.et.write_DO_channel(chan, value)
        else:
            print("Write to unknown attribute %s" % name)
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
    def Reconnect(self):
        self.set_state(DevState.DISABLE)
        self.et._client.close()
        if self.et is None:
            self.init_device()
            self.add_io()
        else:
            if self.et._name == 0:
                self.et.__init__(self.ip)
                self.add_io()
            else:
                self.et.__init__(self.ip)
        self.set_state(DevState.RUNNING)

    def add_io(self):
        #print(self, ' Initialization')
        if self.et is None:
            return
        print(self, hex(self.et._name), 'at %s initialization' % self.ip)
        self.set_state(DevState.INIT)
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
        print(' ')
        self.set_state(DevState.RUNNING)

    def remove_io(self):
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
        pass

    def init_device(self):
        #print(self, 'init_device')
        if hasattr(self, 'et') and self.et is not None:
            return
        self.set_state(DevState.INIT)
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
                self.set_state(DevState.FAULT)
                return
        # create ICP DAS device
        et = ET7000(ip)
        self.et = et
        self.ip = ip
        # add device
        ET7000_Server.devices.append(self)
        msg = 'ET7000 device type %s at %s has been created' % (hex(self.et._name), ip)
        print(msg)
        self.info_stream(msg)
        # set state to running
        self.set_state(DevState.RUNNING)

def post_init_callback():
    #print('post_init')
    util = tango.Util.instance()
    devices = util.get_device_list('*')
    for dev in devices:
        #print(dev)
        if hasattr(dev, 'add_io'):
            dev.add_io()

if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)
    #util = tango.Util.init(sys.argv)
    #util.add_classes(ET7000_Server)
    #util.server_init()
    #util.server_run()
    ET7000_Server.run_server(post_init_callback=post_init_callback)
