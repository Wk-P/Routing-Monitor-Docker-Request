import asyncio
from aiohttp import ClientTimeout, web, ClientSession
import logging
import time
import random
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BACKEND_SERVERS = [
    'http://localhost:8001/process',
    'http://localhost:8002/process',
    'http://localhost:8003/process'
]

# 最大误差队列长度
MAX_ERROR_HISTORY = 100

def create_app():
    app = web.Application()
    app.router.add_post('/forward', handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

async def on_startup(app):
    # 初始化每个后端的任务队列和错误记录
    app['task_queues'] = {i: deque() for i in range(len(BACKEND_SERVERS))}  # 每个后端任务队列
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}
    app['sessions'] = {i: ClientSession(timeout=ClientTimeout(None)) for i in range(len(BACKEND_SERVERS))}
    app['errors'] = {i: deque(maxlen=MAX_ERROR_HISTORY) for i in range(len(BACKEND_SERVERS))}  # 每个后端的误差记录
    logging.info("应用启动完毕")

async def on_cleanup(app):
    for session in app['sessions'].values():
        await session.close()
    logging.info("应用即将退出")

def select_backend(app):
    """基于加权的后端选择"""
    selected_id = None
    min_weight = float('inf')
    now = time.time()
    for backend_id, queue in app['task_queues'].items():
        # 当前任务队列的排队时间
        queue_waiting_time = sum(task['process_time'] for task in queue if task['finish_time'] > now)
        # 平均误差作为调整因子
        avg_error = sum(app['errors'][backend_id]) / len(app['errors'][backend_id]) if app['errors'][backend_id] else 0
        # 权重 = 排队时间 + 误差
        weight = queue_waiting_time + avg_error
        if weight < min_weight:
            min_weight = weight
            selected_id = backend_id
    return selected_id, BACKEND_SERVERS[selected_id]

async def handle(request: web.Request):
    try:
        data = await request.json()
        request_id = data.get("request_id", "unknown")
        process_time = data.get("process_time", random.uniform(1, 5))

        # 1. 选择后端
        backend_id, backend_url = select_backend(request.app)
        async with request.app['locks'][backend_id]:
            now = time.time()
            # 更新任务队列状态
            task_queue = request.app['task_queues'][backend_id]
            while task_queue and task_queue[0]['finish_time'] <= now:
                task_queue.popleft()  # 移除已完成的任务

            # 计算预计等待时间
            queue_waiting_time = sum(task['process_time'] for task in task_queue)
            estimated_finish_time = now + queue_waiting_time + process_time

            # 添加新任务到队列
            task_queue.append({
                "request_id": request_id,
                "process_time": process_time,
                "finish_time": estimated_finish_time,
            })

        logging.info(f"请求 {request_id} 分配给后端 {backend_id}，预计排队等待 {queue_waiting_time:.2f} 秒")

        # 2. 发请求给后端
        async with request.app['sessions'][backend_id].post(backend_url, json={"process_time": process_time}) as resp:
            if resp.status != 200:
                raise ValueError(f"后端 {backend_id} 返回异常状态：{resp.status}")
            backend_resp = await resp.json()

        # 3. 动态调整误差
        real_wait_time = max(0, backend_resp.get("start", now) - now)
        error = queue_waiting_time - real_wait_time
        request.app['errors'][backend_id].append(error)

        # 返回给客户端
        return web.json_response({
            "pending_time_estimated": queue_waiting_time,
            "real_wait_time": real_wait_time,
            "status": backend_resp.get("status", "unknown"),
            "start": backend_resp.get('start', 0),
            "backend_id": backend_id,
            "error": error,
        })

    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)

if __name__ == '__main__':
    web.run_app(create_app(), host='localhost', port=8000)
