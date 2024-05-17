import asyncio
import json
from jsonrpc.stream_parser import StreamParser


class JSONRPCRequestHandler:
    def __init__(self):
        self._methods = {}

    def register(self, method_name: str, callback):
        self._methods[method_name] = callback

    @staticmethod
    def _validate_request(request):
        if not isinstance(request, dict):
            return False
        if "jsonrpc" not in request or not isinstance(request['jsonrpc'], str) or request['jsonrpc'] != "2.0":
            return False
        if "method" not in request or not isinstance(request['method'], str):
            return False
        return True

    @staticmethod
    def _get_method_and_params(request):
        return request["method"], request.get("params", None)

    @staticmethod
    async def _call_method(method, params):
        if asyncio.iscoroutinefunction(method):
            return await method(params)
        else:
            return await asyncio.to_thread(method, params)

    async def _handle_notification(self, request):
        method_name, params = self._get_method_and_params(request)

        method = self._methods.get(method_name, None)
        if method:
            try:
                await self._call_method(method, params)
            except TypeError:
                pass
            except RuntimeError:
                pass

    async def _handle_call(self, request):
        method_name, params = self._get_method_and_params(request)

        response = {
            "jsonrpc": "2.0",
            "id": request["id"]
        }

        method = self._methods.get(method_name, None)
        if method:
            try:
                result = await self._call_method(method, params)
            except TypeError:
                response["error"] = {"code": -32602, "message": "Invalid params"}
            except RuntimeError:
                response["error"] = {"code": -32603, "message": "Internal error"}
            else:
                response["result"] = result
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}
        return response

    async def _handle_request(self, request):
        if self._validate_request(request):
            if "id" in request:
                response = await self._handle_call(request)
            else:
                await self._handle_notification(request)
                response = None
        else:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": None
            }
        return response

    async def _handle_frame(self, frame):
        try:
            request = json.loads(frame)
            if isinstance(request, list):
                if request:
                    response = list(filter(lambda x: x is not None, asyncio.gather(*[self._handle_request(i) for i in request])))
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32600, "message": "Invalid Request"},
                        "id": None
                    }
            else:
                response = await self._handle_request(request)

        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }

        if response:
            try:
                response_data = json.dumps(response).encode()
            except json.JSONDecodeError:
                response_data = json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Internal error"},
                    "id": None
                }).encode()
            return response_data
        return b''

    async def __call__(self, reader, writer):
        parser = StreamParser()
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                for frame in parser.parse(data):
                    response_frame = parser.pack(await self._handle_frame(frame))
                    writer.write(response_frame)
                    await writer.drain()
        except ConnectionResetError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()


async def echo(param):
    return param


async def main():
    request_handler = JSONRPCRequestHandler()
    request_handler.register('echo', echo)

    server = await asyncio.start_server(request_handler, '127.0.0.1', 8888)

    addresses = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addresses}')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())


__all__ = ['JSONRPCRequestHandler']
