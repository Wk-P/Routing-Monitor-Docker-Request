import asyncio
from aiohttp import web, ClientSession
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
    # finish_times 用于记录每个 backend 当前队列「预计完成时间」
    # 初始值为 0，表示现在就能执行
    app['finish_times'] = {i: 0 for i in range(len(BACKEND_SERVERS))}
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}
    # 每个后端一个 Session
    app['sessions'] = {i: ClientSession() for i in range(len(BACKEND_SERVERS))}
    logging.info("应用启动完毕")

async def on_cleanup(app):
    # 关闭所有 Session
    for session in app['sessions'].values():
        await session.close()
    logging.info("应用即将退出")

def select_backend(app):
    # 仍然可以按照「finish_times」最小的后端来做负载均衡
    selected_id = None
    min_finish = float('inf')
    now = time.time()
    for backend_id, ft in app['finish_times'].items():
        # 计算「还剩多少时间」就能开始新任务
        waiting = max(0, ft - now)
        if waiting < min_finish:
            min_finish = waiting
            selected_id = backend_id
    return selected_id, BACKEND_SERVERS[selected_id]

async def handle(request: web.Request):
    receive_time = time.time()
    try:
        data = await request.json()
        request_id = data.get("request_id", "unknown")
        process_time = data.get("process_time", random.uniform(1, 5))

        # 1. 选择后端
        backend_id, backend_url = select_backend(request.app)
        async with request.app['locks'][backend_id]:
            now = time.time()
            # 当前后端 finish_times
            ft = request.app['finish_times'][backend_id]
            # 计算此刻排队的等待时间
            pending_time = max(0, ft - now)

            # 更新该后端新的 finish_time
            new_finish = max(ft, now) + process_time
            request.app['finish_times'][backend_id] = new_finish

        logging.info(f"请求 {request_id} 分配给后端 {backend_id}，预计排队等待 {pending_time:.2f} 秒")

        # 2. 发请求给后端
        async with request.app['sessions'][backend_id].post(backend_url, json={"process_time": process_time}) as resp:
            if resp.status != 200:
                raise ValueError(f"后端 {backend_id} 返回异常状态：{resp.status}")
            backend_resp = await resp.json()
            # 假设后端返回了真正开始处理的时间戳
            real_start_time = backend_resp.get("start", receive_time)

        # 3. 返回给客户端
        return web.json_response({
            "pending_time_estimated": pending_time,
            "real_wait_time": real_start_time - receive_time,
            "status": backend_resp.get("status", "unknown")
        })

    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)

if __name__ == '__main__':
    web.run_app(create_app(), host='0.0.0.0', port=8000)
