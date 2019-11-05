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
    devices = {
        0x7017: {}
    }

    # default conversion from quanta to real units
    @staticmethod
    def convert(b, min, max):
        # обрабатывается 2 случая - минимум нулевой
        if min == 0 and max > 0:
            return max * b / 0xffff
        # и минимум по модулю равен максимуму
        if min == -max and max > 0:
            one = 0xffff / 2
            if b <= one:
                return max * b / one
            else:
                return -max * (0xffff - b) / one
        # в других случаях ошибка
        return float('nan')

    def __init__(self, host, port=502, timeout=0.15):
        self._host = host
        self._port = port
        self._client = ModbusClient(host=self._host, port=self._port, auto_open=True, auto_close=True, timeout=timeout)
        self._client.open()
        self._name = ''
        self.AI_n = 0
        self.AI_ranges = []
        self.AI_masks = []
        self.channels = []
        # module name
        self._name = self.read_module_name()
        if self._name not in ET7000.devices:
            print('Device %s is not supported' % hex(self._name))
        # AIs
        self.AI_n = self.read_AI_n()
        self.AI_ranges = self.read_AI_ranges()
        self.AI_masks = self.read_AI_masks()

    def read_module_name(self):
        regs = self._client.read_holding_registers(559, 1)
        if regs:
            return regs[0]
        return None

    def read_AI_n(self):
        regs = self._client.read_input_registers(320, 1)
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
        self.AI_values = []
        self.AI_units = []
        for k in range(self.AI_n):
            if self.AI_masks[k]:
                rng = ET7000.AI_ranges[self.AI_ranges[k]]
                self.AI_values.append(ET7000.convert(raw[k], rng['min'], rng['max']))
                self.AI_units.append(rng['units'])
            else:
                self.AI_values.append(float('nan'))
                self.AI_units.append('off')
        return self.AI_values

    def read_AI(self):
        self.read_AI_raw()
        self.convert_AI()
        return self.AI_values

    def read_AI_channel(self, k):
        if not self.AI_masks[k]:
            return float('nan')
        regs = self._client.read_input_registers(0+k, 1)
        self.AI_raw[k] = regs[0]
        rng = ET7000.AI_ranges[self.AI_ranges[k]]
        v = ET7000.convert(regs[0], rng['min'], rng['max'])
        self.AI_values[k] = v
        return v

