import asyncio
from aiohttp import ClientTimeout, web, ClientSession
import logging
import time
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BACKEND_SERVERS = [
    'http://localhost:8001/process',
    'http://localhost:8002/process',
    'http://localhost:8003/process'
]

def create_app():
    app = web.Application()
    app.router.add_post('/forward', handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

async def on_startup(app):
    app['finish_times'] = {i: time.time() for i in range(len(BACKEND_SERVERS))}
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}
    app['sessions'] = {i: ClientSession(timeout=ClientTimeout(None)) for i in range(len(BACKEND_SERVERS))}
    app['countdown_task'] = asyncio.create_task(countdown_task(app, interval=0.1))
    logging.info("应用启动完毕")

async def on_cleanup(app):
    app['countdown_task'].cancel()
    await asyncio.gather(app['countdown_task'], return_exceptions=True)
    for session in app['sessions'].values():
        await session.close()
    logging.info("应用即将退出")

async def countdown_task(app, interval):
    """定期减少 finish_times 的时间戳值"""
    try:
        while True:
            now = time.time()
            async with asyncio.Lock():
                for worker_id, finish_time in app['finish_times'].items():
                    if finish_time <= now:
                        app['finish_times'][worker_id] = now
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logging.info("倒计时任务被取消")

def select_backend(app):
    """基于最短 finish_time 的后端选择"""
    selected_worker = None
    min_finish_time = float('inf')
    now = time.time()

    for worker_id, finish_time in app['finish_times'].items():
        waiting_time = max(0, finish_time - now)
        if waiting_time < min_finish_time:
            min_finish_time = waiting_time
            selected_worker = worker_id

    return selected_worker, BACKEND_SERVERS[selected_worker]

async def handle(request: web.Request):
    try:
        data = await request.json()
        request_id = data.get("request_id", "unknown")
        process_time = data.get("process_time", random.uniform(1, 5))

        # 选择后端
        backend_id, backend_url = select_backend(request.app)
        now = time.time()
        
        async with request.app['locks'][backend_id]:
            current_finish_time = request.app['finish_times'][backend_id]
            new_finish_time = max(current_finish_time, now) + process_time
            request.app['finish_times'][backend_id] = new_finish_time

        logging.info(f"请求 {request_id} 分配给后端 {backend_id}，预计完成时间更新为 {new_finish_time}")

        # 发请求给后端
        async with request.app['sessions'][backend_id].post(backend_url, json={"process_time": process_time}) as resp:
            if resp.status != 200:
                raise ValueError(f"后端 {backend_id} 返回异常状态：{resp.status}")
            backend_resp = await resp.json()

        real_wait_time = max(0, backend_resp.get("start", now) - now)

        return web.json_response({
            "pending_time_estimated": max(0, current_finish_time - now),
            "real_wait_time": real_wait_time,
            "status": backend_resp.get("status", "unknown"),
            "start": backend_resp.get('start', 0),
            "backend_id": backend_id,
        })

    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)

if __name__ == '__main__':
    web.run_app(create_app(), host='localhost', port=8000)
