import asyncio
import json
from uuid import uuid4 as generate_uuid
from jsonrpc.stream_parser import StreamParser


class JSONRPCClient:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._parser = StreamParser()

    async def _wait_for_response(self, reader: asyncio.StreamReader):
        while True:
            data = await reader.read(1024)
            if not data:
                break
            for frame in self._parser.parse(data):
                return frame

    async def send_request(self, method, params):
        self._parser.reset()

        request_id = str(generate_uuid())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        request_data = json.dumps(request).encode('utf-8')

        reader, writer = await asyncio.open_connection(self._host, self._port)

        writer.write(self._parser.pack(request_data))
        await writer.drain()

        frame = await self._wait_for_response(reader)
        writer.close()
        await writer.wait_closed()

        response = json.loads(frame)
        return response


async def main():
    client = JSONRPCClient('localhost', 8888)
    print(await client.send_request('echo', 'hello world'))


if __name__ == '__main__':
    asyncio.run(main())


__all__ = ['JSONRPCClient']
