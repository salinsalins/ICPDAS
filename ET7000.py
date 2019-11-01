# Используемые библиотеки
from pyModbusTCP.client import ModbusClient

class ET7000:
    AI_ranges = {
        0x00: {
            'units': 'V',
            'min': -0.015,
            'max': 0.015
        },
        0x01: {
            'units': 'V',
            'min': -0.05,
            'max': 0.05
        },
        0x02: {
            'units': 'V',
            'min': -0.1,
            'max': 0.1
        },
        0x03: {
            'units': 'V',
            'min': -0.5,
            'max': 0.5
        },
        0x04: {
            'units': 'V',
            'min': -1.,
            'max': 1.
        },
        0x05: {
            'units': 'V',
            'min': -2.5,
            'max': 2.5
        },
        0x06: {
            'units': 'A',
            'min': -20.0e-3,
            'max': 20.0e-3
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
        def __init__(self, _addr, _min, _max, convert=None):
            self.addr = _addr  # номер канала АЦП
            self.min = _min  # минимальное значение в вольтах
            self.max = _max  # максимальное
            if self.convert is None:
                self.convert = self.AI()
            else:
                self.convert = convert

        # default conversion from int to volts
        def toV(self, b):
            # обрабатывается вусего 2 случая - минимум нулевой
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

    def __init__(self, host, name=None, port=502, timeout=0.15):
        self._host = host
        self._port = port
        self._client = ModbusClient(host=self._host, port=self._port, auto_open=True, auto_close=True, timeout=timeout)
        self.module_name = self.read_module_name()
        if name is not None:
            if self.module_name != name:
                print('ET7000 device is %s not %s'%(hex(self.module_name), hex(name)))
        self.n_AI = self.read_n_AI()

    def read_module_name(self):
        regs = self._client.read_holding_registers(559, 1)
        if regs:
            return regs[0]
        return None

    def read_n_AI(self):
        regs = self._client.read_input_registers(320, 1)
        if regs:
            return regs[0]
        return None

    def read_AI_range(self):
        regs = self._client.read_holding_registers(427, self.n_chan)
        coils = self._client.read_coils(595, self.n_chan)
        n = 0
        for c in coils:
            if c == 0:
                regs[n] = None
            n += 1
        return regs

    def read(self):
        pass
