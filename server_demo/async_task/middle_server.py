import asyncio
from aiohttp import web, ClientSession
import logging
import random
import time

# 多个后端服务器的列表
BACKEND_SERVERS = [
    'http://localhost:8001/process',
    'http://localhost:8002/process',
    'http://localhost:8003/process'
]

# 配置日志记录
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def countdown_task(app, backend_id, interval=0.1):
    """
    定时任务，定期减少指定后端的等待时间。
    """
    try:
        while True:
            async with app['locks'][backend_id]:
                if app['wait_times'][backend_id] > 0:
                    app['wait_times'][backend_id] -= interval
                    if app['wait_times'][backend_id] < 0:
                        app['wait_times'][backend_id] = 0
                    logging.info(f"后端 {backend_id} 最新等待时间 {app['wait_times'][backend_id]:.1f} 秒")
                else:
                    logging.info(f"后端 {backend_id} 等待时间已归零")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logging.info(f"后端 {backend_id} 的倒计时任务已取消")

async def handle(request: web.Request):
    """
    处理来自客户端的请求，转发到后端并返回处理结果。
    """
    receive = time.time()

    try:
        request_data = await request.json()
        request_id = request_data.get('request_id', '未知')

        # 选择等待时间最少的后端服务器
        backend_id, backend_url = select_backend(request.app)

        # 随机生成处理时间
        task_process_time = random.randint(5, 8)

        # 更新等待时间
        async with request.app['locks'][backend_id]:
            task_wait_time = request.app['wait_times'][backend_id]
            request.app['wait_times'][backend_id] += task_process_time
            logging.info(f"请求 {request_id} 分配到后端 {backend_id}，增加等待时间 {task_process_time} 秒，总等待时间 {request.app['wait_times'][backend_id]} 秒")

        # 向后端发送请求
        async with request.app['sessions'][backend_id].post(backend_url, json={'process_time': task_process_time}) as resp:
            if resp.status != 200:
                raise Exception(f"后端 {backend_id} 返回状态码 {resp.status}")

            data = await resp.json()
            status = data.get("status", "未知")
            task_start_time = data.get('start', receive)

            logging.info(f"请求 {request_id} 在后端 {backend_id} 处理时间 {task_process_time} 秒，预计等待时间 {task_wait_time} 秒")

        response = {
            "status": status,
            "calculate_wait_time": task_wait_time,
            "real_wait_time": task_start_time - receive
        }
        return web.json_response(response)
    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)

def select_backend(app):
    """
    选择一个后端服务器。这里简单采用等待时间最少的策略。
    """
    min_wait = float('inf')
    selected_backend = None
    for backend_id, wait_time in app['wait_times'].items():
        if wait_time < min_wait:
            min_wait = wait_time
            selected_backend = backend_id
    return selected_backend, BACKEND_SERVERS[selected_backend]

async def on_startup(app):
    """
    应用启动时的初始化任务，包括启动倒计时任务和创建 ClientSession。
    """
    app['wait_times'] = {i: 0 for i in range(len(BACKEND_SERVERS))}
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}
    app['countdown_tasks'] = [
        asyncio.create_task(countdown_task(app, i, interval=1))
        for i in range(len(BACKEND_SERVERS))
    ]
    app['sessions'] = {
        i: ClientSession() for i in range(len(BACKEND_SERVERS))
    }
    logging.info("所有倒计时任务和客户端会话已启动")

async def on_cleanup(app):
    """
    应用关闭时的清理任务，包括取消倒计时任务和关闭 ClientSession。
    """
    for task in app['countdown_tasks']:
        task.cancel()
    await asyncio.gather(*app['countdown_tasks'], return_exceptions=True)
    for session in app['sessions'].values():
        await session.close()
    logging.info("所有倒计时任务和客户端会话已关闭")

def create_app():
    """
    创建并配置 aiohttp 应用。
    """
    app = web.Application()
    app.router.add_post('/forward', handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

if __name__ == '__main__':
    web.run_app(create_app(), host='localhost', port=8000)
