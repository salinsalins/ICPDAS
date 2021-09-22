# Используемые библиотеки
import time
import logging
from pyModbusTCP.client import ModbusClient

NaN = float('nan')


class ET7000:
    ranges = {
        0x00: {
            'min': -0.015,
            'max': 0.015,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x01: {
            'min': -0.05,
            'max': 0.05,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x02: {
            'min': -0.1,
            'max': 0.1,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x03: {
            'min': -0.5,
            'max': 0.5,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x04: {
            'min': -1.,
            'max': 1.,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x05: {
            'min': -2.5,
            'max': 2.5,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x06: {
            'min': -20.0e-3,
            'max': 20.0e-3,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'A'
        },
        0x07: {
            'units': 'A',
            'min': 4.0e-3,
            'min_code': 0x0000,
            'max_code': 0xffff,
            'max': 20.0e-3
        },
        0x08: {
            'units': 'V',
            'min': -10.,
            'max': 10.,
            'min_code': 0x8000,
            'max_code': 0x7fff,
        },
        0x09: {
            'units': 'V',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -5.,
            'max': 5.
        },
        0x0A: {
            'units': 'V',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -1.,
            'max': 1.
        },
        0x0B: {
            'units': 'V',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -.5,
            'max': .5
        },
        0x0C: {
            'units': 'V',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -.15,
            'max': .15
        },
        0x0D: {
            'min': -20.0e-3,
            'max': 20.0e-3,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'A'
        },
        0x0E: {
            'units': 'degC',
            'min_code': 0xdca2,
            'max_code': 0x7fff,
            'min': -210.0,
            'max': 760.0
        },
        0x0F: {
            'units': 'degC',
            'min_code': 0xe6d0,
            'max_code': 0x7fff,
            'min': -270.0,
            'max': 1372.0
        },
        0x10: {
            'units': 'degC',
            'min_code': 0xa99a,
            'max_code': 0x7fff,
            'min': -270.0,
            'max': 400.0
        },
        0x11: {
            'units': 'degC',
            'min_code': 0xdd71,
            'max_code': 0x7fff,
            'min': -270.0,
            'max': 1000.0
        },
        0x12: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 1768.0
        },
        0x13: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 1768.0
        },
        0x14: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 1820.0
        },
        0x15: {
            'units': 'degC',
            'min_code': 0xe56b,
            'max_code': 0x7fff,
            'min': -270.0,
            'max': 1300.0
        },
        0x16: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 2320.0
        },
        0x17: {
            'units': 'degC',
            'min_code': 0xe000,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 800.0
        },
        0x18: {
            'units': 'degC',
            'min_code': 0x8000,
            'max_code': 0x4000,
            'min': -200.0,
            'max': 100.0
        },
        0x19: {
            'units': 'degC',
            'min_code': 0xe38e,
            'max_code': 0xffff,
            'min': -200.0,
            'max': 900.0
        },
        0x1A: {
            'min': 0.0,
            'max': 20.0e-3,
            'min_code': 0x0000,
            'max_code': 0xffff,
            'units': 'A'
        },
        0x20: {
            'units': 'degC',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -100.0,
            'max': 100.0
        },
        0x21: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 100.0
        },
        0x22: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 200.0
        },
        0x23: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 600.0
        },
        0x24: {
            'units': 'degC',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -100.0,
            'max': 100.0
        },
        0x25: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 100.0
        },
        0x26: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 200.0
        },
        0x27: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 600.0
        },
        0x28: {
            'units': 'degC',
            'min_code': 0x999a,
            'max_code': 0x7fff,
            'min': -80.0,
            'max': 100.0
        },
        0x29: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 100.0
        },
        0x2A: {
            'units': 'degC',
            'min_code': 0xd556,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 600.0
        },
        0x2B: {
            'units': 'degC',
            'min_code': 0xeeef,
            'max_code': 0x7fff,
            'min': -20.0,
            'max': 150.0
        },
        0x2C: {
            'units': 'degC',
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 200.0
        },
        0x2D: {
            'units': 'degC',
            'min_code': 0xeeef,
            'max_code': 0x7fff,
            'min': -20.0,
            'max': 150.0
        },
        0x2E: {
            'units': 'degC',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 200.0
        },
        0x2F: {
            'units': 'degC',
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 200.0
        },
        0x80: {
            'units': 'degC',
            'min_code': 0xd556,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 600.0
        },
        0x81: {
            'units': 'degC',
            'min_code': 0xd556,
            'max_code': 0x7fff,
            'min': -200.0,
            'max': 600.0
        },
        0x82: {
            'units': 'degC',
            'min_code': 0xd556,
            'max_code': 0x7fff,
            'min': -50.0,
            'max': 150.0
        },
        0x83: {
            'min_code': 0xd556,
            'max_code': 0x7fff,
            'units': 'degC',
            'min': -60.0,
            'max': 180.0
        },
        0x30: {
            'min_code': 0x0000,
            'max_code': 0xffff,
            'min': 0.0,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x31: {
            'min_code': 0x0000,
            'max_code': 0xffff,
            'min': 4.0e-3,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x32: {
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'min': 0.0,
            'max': 10.0,
            'units': 'V'
        },
        0x33: {
            'min': -10.0,
            'max': 10.0,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x34: {
            'min': 0.0,
            'max': 5.0,
            'min_code': 0x0000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0x35: {
            'min': -5.0,
            'max': 5.0,
            'min_code': 0x8000,
            'max_code': 0x7fff,
            'units': 'V'
        },
        0xff: {
            'min': 0,
            'max': 0xffff,
            'min_code': 0x0000,
            'max_code': 0xffff,
            'units': '?'
        }
    }

    @staticmethod
    def ai_convert_function(r):
        v_min = 0
        v_max = 0xffff
        c_min = 0
        c_max = 0xffff
        try:
            v_min = ET7000.ranges[r]['min']
            v_max = ET7000.ranges[r]['max']
            c_min = ET7000.ranges[r]['min_code']
            c_max = ET7000.ranges[r]['max_code']
        except:
            pass
        if c_min < c_max:
            k = float(v_max - v_min) / (c_max - c_min)
            b = v_min - k * c_min
            return lambda x: k * x + b
        k_max = v_max / c_max
        k_min = v_min / (0x10000 - c_min)
        return lambda x: k_max * x if x < 0x8000 else k_min * (0x10000 - x)

    @staticmethod
    def ao_convert_function(r):
        v_min = 0
        v_max = 0xffff
        c_min = 0
        c_max = 0xffff
        try:
            v_min = ET7000.ranges[r]['min']
            v_max = ET7000.ranges[r]['max']
            c_min = ET7000.ranges[r]['min_code']
            c_max = ET7000.ranges[r]['max_code']
        except:
            pass
        # print(hex(r), v_min, v_max, c_min, c_max)
        if c_min < c_max:
            k = (c_max - c_min) / (v_max - v_min)
            b = c_min - k * v_min
            return lambda x: int(k * x + b)
        k_max = c_max / v_max
        k_min = (0xffff - c_min) / v_min
        # return lambda x: int((x >= 0) * k_max * x + (x < 0) * (0xffff - k_min * x))
        return lambda x: int(k_max * x + 0.5) if (x >= 0) else int(0xffff - k_min * x + 0.5)

    def __init__(self, host: str, port=502, timeout=0.15, logger=None, client=ModbusClient):
        self.host = host
        self.port = port
        # logger config
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        # defaults
        self.type = 0
        self.type_str = '0000'
        # default ai
        self.ai_n = 0
        self.ai_masks = []
        self.ai_ranges = []
        self.ai_min = []
        self.ai_max = []
        self.ai_units = []
        # default ao
        self.ao_n = 0
        self.ao_masks = []
        self.ao_ranges = []
        self.ao_min = []
        self.ao_max = []
        self.ao_units = []
        # default di
        self.di_n = 0
        # default do
        self.do_n = 0
        # modbus client
        self.client = client(host, port, auto_open=True, auto_close=False, timeout=timeout)
        self.is_open = self.client.open()
        if not self.is_open:
            self.logger.error('ET-7xxx device at %s is offline' % host)
            return
        # read module type
        self.type = self.read_module_type()
        self.type_str = hex(self.type).replace('0x', '')
        # ai
        self.ai_n = self.ai_read_n()
        self.ai_masks = self.ai_read_masks()
        self.ai_ranges = self.ai_read_ranges()
        self.ai_units = [''] * self.ai_n
        self.ai_convert = [lambda x: x] * self.ai_n
        self.ai_min = [0.0] * self.ai_n
        self.ai_max = [0.0] * self.ai_n
        for i in range(self.ai_n):
            r = self.ai_ranges[i]
            self.ai_units[i] = ET7000.ranges[r]['units']
            self.ai_min[i] = ET7000.ranges[r]['min']
            self.ai_max[i] = ET7000.ranges[r]['max']
            self.ai_convert[i] = ET7000.ai_convert_function(r)
        # ao
        self.ao_n = self.ao_read_n()
        self.ao_masks = self.ao_read_masks()
        self.ao_ranges = self.ao_read_ranges()
        self.ao_units = [''] * self.ao_n
        self.ao_min = [0.0] * self.ao_n
        self.ao_max = [0.0] * self.ao_n
        self.ao_convert = [lambda x: x] * self.ao_n
        self.ao_convert_write = [lambda x: 0] * self.ao_n
        self.ao_quanta = [0.0] * self.ao_n
        for i in range(self.ao_n):
            r = self.ai_ranges[i]
            self.ao_units[i] = ET7000.ranges[r]['units']
            self.ao_min[i] = ET7000.ranges[r]['min']
            self.ao_max[i] = ET7000.ranges[r]['max']
            self.ao_convert[i] = ET7000.ai_convert_function(r)  # !!! ai_convert for reading
            self.ao_convert_write[i] = ET7000.ao_convert_function(r)  # !!! ao_convert for writing
            self.ao_quanta[i] = abs(self.ao_convert[i](1) - self.ao_convert[i](0))
        self.ao_last_written_values = [0.0] * self.ao_n
        self.ao_correct_output = True
        # di
        self.di_n = self.di_read_n()
        # do
        self.do_n = self.do_read_n()
        self.logger.debug('ET-%s at %s has been created' % (self.type_str, host))

    def read_module_type(self):
        regs = self.client.read_holding_registers(559, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_holding_registers(260, 1)
        if regs:
            return regs[0]
        return 0

    # AI functions
    def ai_read_n(self):
        regs = self.client.read_input_registers(320, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(120, 1)
        if regs:
            return regs[0]
        return 0

    def ai_read_masks(self):
        coils = self.client.read_coils(595, self.ai_n)
        if coils and len(coils) == self.ai_n:
            return coils
        return [False] * self.ai_n

    def ai_read_ranges(self):
        regs = self.client.read_holding_registers(427, self.ai_n)
        if regs and len(regs) == self.ai_n:
            return regs
        return [0xff] * self.ai_n

    def ai_read(self, channel=None):
        if channel is not None:
            return self.ai_read_channel(channel)
        n = self.ai_n
        result = self.client.read_input_registers(0, n)
        if result and len(result) == n:
            for i in range(n):
                if self.ai_masks[i]:
                    result[i] = self.ai_convert[i](result[i])
                else:
                    result[i] = NaN
            return result
        else:
            return [NaN] * n

    def ai_read_channel(self, channel: int):
        v = NaN
        try:
            if self.ai_masks[channel]:
                regs = self.client.read_input_registers(0 + channel, 1)
                if regs:
                    v = self.ai_convert[channel](regs[0])
        except:
            pass
        return v

    def ai_write_masks(self, masks):
        return self.client.write_multiple_coils(595, [bool(m) for m in masks])

    def ai_write_ranges(self, data):
        return self.client.write_multiple_registers(427, [int(m) for m in data])

    # AO functions
    def ao_read_n(self):
        regs = self.client.read_input_registers(330, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(130, 1)
        if regs:
            return regs[0]
        return 0

    def ao_read_masks(self):
        return [True] * self.ao_n

    def ao_read_ranges(self):
        regs = self.client.read_holding_registers(459, self.ao_n)
        if regs and len(regs) == self.ao_n:
            return regs
        return [0xff] * self.ao_n

    def ao_read(self, channel=None):
        if channel is not None:
            return self.ao_read_channel(channel)
        n = self.ao_n
        regs = self.client.read_holding_registers(0, n)
        if regs and len(regs) == n:
            for k in range(n):
                regs[k] = self.ao_convert[k](regs[k])
        else:
            regs = [NaN] * n
        return regs

    def ao_read_channel(self, k: int):
        v = NaN
        try:
            if self.ao_masks[k]:
                regs = self.client.read_holding_registers(0 + k, 1)
                if regs:
                    v = self.ao_convert[k](regs[0])
            if self.ao_correct_output:
                # self.logger.debug('%s', abs(self.ao_last_written_values[k] - v) / self.ao_quanta[k])
                if abs(self.ao_last_written_values[k] - v) < self.ao_quanta[k]:
                    v = self.ao_last_written_values[k]
        except:
            pass
        return v

    def ao_write(self, values):
        if len(values) != self.ao_n:
            return False
        regs = [self.ao_convert_write[i](v) for i, v in enumerate(values)]
        result = self.client.write_multiple_registers(0, regs)
        if result:
            return True
        return False

    def ao_write_channel(self, k: int, value):
        raw = self.ao_convert_write[k](float(value))
        result = self.client.write_single_register(0 + k, raw)
        if result:
            self.ao_last_written_values[k] = float(value)
            return True
        return False

    def ao_write_ranges(self, data):
        return self.client.write_multiple_registers(459, [int(m) for m in data])

    # DI functions
    def di_read_n(self):
        regs = self.client.read_input_registers(300, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(100, 1)
        if regs:
            return regs[0]
        return 0

    def di_read(self, channel=None):
        if channel is not None:
            return self.di_read_channel(channel)
        regs = self.client.read_discrete_inputs(0, self.di_n)
        if regs and len(regs) == self.di_n:
            return regs
        return [None] * self.di_n

    def di_read_channel(self, k: int):
        reg = self.client.read_discrete_inputs(0 + k, 1)
        if reg:
            return reg[0]
        return None

    # DO functions
    def do_read_n(self):
        regs = self.client.read_input_registers(310, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(110, 1)
        if regs:
            return regs[0]
        return 0

    def do_read(self, channel=None):
        if channel is not None:
            return self.do_read_channel(channel)
        regs = self.client.read_coils(0, self.do_n)
        if regs and len(regs) == self.do_n:
            return regs
        return [None] * self.do_n

    def do_read_channel(self, k: int):
        reg = self.client.read_coils(0 + k, 1)
        if reg:
            return reg[0]
        return None

    def do_write(self, values):
        result = self.client.write_multiple_coils(0, values)
        if result:
            return True
        return False

    def do_write_channel(self, k: int, value: bool):
        result = self.client.write_single_coil(0 + k, value)
        if result:
            return result
        return False

    def read_modbus(self, addr, n):
        if addr >= 40000:
            return self.client.read_holding_registers(addr - 40000, n)
        if addr >= 30000:
            return self.client.read_input_registers(addr - 30000, n)
        if addr >= 20000:
            return None
        if addr >= 10000:
            return self.client.read_discrete_inputs(addr - 10000, n)
        if addr >= 0:
            return self.client.read_coils(addr, n)
        return None

    def write_modbus(self, addr, v):
        if addr >= 40000:
            return self.client.write_multiple_registers(addr - 40000, v)
        if addr >= 30000:
            return False
        if addr >= 20000:
            return False
        if addr >= 10000:
            return False
        if addr >= 0:
            return self.client.write_multiple_coils(addr, v)
        return False


class FakeET7000(ET7000):
    class _client:
        def __init__(self, host, *args, **kwargs):
            self.is_open = False
            self.count = 0
            self.holding_registers = [0] * 6
            self.coils = [True] * 6
            self.data = {
                40559: 0x7026,
                30320: 6,
                595: True, 596: True, 597: True, 598: True, 599: True, 600: True,
                40427: 4, 40428: 4, 40429: 4, 40430: 4, 40431: 4, 40432: 4,
                30000: 0, 30001: 1, 30002: 2, 30003: 3, 30004: 4, 30005: 5,
                30330: 1,
                40459: 0x33,
                40000: 0, 40001: 0, 40002: 0, 40003: 0, 40004: 0, 40005: 0,
                30300: 2,
                30310: 2,
                10000: 0, 10001: 1,
                0: 0, 1: 1,
            }

        def new_count(self):
            self.count += 1
            if self.count == 0x8000:
                self.count = 0
            return self.count

        def modbus_read(self, prefix, n, m):
            result = []
            for i in range(m):
                result.append(self.data[prefix + n + i])
            return result

        def modbus_write(self, prefix, n, m, values):
            for i in range(m):
                self.data[prefix + n + i] = values[i]
            return True

        def read_holding_registers(self, n, m):
            return self.modbus_read(40000, n, m)
            # if n in self.data:
            #     return [self.data[n]] * m
            # return self.holding_registers[n:n+m]

        def read_input_registers(self, n, m):
            return self.modbus_read(30000, n, m)
            # if n in self.data:
            #     return [self.data[n]] * m
            # return [self.new_count() for i in range(m)]

        def read_coils(self, n, m):
            return self.modbus_read(0, n, m)
            # if n in self.data:
            #     return [self.data[n]] * m
            # return self.coils[:m]

        def write_single_register(self, n, v):
            return self.modbus_write(40000, n, 1, [v])
            # if n < 6:
            #     self.holding_registers[n] = v
            # return True

        def write_multiple_registers(self, n, v):
            return self.modbus_write(40000, n, len(v), v)
            # n2 = n + len(m)
            # if n < 6 and n2 < 6:
            #     self.holding_registers[n:n2] = m
            # return True

        def write_single_coil(self, n, v):
            return self.modbus_write(0, n, 1, [v])
            # if n < 6:
            #     self.coils[n] = bool(m)
            # return True

        def write_multiple_coils(self, n, v):
            return self.modbus_write(0, n, len(v), v)
            # n2 = n + len(m)
            # if n < 6 and n2 < 6:
            #     self.coils[n:n2] = m
            # return True

        def read_discrete_inputs(self, n, m):
            return self.modbus_read(10000, n, m)
            # return [True] * m

        def auto_close(self, x):
            return x

        def open(self):
            self.is_open = True
            return self.is_open

        def close(self):
            self.is_open = False
            return self.is_open

    def __init__(self, host, port=502, timeout=0.15, logger=None, client=_client):
        super().__init__(host, port=port, timeout=timeout, logger=logger, client=FakeET7000._client)
        self.type_str = 'Emulated ' + self.type_str

if __name__ == "__main__":
    for r in ET7000.ranges:
        f = ET7000.ai_convert_function(r)
        if f(ET7000.ranges[r]['min_code']) != ET7000.ranges[r]['min']:
            print(hex(r), hex(ET7000.ranges[r]['min_code']), f(ET7000.ranges[r]['min_code']), '!=', ET7000.ranges[r]['min'])
        if f(ET7000.ranges[r]['max_code']) != ET7000.ranges[r]['max']:
            print(hex(r), hex(ET7000.ranges[r]['max_code']), f(ET7000.ranges[r]['max_code']), '!=', ET7000.ranges[r]['max'])
    #
    ip = '192.168.1.122'
    et = ET7000(ip)
    if et.type == 0:
        print('ET7000 not found at %s' % ip)
    else:
        print('ET7000 series %s at %s' % (et.type_str, ip))
        print('----------------------------------------')
        print('%d ai' % et.ai_n)
        v = et.ai_read()
        for k in range(et.ai_n):
            print(k, v[k], et.ai_units[k], ' range:', hex(et.ai_ranges[k]))
        print('----------------------------------------')
        print('%d ao' % et.ao_n)
        v = et.ao_read()
        for k in range(et.ao_n):
            print(k, v[k], et.ao_units[k], ' range:', hex(et.ao_ranges[k]))
        print('----------------------------------------')
        print('%d di' % et.di_n)
        v = et.di_read()
        for k in range(et.di_n):
            print(k, v[k])
        print('----------------------------------------')
        print('%d do' % et.do_n)
        v = et.do_read()
        for k in range(et.do_n):
            print(k, et.v[k])
