import aiohttp
import asyncio
from aiohttp import web
import multiprocessing

route_table = [
    {
        "address": "http://192.168.56.103:8080",
        'status': "N"
    },
    {
        "address": "http://192.168.56.104:8080",
        'status': "Y"
    }
]

def update_route_table(shared_route_table):
    # 在主进程中更新共享的route_table
    while True:
        # 这里可以根据需要更新route_table
        # 例如：shared_route_table[0]['status'] = 'Y'
        pass

async def web_app(shared_route_table):
    # 协程中使用共享的route_table
    while True:
        # 这里可以访问共享的route_table，根据需要进行处理
        await asyncio.sleep(1)

async def handle_request(request):
    # 在处理请求时使用共享的route_table
    global server_index
    server_url = None

    while True:
        if shared_route_table[server_index]['status'] == 'Y':
            server_url = shared_route_table[server_index]['address']
            break
        server_index = (server_index + 1) % len(shared_route_table)

    # 其余的请求处理逻辑不变
    return web.Response(text=f"Forwarded to {server_url}")

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    shared_route_table = manager.list(route_table)  # 创建一个共享的列表

    # 启动一个进程来更新route_table
    update_process = multiprocessing.Process(target=update_route_table, args=(shared_route_table,))
    update_process.start()

    # 创建一个事件循环
    loop = asyncio.get_event_loop()

    # 启动web_app协程
    web_app_task = loop.create_task(web_app(shared_route_table))

    app = web.Application()
    app.router.add_post('/', handle_request)

    server_index = 0  # 这个变量需要在全局中声明

    web.run_app(app, host='192.168.56.102', port=8080)
