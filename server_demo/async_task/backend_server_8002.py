import asyncio
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
import time

# 单线程池
thread_executor = ThreadPoolExecutor(max_workers=1)

async def handle(request: web.Request):
    data = await request.json()
    process_time = data.get("process_time", 1.0)
    print(f"后端收到任务，处理时间 {process_time} 秒")

    loop = asyncio.get_running_loop()

    # 模拟处理任务
    start_time = await loop.run_in_executor(thread_executor, process, process_time)
    return web.json_response({"status": "任务完成", "start": start_time, "end": time.time()})

def process(t):
    """
    模拟耗时任务
    """
    start = time.time()
    time.sleep(t)  # 模拟阻塞
    print(f"任务处理完成，开始时间 {start}")
    return start

if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/process', handle)
    web.run_app(app, host='localhost', port=8002)  # 修改端口为 8002, 8003 运行多个实例
