# Используемые библиотеки
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
        }
    }
    devices = {
        0x7017: {
            'AI': {
                'channels': 8,
                }
            },
            'DO': 4
    }

    class AI:
        def __init__(self, _addr, _min=-10.0, _max=10.0, _units='V'):
            self.addr = _addr  # номер канала АЦП
            # if second argument is dictionary of type range
            try:
                self.min = _min['min']
                self.max = _min['max']
                self.units = _min['units']
                return
            except:
                pass
            self.min = _min  # минимальное значение
            self.max = _max  # максимальное
            self.units = _units

        # default conversion from quanta to real units
        def convert(self, b):
            # обрабатывается 2 случая - минимум нулевой
            if self.min == 0 and self.max > 0:
                return self.max * b / 0xffff
            # и минимум по модулю равен максимуму
            if self.min == -self.max and self.max > 0:
                one = 0xffff / 2
                if b <= one:
                    return self.max * b / one
                else:
                    return -self.max * (0xffff - b) / one
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
        self.init()

    def init(self):
        self._name = self.read_module_name()
        if self._name not in ET7000.devices:
            print('Device %s is not supported' % hex(self._name))
        self.AI_n = self.read_AI_n()
        self.AI_ranges = self.read_AI_range()
        self.AI_masks = self.read_AI_mask()

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

    def read_AI_range(self):
        regs = self._client.read_holding_registers(427, self.AI_n)
        return regs

    def read_AI_mask(self):
        coils = self._client.read_coils(595, self.AI_n)
        return coils

    def read_AI(self):
        regs = self._client.read_input_registers(0, self.AI_n)
        return regs



    def read(self):
        pass
