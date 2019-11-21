# Используемые библиотеки
import time
import logging
from pyModbusTCP.client import ModbusClient

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
    devices = {
        0x7015: {
        },
        0x7016: {
        },
        0x7018: {
        },
        0x7060: {
        },
        0x7026: {
        }
    }

    @staticmethod
    def range(r):
        if r in ET7000.ranges:
            return (ET7000.ranges[r])
        return ET7000.ranges[0xff]

    # default conversion from quanta to real units
    @staticmethod
    def convert(b, amin, amax):
        b = float(b)
        # обрабатывается 2 случая - минимум нулевой или больше 0
        if amin >= 0 and amax > 0:
            return amin + (amax - amin) * b / 0xffff
        # и минимум  и максимум разного знака
        if amin < 0 and amax > 0:
            range = max(-amin, amax)
            if b <= 0x7fff:
                return range * b / 0x7fff
            else:
                return range * (0x8000 - b) / 0x8000
        # в других случаях ошибка
        return float('nan')

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
            k = (v_max - v_min) / (c_max - c_min)
            b = v_min - k * c_min
            return  lambda x: k * x + b
        k_max = v_max / c_max
        k_min = v_min / (0x10000 - c_min)
        return lambda x: (x < 0x8000) * k_max * x + (x >= 0x8000) *  k_min * (0x10000 - x)

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
        #print(hex(r), v_min, v_max, c_min, c_max)
        if c_min < c_max:
            k = (c_max - c_min) / (v_max - v_min)
            b = c_min - k * v_min
            return  lambda x: k * x + b
        k_max = c_max / v_max
        k_min = (0xffff - c_min) / v_min
        return lambda x: (x >= 0) * k_max * x + (x < 0) * (0xffff - k_min * x)

    @staticmethod
    def convert_to_raw(v, amin, amax):
        v = float(v)
        # обрабатывается 2 случая - минимум нулевой или больше 0
        if amin >= 0 and amax > 0:
            return int((v - amin) / (amax - amin) * 0xffff)
        # и минимум  и максимум разного знака
        if amin < 0 and amax > 0:
            if v >= 0.0:
                return int(v * 0x7fff / amax)
            else:
                return int(0x8000 - v / amax * 0x7fff)
        # в других случаях ошибка
        return 0

    def __init__(self, host, port=502, timeout=0.15, logger=None):
        # logger confid
        if logger is None:
            logger = logging.getLogger(__name__)
        # default device type
        self._name = 0
        # default ai
        self.AI_n = 0
        self.AI_masks = []
        self.AI_ranges = []
        self.AI_min = []
        self.AI_max = []
        self.AI_units = []
        self.AI_raw = []
        self.AI_values = []
        # default ao
        self.AO_n = 0
        self.AO_ranges = []
        self.AO_min = []
        self.AO_max = []
        self.AO_units = []
        self.AO_raw = []
        self.AO_values = []
        self.AO_write_raw = []
        self.AO_write_values = []
        self.AO_write_result = False
        # default di
        self.DI_n = 0
        self.DI_values = []
        # default do
        self.DO_n = 0
        self.DO_values = []
        # modbus client
        self._client = ModbusClient(host, port, auto_open=True, auto_close=True, timeout=timeout)
        status = self._client.open()
        if not status:
            #print('ET7000 device at %s is offline' % host)
            logger.error('ET7000 device at %s is offline' % host)
            return
        # read module name
        self._name = self.read_module_name()
        if self._name not in ET7000.devices:
            #print('ET7000 device type %s probably not supported' % hex(self._name))
            logger.warning('ET7000 device type %s probably not supported' % hex(self._name))
        # ai
        self.AI_n = self.read_AI_n()
        self.AI_masks = [False] * self.AI_n
        self.AI_ranges = [0xff] * self.AI_n
        self.AI_raw = [0] * self.AI_n
        self.AI_values = [float('nan')] * self.AI_n
        self.AI_units = [''] * self.AI_n
        self.read_AI_masks()
        self.read_AI_ranges()
        self.AI_convert = [lambda x: x] * self.AI_n
        for n in range(self.AI_n):
            r = self.AI_ranges[n]
            self.AI_units[n] = ET7000.ranges[r]['units']
            self.AI_convert[n] = ET7000.ai_convert_function(r)
        # ao
        self.AO_n = self.read_AO_n()
        self.AO_ranges = [0xff] * self.AO_n
        self.AO_raw = [0] * self.AO_n
        self.AO_values = [float('nan')] * self.AO_n
        self.AO_units = [''] * self.AO_n
        self.AO_write = [0] * self.AO_n
        self.AO_write_raw = [0] * self.AO_n
        self.read_AO_ranges()
        self.AO_convert = [lambda x: x] * self.AI_n
        self.AO_convert_write = [lambda x: 0] * self.AI_n
        for n in range(self.AO_n):
            r = self.AO_ranges[n]
            self.AO_units[n] = ET7000.ranges[r]['units']
            self.AO_convert[n] = ET7000.ai_convert_function(r) # !!! ai_convert for reading
            self.AO_convert_write[n] = ET7000.ao_convert_function(r)  # !!! ao_convert for writing
        # di
        self.DI_n = self.read_DI_n()
        self.DI_values = [False] * self.DI_n
        # do
        self.DO_n = self.read_DO_n()
        self.DO_values = [False] * self.DO_n
        self.DO_write = [False] * self.DO_n

    def read_module_name(self):
        regs = self._client.read_holding_registers(559, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self._client.read_holding_registers(260, 1)
        if regs:
            return regs[0]
        return 0

    # AI functions
    def read_AI_n(self):
        regs = self._client.read_input_registers(320, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self._client.read_input_registers(120, 1)
        if regs:
            return regs[0]
        return 0

    def read_AI_masks(self):
        coils = self._client.read_coils(595, self.AI_n)
        if coils and len(coils) == self.AI_n:
            self.AI_masks = coils
        return coils

    def read_AI_ranges(self):
        regs = self._client.read_holding_registers(427, self.AI_n)
        if regs and len(regs) == self.AI_n:
            self.AI_ranges = regs
        return regs

    def read_AI_raw(self, channel=None):
        if channel is None:
            n = self.AI_n
            channel = 0
        else:
            n = 1
        regs = self._client.read_input_registers(0+channel, n)
        if regs and len(regs) == n:
            self.AI_raw[channel:channel+n] = regs
        if n == 1:
            return regs[0]
        return regs

    def convert_AI(self):
        for k in range(self.AI_n):
            if self.AI_masks[k]:
                self.AI_values[k] = self.AI_convert[k](self.AI_raw[k])
            else:
                self.AI_values[k] = float('nan')
        return self.AI_values

    def read_AI(self, channel=None):
        if channel is None:
            self.read_AI_raw()
            self.convert_AI()
            return self.AI_values
        return self.read_AI_channel(channel)

    def read_AI_channel(self, k:int):
        v = float('nan')
        if self.AI_masks[k]:
            regs = self._client.read_input_registers(0+k, 1)
            if regs:
                self.AI_raw[k] = regs[0]
                v = self.AI_convert[k](regs[0])
        self.AI_values[k] = v
        return v

    # AO functions
    def read_AO_n(self):
        regs = self._client.read_input_registers(330, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self._client.read_input_registers(130, 1)
        if regs:
            return regs[0]
        return 0

    def read_AO_ranges(self):
        regs = self._client.read_holding_registers(459, self.AO_n)
        if regs and len(regs) == self.AO_n:
            self.AO_ranges = regs
        return regs

    def read_AO_raw(self, channel=None):
        if channel is None:
            n = self.AO_n
            channel = 0
        else:
            n = 1
        regs = self._client.read_holding_registers(0+channel, n)
        if regs and len(regs) == n:
            self.AO_raw[channel:channel+n] = regs
        if n == 1:
            return regs[0]
        return regs

    def write_AO_raw(self, regs):
        result = self._client.write_multiple_registers(0, regs)
        self.AO_write_result = result
        if len(regs) == self.AO_n:
            self.AO_write_raw = regs
        return result

    def convert_AO(self):
        raw = self.AO_raw
        for k in range(self.AO_n):
            self.AO_values[k] = self.AO_convert[k](raw[k])
        return self.AO_values

    def convert_to_raw_AO(self, values=None):
        if values is None:
            values = self.AO_write_values
        answer = []
        for k in range(len(values)):
            answer.append(self.AO_convert_write[k](values[k]))
        return answer

    def read_AO(self):
        self.AO_raw = self.read_AO_raw()
        self.convert_AO()
        return self.AO_values

    def read_AO_channel(self, k: int):
        v = float('nan')
        regs = self._client.read_holding_registers(0+k, 1)
        if regs:
            v = self.AO_convert[k](regs[0])
            self.AO_values[k] = v
        return v

    def write_AO(self, values):
        self.AO_write_values = values
        regs = ET7000.convert_to_raw_AO(values)
        result = self.write_AO_raw(regs)
        return result

    def write_AO_channel(self, k: int, value):
        raw = self.AO_convert_write[k](value)
        result = self._client.write_single_register(0+k, raw)
        self.AO_write_result = result
        if result:
            self.AO_write_values[k] = value
            self.AO_write_raw[k] = raw
        return result

    # DI functions
    def read_DI_n(self):
        regs = self._client.read_input_registers(300, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self._client.read_input_registers(100, 1)
        if regs:
            return regs[0]
        return 0

    def read_DI(self):
        regs = self._client.read_discrete_inputs(0, self.DI_n)
        if regs:
            self.DI_values = regs
        return self.DI_values

    def read_DI_channel(self, k: int):
        reg = self._client.read_discrete_inputs(0+k, 1)
        if reg:
            self.DI_values[k] = reg[0]
            return reg[0]
        return None

    # DO functions
    def read_DO_n(self):
        self.DO_time = time.time()
        regs = self._client.read_input_registers(310, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self._client.read_input_registers(110, 1)
        if regs:
            return regs[0]
        return 0

    def read_DO(self):
        regs = self._client.read_coils(0, self.DI_n)
        if regs:
            self.DI_values = regs
        return self.DI_values

    def read_DO_channel(self, k: int):
        reg = self._client.read_coils(0+k, 1)
        if reg:
            self.DO_values[k] = reg[0]
            return reg[0]
        return None

    def write_DO(self, values):
        self.DO_write = values
        self.DO_write_result = self._client.write_multiple_coils(0, values)
        return self.DO_write_result

    def write_DO_channel(self, k, value: bool):
        result = self._client.write_single_coil(0+k, value)
        self.DO_write_result = result
        if result:
            self.DO_write[k] = value
        return result

if __name__ == "__main__":
    for r in ET7000.ranges:
        f = ET7000.ai_convert_function(r)
        if f(ET7000.ranges[r]['min_code']) != ET7000.ranges[r]['min']:
            print(hex(r), hex(ET7000.ranges[r]['min_code']), f(ET7000.ranges[r]['min_code']),  ET7000.ranges[r]['min'])
        if f(ET7000.ranges[r]['max_code']) != ET7000.ranges[r]['max']:
            print(hex(r), hex(ET7000.ranges[r]['max_code']), f(ET7000.ranges[r]['max_code']), ET7000.ranges[r]['max'])
    ip = '192.168.1.122'
    et = ET7000(ip)
    if et._name == 0:
        print('ET7000 not found at %s' % ip)
    else:
        print('ET7000 series %s at %s' % (hex(et._name), ip))
        print('----------------------------------------')
        print('%d ai' % et.AI_n)
        et.read_AI()
        for k in range(et.AI_n):
            print(k, hex(et.AI_raw[k]), et.AI_values[k], et.AI_units[k], ' range:', hex(et.AI_ranges[k]))
        print('----------------------------------------')
        print('%d ao' % et.AO_n)
        et.read_AO()
        for k in range(et.AO_n):
            print(k, hex(et.AO_raw[k]), et.AO_values[k], et.AO_units[k], ' range:', hex(et.AO_ranges[k]))
        print('----------------------------------------')
        print('%d di' % et.DI_n)
        et.read_DI()
        for k in range(et.DI_n):
            print(k, et.DI_values[k])
        print('----------------------------------------')
        print('%d do' % et.DO_n)
        et.read_DO()
        for k in range(et.DO_n):
            print(k, et.DO_values[k])
