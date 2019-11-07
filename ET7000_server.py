#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ICP DAS ET7000 tango device server"""

import sys
import time
import numpy

import tango
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property

from ET7000 import ET7000


class ET7000_Server(Device):

    type = attribute(label="type", dtype=int,
                        display_level=DispLevel.OPERATOR,
                        access=AttrWriteType.READ,
                        unit="", format="%d",
                        doc="ET7000 device type")

    def read_type(self):
        return self.type

    def init_device(self):
        Device.init_device(self)
        self.et = ET7000('192.168.1.122')
        self.type = self.et.AI_n
        print(hex(self.et.AI_n))
        db = tango.Database()
        di = db.get_device_info('et7000_server/test/1')
        print(di)

        self.__current = 0.0
        self.set_state(DevState.STANDBY)


if __name__ == "__main__":
    #if len(sys.argv) < 3:
        #print("Usage: python ET7000_server.py device_name ip_address")
        #exit(-1)

    ET7000_Server.run_server()
