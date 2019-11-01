# Используемые библиотеки
from pyModbusTCP.client import ModbusClient

class ET7000:
    dev = {
        0x7017: {
            'AI': {
                'channels': 8,
                'range': {
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
                    }
                }
            },
            'DO': 4
        }
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

    def __init__(self, host, port=502, timeout=0.15):
        self._host = host
        self._port = port
        self._client = ModbusClient(host=self._host, port=self._port, auto_open=True, auto_close=True, timeout=timeout)
        self.channels = []
        self.module_name = self.read_module_name()

    def read_module_name(self):
        regs = self._client.read_holding_registers(559, 1)
        if regs:
            return regs[0]
        return None

    def read_AI_range(self):
        regs = self._client.read_holding_registers(427, 8)
        coils = self._client.read_coils(595, 8)
        n = 0
        for c in coils:
            if c == 0:
                regs[n] = None
            n += 1
        return regs

    def read(self):
        pass
