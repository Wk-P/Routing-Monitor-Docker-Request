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
    app['finish_times'] = {i: 0 for i in range(len(BACKEND_SERVERS))}
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}
    app['sessions'] = {i: ClientSession(timeout=ClientTimeout(None)) for i in range(len(BACKEND_SERVERS))}
    logging.info("应用启动完毕")

async def on_cleanup(app):
    for session in app['sessions'].values():
        await session.close()
    logging.info("应用即将退出")

def select_backend(app):
    """基于最短 finish_time 的后端选择"""
    selected_id = None
    min_finish = float('inf')
    now = time.time()
    for backend_id, ft in app['finish_times'].items():
        waiting = max(0, ft - now)
        if waiting < min_finish:
            min_finish = waiting
            selected_id = backend_id
    return selected_id, BACKEND_SERVERS[selected_id]

async def handle(request: web.Request):
    try:
        data = await request.json()
        request_id = data.get("request_id", "unknown")
        process_time = data.get("process_time", random.uniform(1, 5))

        # 1. 选择后端
        backend_id, backend_url = select_backend(request.app)
        now: float = time.time()
        async with request.app['locks'][backend_id]:
            ft = request.app['finish_times'][backend_id]
            pending_time_estimated = max(0, ft - now)

            # 更新 finish_time
            new_finish = max(ft, time.time()) + process_time
            request.app['finish_times'][backend_id] = new_finish

        logging.info(f"请求 {request_id} 分配给后端 {backend_id}，预计排队等待 {pending_time_estimated:.2f} 秒")

        # 2. 发请求给后端
        async with request.app['sessions'][backend_id].post(backend_url, json={"process_time": process_time}) as resp:
            if resp.status != 200:
                raise ValueError(f"后端 {backend_id} 返回异常状态：{resp.status}")
            backend_resp = await resp.json()

        # 返回给客户端
        real_wait_time = max(0, backend_resp.get("start", now) - now)
        error = pending_time_estimated - real_wait_time

        return web.json_response({
            "pending_time_estimated": pending_time_estimated,
            "real_wait_time": real_wait_time,
            "status": backend_resp.get("status", "unknown"),
            "start": backend_resp.get('start', 0),
            "backend_id": backend_id,
            "error": abs(error)
        })

    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)

if __name__ == '__main__':
    web.run_app(create_app(), host='localhost', port=8000)
