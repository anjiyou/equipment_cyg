import struct

from modbus_tk import defines as modbus_tk_defines
from modbus_tk.modbus_tcp import TcpMaster


class PlcInovance:

    def __init__(self, ip: str, port=502, timeout=5):
        self._ip = ip
        self._port = port
        self._timeout = timeout
        self.master = TcpMaster(ip, port)
        self.master.set_timeout(timeout)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    def communication_open(self):
        self.master.open()

    def communication_close(self):
        self.master.close()

    def read_bool(self, start, length=1) -> bool:
        result = self.master.execute(1, modbus_tk_defines.READ_HOLDING_REGISTERS, start, quantity_of_x=length)
        return bool(result[0])

    def write_bool(self, start, value: bool) -> None:
        write_value = 1 if value else 0
        self.master.execute(1, modbus_tk_defines.WRITE_SINGLE_REGISTER, start, output_value=write_value)

    def read_str(self, start, length) -> str:
        result = self.master.execute(1, modbus_tk_defines.READ_HOLDING_REGISTERS, start, quantity_of_x=length)
        string_value = "".join([chr(value) for value in result])
        return string_value

    def write_str(self, start, value) -> None:
        string_ascii = [ord(char) for char in value]
        self.master.execute(1, modbus_tk_defines.WRITE_MULTIPLE_REGISTERS, start, output_value=string_ascii)

    def read_int(self, start: int, length=1) -> int:
        result = self.master.execute(1, modbus_tk_defines.HOLDING_REGISTERS, start, quantity_of_x=length)
        return result[0]

    def write_int(self, start, value) -> None:
        self.master.execute(1, modbus_tk_defines.WRITE_SINGLE_REGISTER, start, output_value=value)

    def read_float(self, start, length=2) -> float:
        result = self.master.execute(1, modbus_tk_defines.READ_HOLDING_REGISTERS, start, quantity_of_x=length)
        if result:
            high_word, low_word = result
            combined_word = (high_word << 16) + low_word
            float_value = struct.unpack('!f', struct.pack('!I', combined_word))[0]
            return round(float_value, 3)

    def write_float(self, start, value: float) -> None:
        float_bytes = struct.pack('!f', value)
        high_word, low_word = struct.unpack('!HH', float_bytes)
        self.master.execute(1, modbus_tk_defines.WRITE_MULTIPLE_REGISTERS, start, output_value=[high_word, low_word])

    def read_continuous(self, start, length) -> list:
        """连续读多个值."""
        result = self.master.execute(1, modbus_tk_defines.HOLDING_REGISTERS, start, quantity_of_x=length)
        return result

    def write_continuous(self, start, values: list) -> None:
        """如 [10, 200, 300, 400] 写入地址为20的寄存器。那么20: 100, 21:200, 22: 300, 23: 400."""
        self.master.execute(1, modbus_tk_defines.WRITE_MULTIPLE_REGISTERS, start, output_value=values)

    def write_multiple(self, starts: list, values: list) -> None:
        """写入多个地址中多个值，可以写不是连续的地址位."""
        for start in range(len(starts)):
            self.master.execute(1, modbus_tk_defines.WRITE_SINGLE_REGISTER, start + 1, output_value=values[start])
