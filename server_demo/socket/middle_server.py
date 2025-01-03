# middle_server.py
import asyncio
import json
import time
from aiohttp import web, ClientSession
from typing import Tuple, Dict

class MiddleServer:
    def __init__(self, backend_addresses):
        self.backend_addresses = backend_addresses
        self.backend_pending_time = {addr: 0 for addr in backend_addresses}
        self.queue: asyncio.Queue[Tuple[Dict, asyncio.Future[Dict]]] = asyncio.Queue()

    async def start(self):
        app = web.Application()
        app["queue"] = self.queue
        app.router.add_post("/handle", self.handle)

        asyncio.create_task(self.process_queue())
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 4000)
        print("Middle server listening on localhost:4000")
        await site.start()
        await asyncio.Event().wait()  # Keep the server running

    async def handle(self, request: web.Request) -> web.Response:
        data = await request.json()
        estimated_processing_time = data.get("estimated_time", 1)  # Default to 1 second if not provided

        # Select backend based on pending time including the estimated processing time
        backend = self.select_backend(estimated_processing_time)

        if backend is None:
            print("No backend available")
            return web.Response(text=json.dumps({"error": "No backend available"}), status=503)

        response_future: asyncio.Future[Dict] = asyncio.Future()
        await self.queue.put((data, response_future, backend, estimated_processing_time))
        response = await response_future
        return web.Response(text=json.dumps(response))

    async def process_queue(self):
        while True:
            request, response_future, backend, estimated_processing_time = await self.queue.get()

            # Increment pending time preemptively
            async with self.lock:
                self.backend_pending_time[backend] += estimated_processing_time

            try:
                async with ClientSession() as session:
                    async with session.post(f"http://{backend[0]}:{backend[1]}/process", json=request) as resp:
                        response = await resp.json()

                response_future.set_result(response)
                print(f"Response from backend {backend}: {response}")

            except Exception as e:
                print(f"Error processing request with backend {backend}: {e}")
                response_future.set_result({"error": "Failed to process request"})

            finally:
                # Decrement pending time after actual processing
                async with self.lock:
                    self.backend_pending_time[backend] -= estimated_processing_time

                # Log pending time for debugging
                async with self.lock:
                    print(f"Updated pending times: {self.backend_pending_time}")

    async def select_backend(self, estimated_processing_time: float) -> Tuple[str, int]:
        # Add estimated time to current pending time and select the backend with the minimum value
        async with self.lock:
            selected_backend = min(
                self.backend_pending_time,
                key=lambda addr: self.backend_pending_time[addr] + estimated_processing_time,
                default=None
            )
            print(f"Selected backend: {selected_backend} with pending times: {self.backend_pending_time}")
            return selected_backend

if __name__ == "__main__":
    backends = [("localhost", 5001), ("localhost", 5002), ("localhost", 5003)]
    server = MiddleServer(backends)
    asyncio.run(server.start())



