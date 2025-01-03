# backend.py
import asyncio
from aiohttp import web

class BackendServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def start(self):
        app = web.Application()
        app.router.add_post("/process", self.handle)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        print(f"Backend server listening on {self.host}:{self.port}")
        await site.start()
        await asyncio.Event().wait()  # Keep the server running

    async def handle(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            print(f"Processing: {data}")

            await asyncio.sleep(2)  # Simulating processing time

            response = {"status": "done", "task": data["task"]}
            return web.json_response(response)

        except Exception as e:
            print(f"Error processing request: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

if __name__ == "__main__":
    async def main():
        ports = [5001, 5002, 5003]
        tasks = [BackendServer("localhost", port).start() for port in ports]
        await asyncio.gather(*tasks)

    asyncio.run(main())
