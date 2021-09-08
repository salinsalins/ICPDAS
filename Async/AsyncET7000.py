# Используемые библиотеки
import time
import asyncio

import ET7000
from Async.AsyncModbusClient import AsyncModbusClient


class AsyncET7000(ET7000):

    def __init__(self, host, port=502, timeout=0.15, logger=None):
        super().__init(host, port, timeout, logger)
        self._client.close()
        self.async_client = AsyncModbusClient(host, port, auto_open=True, auto_close=True, timeout=timeout)

    async def async_init(self):
        pass

    async def async_read_module_name(self):
        regs = await self.async_client.read_holding_registers(559, 1)
        if regs and regs[0] != 0:
            return regs[0]
        regs = await self.async_client.read_holding_registers(260, 1)
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

    def read_AO_masks(self):
        return self.AO_masks

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
        if self.AO_masks[k]:
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
            pass
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

    def write_DO_channel(self, k: int, value: bool):
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
