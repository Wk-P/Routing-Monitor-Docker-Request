# backend_server.py

import asyncio
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
import time


def process(t):
    start = time.time()
    time.sleep(t)
    return start

async def handle(request: web.Request):
    request_data: dict = await request.json()
    process_time = request_data.get('process_time')
    loop = asyncio.get_running_loop()
    task_start_time = await loop.run_in_executor(thread_executor, process, process_time)
    return web.json_response({"status": "任务完成", "start": task_start_time})

thread_executor = ThreadPoolExecutor(max_workers=1)
app = web.Application()
app.router.add_post('/process', handle)

if __name__ == '__main__':
    web.run_app(app, host='localhost', port=8002)
