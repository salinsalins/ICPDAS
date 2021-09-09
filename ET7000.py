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
    def convert_from_raw(bit_code, min_code, max_code):
        bit_code = float(bit_code)
        # обрабатывается 2 случая - минимум нулевой или больше 0
        if min_code >= 0 and max_code > 0:
            return min_code + (max_code - min_code) * bit_code / 0xffff
        # и минимум  и максимум разного знака
        if min_code < 0 and max_code > 0:
            range = max(-min_code, max_code)
            if bit_code <= 0x7fff:
                return range * bit_code / 0x7fff
            else:
                return range * (0x8000 - bit_code) / 0x8000
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
        return lambda x: int(k_max * x) if (x >= 0) else int(0xffff - k_min * x)

    @staticmethod
    # Legacy. Did nut used here.
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

    def __init__(self, host: str, port=502, timeout=0.15, logger=None):
        self.host = host
        self.port = port
        # logger config
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        # defaults
        self.name = 0
        self.type = '0000'
        # default ai
        self.ai_n = 0
        self.ai_masks = []
        self.ai_ranges = []
        self.ai_units = []
        self.ai_convert = []
        # default ao
        self.ao_n = 0
        self.ao_masks = []
        self.ao_ranges = []
        self.ao_min = []
        self.ao_max = []
        self.ao_units = []
        self.ao_raw = []
        self.ao_values = []
        self.ao_write_raw_values = []
        self.ao_write_values = []
        self.ao_write_result = False
        # default di
        self.di_n = 0
        self.di_values = []
        # default do
        self.do_n = 0
        self.do_values = []
        # modbus client
        self.client = ModbusClient(host, port, auto_open=True, auto_close=False, timeout=timeout)
        status = self.client.open()
        if not status:
            self.logger.error('ET-7000 device at %s is offline' % host)
            return
        # read module name
        self.name = self.read_module_name()
        self.type = hex(self.name).replace('0x', '')
        if self.name not in ET7000.devices:
            self.logger.warning('Unknown ET-7000 device type %s' % hex(self.name))
        # ai
        self.ai_n = self.ai_read_n()
        self.ai_masks = self.ai_read_masks()
        self.ai_ranges = self.ai_read_ranges()
        self.ai_raw = [0] * self.ai_n
        self.ai_values = [float('nan')] * self.ai_n
        self.ai_units = [''] * self.ai_n
        for i in range(self.ai_n):
            try:
                rng = ET7000.ranges[self.ai_ranges[i]]
            except:
                rng = ET7000.ranges[0xff]
            self.ai_units[i] = rng['units']
            self.ai_convert[i] = ET7000.ai_convert_function(r)
        # ao
        self.ao_n = self.ao_read_n()
        self.ao_masks = [True] * self.ao_n
        self.ao_read_masks()
        self.ao_ranges = [0xff] * self.ao_n
        self.ao_read_ranges()
        self.ao_raw = [0] * self.ao_n
        self.ao_write_raw_values = [0] * self.ao_n
        self.ao_values = [float('nan')] * self.ao_n
        self.ao_write_values = [float('nan')] * self.ao_n
        self.ao_units = [''] * self.ao_n
        self.ao_write = [0] * self.ao_n
        self.ao_convert = [lambda x: x] * self.ai_n
        self.ao_convert_write = [lambda x: 0] * self.ai_n
        for i in range(self.ao_n):
            r = self.ao_ranges[i]
            self.ao_units[i] = ET7000.ranges[r]['units']
            self.ao_convert[i] = ET7000.ai_convert_function(r)  # !!! ai_convert for reading
            self.ao_convert_write[i] = ET7000.ao_convert_function(r)  # !!! ao_convert for writing
        # di
        self.di_n = self.di_read_n()
        self.di_values = [False] * self.di_n
        # do
        self.do_n = self.do_read_n()
        self.do_values = [False] * self.do_n
        self.do_write = [False] * self.do_n

    def read_module_name(self):
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

    def ai_read(self):
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
        return self.ao_masks

    def ao_read_ranges(self):
        regs = self.client.read_holding_registers(459, self.ao_n)
        if regs and len(regs) == self.ao_n:
            self.ao_ranges = regs
        return regs

    def ao_read_raw(self, channel=None):
        if channel is None:
            n = self.ao_n
            channel = 0
        else:
            n = 1
        regs = self.client.read_holding_registers(0 + channel, n)
        if regs and len(regs) == n:
            self.ao_raw[channel:channel + n] = regs
        if n == 1:
            return regs[0]
        return regs

    def ao_write_raw(self, regs):
        result = self.client.write_multiple_registers(0, regs)
        self.ao_write_result = result
        if len(regs) == self.ao_n:
            self.ao_write_raw_values = regs
        return result

    def ao_convert_from_raw(self):
        raw = self.ao_raw
        for k in range(self.ao_n):
            self.ao_values[k] = self.ao_convert[k](raw[k])
        return self.ao_values

    def ao_convert_to_raw(self, values=None):
        if values is None:
            values = self.ao_write_values
        answer = []
        for k in range(len(values)):
            answer.append(self.ao_convert_write[k](values[k]))
        return answer

    def ao_read(self):
        n = self.ao_n
        regs = self.client.read_holding_registers(0, n)
        if regs and len(regs) == n:
            for k in range(n):
                regs[k] = self.ao_convert[k](regs[k])
        else:
            regs = [NaN] * n
        return regs

    def ao_read_channel(self, k: int):
        v = float('nan')
        if self.ao_masks[k]:
            regs = self.client.read_holding_registers(0 + k, 1)
            if regs:
                v = self.ao_convert[k](regs[0])
                self.ao_values[k] = v
        return v

    def ao_write(self, values):
        self.ao_write_values = values
        regs = ET7000.ao_convert_to_raw(values)
        result = self.ao_write_raw_values(regs)
        return result

    def ao_write_channel(self, k: int, value):
        raw = self.ao_convert_write[k](value)
        result = self.client.write_single_register(0 + k, raw)
        self.ao_write_result = result
        if result:
            self.ao_write_values[k] = value
            self.ao_write_raw_values[k] = raw
            pass
        return result

    # DI functions
    def di_read_n(self):
        regs = self.client.read_input_registers(300, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(100, 1)
        if regs:
            return regs[0]
        return 0

    def di_read(self):
        regs = self.client.read_discrete_inputs(0, self.di_n)
        if regs:
            self.di_values = regs
        return self.di_values

    def di_read_channel(self, k: int):
        reg = self.client.read_discrete_inputs(0 + k, 1)
        if reg:
            self.di_values[k] = reg[0]
            return reg[0]
        return None

    # DO functions
    def do_read_n(self):
        self.DO_time = time.time()
        regs = self.client.read_input_registers(310, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = self.client.read_input_registers(110, 1)
        if regs:
            return regs[0]
        return 0

    def do_read(self):
        regs = self.client.read_coils(0, self.di_n)
        if regs:
            self.di_values = regs
        return self.di_values

    def do_read_channel(self, k: int):
        reg = self.client.read_coils(0 + k, 1)
        if reg:
            self.do_values[k] = reg[0]
            return reg[0]
        return None

    def do_write(self, values):
        self.do_write = values
        self.DO_write_result = self.client.write_multiple_coils(0, values)
        return self.DO_write_result

    def do_write_channel(self, k: int, value: bool):
        result = self.client.write_single_coil(0 + k, value)
        self.DO_write_result = result
        if result:
            self.do_write[k] = value
        return result


if __name__ == "__main__":
    for r in ET7000.ranges:
        f = ET7000.ai_convert_function(r)
        if f(ET7000.ranges[r]['min_code']) != ET7000.ranges[r]['min']:
            print(hex(r), hex(ET7000.ranges[r]['min_code']), f(ET7000.ranges[r]['min_code']), ET7000.ranges[r]['min'])
        if f(ET7000.ranges[r]['max_code']) != ET7000.ranges[r]['max']:
            print(hex(r), hex(ET7000.ranges[r]['max_code']), f(ET7000.ranges[r]['max_code']), ET7000.ranges[r]['max'])
    ip = '192.168.1.122'
    et = ET7000(ip)
    if et.name == 0:
        print('ET7000 not found at %s' % ip)
    else:
        print('ET7000 series %s at %s' % (hex(et.name), ip))
        print('----------------------------------------')
        print('%d ai' % et.ai_n)
        et.ai_read()
        for k in range(et.ai_n):
            print(k, hex(et.ai_raw[k]), et.ai_values[k], et.ai_units[k], ' range:', hex(et.ai_ranges[k]))
        print('----------------------------------------')
        print('%d ao' % et.ao_n)
        et.ao_read()
        for k in range(et.ao_n):
            print(k, hex(et.ao_raw[k]), et.ao_values[k], et.ao_units[k], ' range:', hex(et.ao_ranges[k]))
        print('----------------------------------------')
        print('%d di' % et.di_n)
        et.di_read()
        for k in range(et.di_n):
            print(k, et.di_values[k])
        print('----------------------------------------')
        print('%d do' % et.do_n)
        et.do_read()
        for k in range(et.do_n):
            print(k, et.do_values[k])
