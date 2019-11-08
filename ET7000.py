# Используемые библиотеки
import time
from pyModbusTCP.client import ModbusClient

class ET7000:
    AI_ranges = {
        0x00: {
            'min': -0.015,
            'max': 0.015,
            'units': 'V'
        },
        0x01: {
            'min': -0.05,
            'max': 0.05,
            'units': 'V'
        },
        0x02: {
            'min': -0.1,
            'max': 0.1,
            'units': 'V'
        },
        0x03: {
            'min': -0.5,
            'max': 0.5,
            'units': 'V'
        },
        0x04: {
            'min': -1.,
            'max': 1.,
            'units': 'V'
        },
        0x05: {
            'min': -2.5,
            'max': 2.5,
            'units': 'V'
        },
        0x06: {
            'min': -20.0e-3,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x07: {
            'units': 'A',
            'min': 4.0e-3,
            'max': 20.0e-3
        },
        0x08: {
            'units': 'V',
            'min': -10.,
            'max': 10.
        },
        0x09: {
            'units': 'V',
            'min': -5.,
            'max': 5.
        },
        0x0A: {
            'units': 'V',
            'min': -1.,
            'max': 1.
        },
        0x0B: {
            'units': 'V',
            'min': -.5,
            'max': .5
        },
        0x0C: {
            'units': 'V',
            'min': -.15,
            'max': .15
        },
        0x0D: {
            'min': -20.0e-3,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x0E: {
            'units': 'degC',
            'min': -210.0,
            'max': 760.0
        },
        0x0F: {
            'units': 'degC',
            'min': -270.0,
            'max': 1372.0
        },
        0x10: {
            'units': 'degC',
            'min': -270.0,
            'max': 400.0
        },
        0x11: {
            'units': 'degC',
            'min': -270.0,
            'max': 1000.0
        },
        0x12: {
            'units': 'degC',
            'min': 0.0,
            'max': 1768.0
        },
        0x13: {
            'units': 'degC',
            'min': 0.0,
            'max': 1768.0
        },
        0x14: {
            'units': 'degC',
            'min': 0.0,
            'max': 1820.0
        },
        0x15: {
            'units': 'degC',
            'min': -270.0,
            'max': 1300.0
        },
        0x16: {
            'units': 'degC',
            'min': 0.0,
            'max': 2320.0
        },
        0x17: {
            'units': 'degC',
            'min': -200.0,
            'max': 800.0
        },
        0x18: {
            'units': 'degC',
            'min': -200.0,
            'max': 100.0
        },
        0x19: {
            'units': 'degC',
            'min': -200.0,
            'max': 900.0
        },
        0x1A: {
            'min': 0.0,
            'max': 20.0e-3,
            'units': 'A'
        }
    }
    AO_ranges = {
        0x30: {
            'min': 0.0,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x31: {
            'min': 4.0e-3,
            'max': 20.0e-3,
            'units': 'A'
        },
        0x32: {
            'min': 0.0,
            'max': 10.0,
            'units': 'V'
        },
        0x33: {
            'min': -10.0,
            'max': 10.0,
            'units': 'V'
        },
        0x34: {
            'min': 0.0,
            'max': 5.0,
            'units': 'V'
        },
        0x35: {
            'min': -5.0,
            'max': 5.0,
            'units': 'V'
        }
    }
    devices = {
        0x7016: {
        },
        0x7018: {
        },
        0x7026: {
        }
    }

    # default conversion from quanta to real units
    @staticmethod
    def convert(b, amin, amax):
        # обрабатывается 2 случая - минимум нулевой
        if amin == 0 and amax > 0:
            return amax * b / 0xffff
        # и минимум по модулю равен максимуму
        if min == -amax and amax > 0:
            one = 0xffff / 2
            if b <= one:
                return amax * b / one
            else:
                return -amax * (0xffff - b) / one
        # в других случаях ошибка
        return float('nan')

    @staticmethod
    def convert_to_raw(f, amin, amax):
        # обрабатывается 2 случая - минимум нулевой
        if amin == 0 and amax > 0:
            return int(f * 0xffff / amax)
        # и минимум по модулю равен максимуму
        if min == -amax and amax > 0:
            one = 0xffff / 2
            if f > 0.0:
                return int(f * one / amax)
            else:
                return int(0xffff + (f * one / amax))
        # в других случаях ошибка
        return float('nan')

    def __init__(self, host, port=502, timeout=0.15):
        self._host = host
        self._port = port
        self._client = ModbusClient(host=self._host, port=self._port, auto_open=True, auto_close=True, timeout=timeout)
        self._client.open()
        self._name = 0
        self.AI_n = 0
        self.AI_ranges = []
        self.AI_masks = []
        self.channels = []
        # module name
        self._name = self.read_module_name()
        if self._name not in ET7000.devices:
            print('ET7000 device type %s is not supported' % hex(self._name))
        # AIs
        self.AI_time = time.time()
        self.AI_n = 0
        self.AI_ranges = []
        self.AI_masks = []
        self.AI_raw = []
        self.AI_values = []
        self.AI_units = []
        self.AI_n = self.read_AI_n()
        if self.AI_n > 0:
            self.AI_ranges = self.read_AI_ranges()
            self.AI_masks = self.read_AI_masks()
            self.AI_raw = [0 for r in self.AI_ranges]
            self.AI_values = [float('nan') for r in self.AI_ranges]
            self.AI_units = [ET7000.AI_ranges[r]['units'] for r in self.AI_ranges]
        # AOs
        self.AO_time = time.time()
        self.AO_n = 0
        self.AO_ranges = []
        self.AO_raw = []
        self.AO_values = []
        self.AO_units = []
        self.AO_write_raw = []
        self.AO_write = []
        self.AO_write_result = False
        self.AO_n = self.read_AO_n()
        if self.AO_n > 0:
            self.AO_ranges = self.read_AO_ranges()
            self.AO_values = [float('nan') for r in self.AO_ranges]
            self.AO_raw = [0 for r in self.AO_ranges]
            self.AO_units = [ET7000.AO_ranges[r]['units'] for r in self.AO_ranges]
            self.AO_write = [0 for r in self.AO_ranges]
            self.AO_write_raw = [0 for r in self.AO_ranges]
        # DIs
        self.DI_n = 0
        self.DI_values = []
        self.DI_n = self.read_DI_n()
        self.DI_time = time.time()
        self.DI_values = [False] * self.DI_n
        # DOs
        self.DO_time = time.time()
        self.DO_n = 0
        self.DO_values = []
        self.DO_write = []
        self.DO_n = self.read_DO_n()
        self.DO_values = [False] * self.DI_n
        self.DO_write = [False] * self.DI_n

    def read_module_name(self):
        regs = self._client.read_holding_registers(559, 1)
        if regs:
            return regs[0]
        return None

    # AI functions
    def read_AI_n(self):
        regs = self._client.read_input_registers(320, 1)
        self.AI_time = time.time()
        if regs:
            return regs[0]
        return 0

    def read_AI_ranges(self):
        regs = self._client.read_holding_registers(427, self.AI_n)
        return regs

    def read_AI_masks(self):
        coils = self._client.read_coils(595, self.AI_n)
        return coils

    def read_AI_raw(self):
        regs = self._client.read_input_registers(0, self.AI_n)
        self.AI_raw = regs
        self.AI_time = time.time()
        return regs

    def convert_AI(self, raw=None):
        if raw is None:
            raw = self.AI_raw
        for k in range(self.AI_n):
            if self.AI_masks[k]:
                rng = ET7000.AI_ranges[self.AI_ranges[k]]
                self.AI_values[k] = ET7000.convert(raw[k], rng['min'], rng['max'])
            else:
                self.AI_values[k] = float('nan')
        return self.AI_values

    def read_AI(self):
        self.AI_raw = self.read_AI_raw()
        self.convert_AI()
        return self.AI_values

    def read_AI_channel(self, k):
        if self.AI_masks[k]:
            regs = self._client.read_input_registers(0+k, 1)
            self.AI_raw[k] = regs[0]
            rng = ET7000.AI_ranges[self.AI_ranges[k]]
            v = ET7000.convert(regs[0], rng['min'], rng['max'])
        else:
            v = float('nan')
        self.AI_values[k] = v
        return v

    # AO functions
    def read_AO_n(self):
        regs = self._client.read_input_registers(330, 1)
        if regs:
            return regs[0]
        return 0

    def read_AO_ranges(self, n=None):
        if n is None:
            n = self.AO_n
        regs = self._client.read_holding_registers(459, n)
        return regs

    def read_AO_raw(self):
        regs = self._client.read_holding_registers(0, self.AO_n)
        self.AO_raw = regs
        self.AO_time = time.time()
        return regs

    def write_AO_raw(self, regs):
        self.AO_write_raw = regs
        self.AO_write_result = self._client.write_multiple_registers(0, regs)
        self.AO_time = time.time()
        return self.AO_write_result

    def convert_AO(self, raw=None):
        if raw is None:
            raw = self.AO_raw
        for k in range(self.AO_n):
            rng = ET7000.AO_ranges[self.AO_ranges[k]]
            self.AO_values[k] = ET7000.convert(raw[k], rng['min'], rng['max'])
        return self.AO_values

    def convert_to_raw_AO(self, values=None):
        if values is None:
            values = self.AO_values
        answer = []
        for k in range(len(values)):
            rng = ET7000.AO_ranges[self.AO_ranges[k]]
            answer.append(ET7000.convert_to_raw(values[k], rng['min'], rng['max']))
        return answer

    def read_AO(self):
        self.AO_raw = self.read_AO_raw()
        self.convert_AO()
        return self.AO_values

    def read_AO_channel(self, k):
        regs = self._client.read_holding_registers(0+k, 1)
        rng = ET7000.AO_ranges[self.AO_ranges[k]]
        v = ET7000.convert(regs[0], rng['min'], rng['max'])
        self.AO_values[k] = v
        return v

    def write_AO(self, values):
        self.AO_write = values
        regs = ET7000.convert_to_raw_AO(values)
        result = self.write_AO_raw(regs)
        return result

    def write_AO_channel(self, k, value):
        rng = ET7000.AO_ranges[self.AO_ranges[k]]
        reg = ET7000.convert_to_raw(value, rng['min'], rng['max'])
        self.AO_write_raw[k] = reg
        result = self._client.write_single_register(0+k, reg)
        return result

    # DI functions
    def read_DI_n(self):
        regs = self._client.read_input_registers(300, 1)
        if regs:
            return regs[0]
        return 0

    def read_DI(self):
        regs = self._client.read_discrete_inputs(0, self.DI_n)
        self.DI_values = regs
        self._time = time.time()
        return self.DI_values

    def read_DI_channel(self, k):
        reg = self._client.read_discrete_inputs(0+k, 1)
        self._time = time.time()
        return reg[0]

    # DO functions
    def read_DO_n(self):
        regs = self._client.read_input_registers(310, 1)
        self.DO_time = time.time()
        if regs:
            return regs[0]
        return 0

    def read_DO(self):
        regs = self._client.read_coils(0, self.DI_n)
        self.DI_values = regs
        self.DO_time = time.time()
        return self.DI_values

    def read_DO_channel(self, k):
        reg = self._client.read_coils(0+k, 1)
        self.DO_time = time.time()
        return reg[0]

    def write_DO(self, values):
        self.DO_write = values
        self.DO_write_result = self._client.write_multiple_coils(0, values)
        self.DO_time = time.time()
        return self.DO_write_result

    def write_DO_channel(self, k, value):
        result = self._client.write_single_coil(0+k, value)
        self.DO_time = time.time()
        return result

