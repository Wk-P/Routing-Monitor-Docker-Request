import asyncio
from aiohttp import web, ClientSession
import logging
import random
import time
from collections import deque

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 后端服务器列表（示例地址，需要你自行实现或更改）
BACKEND_SERVERS = [
    'http://localhost:8001/process',
    'http://localhost:8002/process',
    'http://localhost:8003/process'
]


async def handle(request: web.Request):
    """
    处理来自客户端的请求，转发到后端并返回处理结果。
    在正式分配任务前，计算当前队列的预计等待时间 (pending time)。
    """
    receive_time = time.time()

    try:
        request_data: dict = await request.json()
        request_id = request_data.get('request_id', '未知')
        process_time = request_data.get('process_time', random.uniform(1, 5))

        # 1. 根据当前各后端队列的负载，选择最优后端
        backend_id, backend_url = select_backend(request.app)

        # 2. 计算待分配给该后端时，预计的排队时间 (pending time)
        async with request.app['locks'][backend_id]:
            queue = request.app['task_queues'][backend_id]
            current_time = time.time()

            # 计算队列里所有任务的剩余处理时间之和
            # 对于每个任务，剩余时间 = max(0, (enqueue_time + process_time) - current_time)
            pending_time = sum(
                max(0, task['enqueue_time'] + task['process_time'] - current_time)
                for task in queue
            )

            logging.info(
                f"请求 {request_id} 分配到后端 {backend_id}，"
                f"队列预计等待时间 {pending_time:.2f} 秒，"
                f"新任务处理时间 {process_time:.2f} 秒"
            )

            # 将当前任务加入队列
            queue.append({
                "process_time": process_time,
                "enqueue_time": current_time
            })

        # 3. 将请求转发给后端
        async with request.app['sessions'][backend_id].post(
            backend_url,
            json={"process_time": process_time}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"后端 {backend_id} 返回状态码 {resp.status}")

            backend_response = await resp.json()
            # 后端返回的任务实际开始处理的时间（也可能是后端的系统时间）
            task_start_time = backend_response.get("start", receive_time)

        # 4. 任务完成后从队列中移除（此处为简化，假设任务完成后即刻移除队列头）
        #    但更合理的做法是后端真正开始处理后，由倒计时协程决定何时移除。
        async with request.app['locks'][backend_id]:
            if request.app['task_queues'][backend_id]:
                request.app['task_queues'][backend_id].popleft()

        # 5. 构建返回结果
        response = {
            "status": backend_response.get("status", "未知"),
            "calculate_wait_time": pending_time,
            "real_wait_time": task_start_time - receive_time,
            "start": backend_response.get('start', 0),
            "backend_id": backend_id,
            "error": pending_time - (task_start_time - receive_time),
        }
        return web.json_response(response)

    except Exception as e:
        logging.error(f"处理请求时发生错误: {e}")
        return web.json_response({"error": "Failed to process request"}, status=500)


def select_backend(app):
    """
    根据当前各后端的队列负载，选择最优后端。
    这里简单实现：选择待处理任务数最少（或剩余处理时间最少）的后端。
    """
    min_wait = float('inf')
    selected_backend = 0

    for backend_id, queue in app['task_queues'].items():
        current_time = time.time()
        # 计算该后端当前所有任务的剩余处理时间
        total_remaining_time = sum(
            max(0, task['enqueue_time'] + task['process_time'] - current_time)
            for task in queue
        )
        if total_remaining_time < min_wait:
            min_wait = total_remaining_time
            selected_backend = backend_id

    return selected_backend, BACKEND_SERVERS[selected_backend]


async def countdown_task(app, backend_id, interval=0.1):
    """
    定时更新任务队列，将已完成的任务移除。
    以防队列里残留已完成的任务，影响下一次调度的准确性。
    """
    try:
        while True:
            async with app['locks'][backend_id]:
                queue = app['task_queues'][backend_id]
                current_time = time.time()

                # 如果队列头部的任务已完成，则移除它
                while queue and (queue[0]['enqueue_time'] + queue[0]['process_time']) <= current_time:
                    queue.popleft()

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        logging.info(f"后端 {backend_id} 的倒计时任务已取消")


async def on_startup(app):
    """
    应用启动时的初始化任务。
    """
    # 初始化每个后端的任务队列和锁
    app['task_queues'] = {i: deque() for i in range(len(BACKEND_SERVERS))}
    app['locks'] = {i: asyncio.Lock() for i in range(len(BACKEND_SERVERS))}

    # 启动定时任务，定期移除已完成的任务
    app['countdown_tasks'] = [
        asyncio.create_task(countdown_task(app, i, interval=0.1))
        for i in range(len(BACKEND_SERVERS))
    ]

    # 为每个后端创建一个共享的 ClientSession
    app['sessions'] = {
        i: ClientSession() for i in range(len(BACKEND_SERVERS))
    }

    logging.info("应用启动完成，所有资源已初始化")


async def on_cleanup(app):
    """
    应用关闭时的清理任务。
    """
    # 取消所有倒计时任务
    for task in app['countdown_tasks']:
        task.cancel()
    await asyncio.gather(*app['countdown_tasks'], return_exceptions=True)

    # 关闭所有 ClientSession
    for session in app['sessions'].values():
        await session.close()

    logging.info("应用关闭，所有资源已清理")


def create_app():
    """
    创建并配置 aiohttp 应用。
    """
    app = web.Application()
    # 添加路由，客户端发送 POST 请求到 /forward
    app.router.add_post('/forward', handle)

    # 绑定启动与清理事件
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app


if __name__ == '__main__':
    # 启动服务
    web.run_app(create_app(), host='localhost', port=8000)
