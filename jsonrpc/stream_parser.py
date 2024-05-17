class StreamParser:
    def __init__(self, sof=0xA5, eof=0x00):
        self._sof = sof
        self._eof = eof
        self._sof_bytes = sof.to_bytes(1, 'big')
        self._eof_bytes = eof.to_bytes(1, 'big')
        self._buffer = b''
        self._state = False

    def parse(self, data):
        i = 0
        for j in range(len(data)):
            if data[j] == self._sof:
                self._buffer = b''
                self._state = True
                i = j + 1
            if data[j] == self._eof and self._state:
                self._buffer += data[i:j]
                self._state = False
                i = j + 1
                yield self._buffer
        if self._state:
            self._buffer += data[i:]

    def pack(self, data):
        return self._sof_bytes + data + self._eof_bytes

    def reset(self):
        self._buffer = b''
        self._state = False


__all__ = ['StreamParser']
