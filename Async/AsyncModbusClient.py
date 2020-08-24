# -*- coding: utf-8 -*-
import asyncio
import struct

import pyModbusTCP.constants as const
from pyModbusTCP.client import ModbusClient


class AsyncModbusClient(ModbusClient):
    def __init__(self, host=None, port=None, unit_id=None, timeout=None,
                 debug=None, auto_open=None, auto_close=None):
        """Constructor

        Modbus server params (host, port) can be set here or with host(), port()
        functions. Same for debug option.

        Use functions avoid to launch ValueError except if params is incorrect.

        :param host: hostname or IPv4/IPv6 address server address (optional)
        :type host: str
        :param port: TCP port number (optional)
        :type port: int
        :param unit_id: unit ID (optional)
        :type unit_id: int
        :param timeout: socket timeout in seconds (optional)
        :type timeout: float
        :param debug: debug state (optional)
        :type debug: bool
        :param auto_open: auto TCP connect (optional)
        :type auto_open: bool
        :param auto_close: auto TCP close (optional)
        :type auto_close: bool
        :return: Object ModbusClient
        :rtype: ModbusClient
        :raises ValueError: if a set parameter value is incorrect
        """
        # object vars
        self.__hostname = 'localhost'
        self.__port = const.MODBUS_PORT
        self.__unit_id = 1
        self.__timeout = 30.0                # socket timeout
        self.__debug = False                 # debug trace on/off
        self.__auto_open = False             # auto TCP connect
        self.__auto_close = False            # auto TCP close
        self.__mode = const.MODBUS_TCP       # default is Modbus/TCP
        self.__sock = None                   # socket handle
        self.__hd_tr_id = 0                  # store transaction ID
        self.__version = const.VERSION       # version number
        self.__last_error = const.MB_NO_ERR  # last error code
        self.__last_except = 0               # last expect code
        # set host
        if host:
            if not self.host(host):
                raise ValueError('host value error')
        # set port
        if port:
            if not self.port(port):
                raise ValueError('port value error')
        # set unit_id
        if unit_id is not None:
            if self.unit_id(unit_id) is None:
                raise ValueError('unit_id value error')
        # set timeout
        if timeout:
            if not self.timeout(timeout):
                raise ValueError('timeout value error')
        # set debug
        if debug:
            if not self.debug(debug):
                raise ValueError('debug value error')
        # set auto_open
        if auto_open:
            if not self.auto_open(auto_open):
                raise ValueError('auto_open value error')
        # set auto_close
        if auto_close:
            if not self.auto_close(auto_close):
                raise ValueError('auto_close value error')
        super().__init__(host, port, unit_id, timeout, debug, auto_open, auto_close)

    async def async_init(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    def async_read_holding_registers(self, reg_addr, reg_nb=1):
        """Modbus function READ_HOLDING_REGISTERS (0x03)

        :param reg_addr: register address (0 to 65535)
        :type reg_addr: int
        :param reg_nb: number of registers to read (1 to 125)
        :type reg_nb: int
        :returns: registers list or None if fail
        :rtype: list of int or None
        """
        # check params
        if not (0 <= int(reg_addr) <= 65535):
            self.__debug_msg('read_holding_registers(): reg_addr out of range')
            return None
        if not (1 <= int(reg_nb) <= 125):
            self.__debug_msg('read_holding_registers(): reg_nb out of range')
            return None
        if (int(reg_addr) + int(reg_nb)) > 65536:
            self.__debug_msg('read_holding_registers(): read after ad 65535')
            return None
        # build frame
        tx_buffer = self._mbus_frame(const.READ_HOLDING_REGISTERS, struct.pack('>HH', reg_addr, reg_nb))
        # send request
        s_send = await self.async_send_mbus(tx_buffer)
        # check error
        if not s_send:
            return None
        # receive
        f_body = await self.async_recv_mbus()
        # check error
        if not f_body:
            return None
        # check min frame body size
        if len(f_body) < 2:
            self.__last_error = const.MB_RECV_ERR
            self.__debug_msg('read_holding_registers(): rx frame under min size')
            self.close()
            return None
        # extract field "byte count"
        rx_byte_count = struct.unpack('B', f_body[0:1])[0]
        # frame with regs value
        f_regs = f_body[1:]
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if not ((rx_byte_count >= 2 * reg_nb) and
                (rx_byte_count == len(f_regs))):
            self.__last_error = const.MB_RECV_ERR
            self.__debug_msg('read_holding_registers(): rx byte count mismatch')
            self.close()
            return None
        # allocate a reg_nb size list
        registers = [None] * reg_nb
        # fill registers list with register items
        for i, item in enumerate(registers):
            registers[i] = struct.unpack('>H', f_regs[i * 2:i * 2 + 2])[0]
        # return registers list
        return registers

    def async_send_mbus(self, frame):
        try:
            self.writer.write(frame)
            await self.writer.drain()
            return len(frame)
        except:
            return None


    data = await reader.read(100)
    print(f'Received: {data.decode()!r}')

    print('Close the connection')
    writer.close()
    await writer.wait_closed()
