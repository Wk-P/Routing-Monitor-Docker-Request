import aiohttp
from aiohttp import web
import multiprocessing


async def handle_request(request):
    global server_index
    server_url = None

    table = route_table_queue.get()

    while True:
        if table[server_index]['status'] == 'Y':
            server_url = table[server_index]['address']
            server_index = (server_index + 1) % len(route_table)
            break
        server_index = (server_index + 1) % len(route_table)

    route_table_queue.put(table)


    request_data = await request.json()
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=request.method,
            url=server_url,
            headers=request.headers,
            # get request body json data
            json=request_data
        ) as response:
            response_data = await response.json()
            response_data = {
                "data": response_data,
                "server": server_url,
            }

            forwarded_response = web.json_response(response_data)
            return forwarded_response


async def get_route_table(queue):
    while True:
        modified_route_table = queue.get()
        route_table = modified_route_table
        queue.put(route_table)

if __name__ == "__main__":
    route_table_queue = multiprocessing.Queue(1)
    resources_table_queue = multiprocessing.Queue(1)

    # Use a Manager l    shared_memory_name = data_memory.name
    route_table = [
        {
            "address": "http://192.168.56.103:8080",
            'status': "Y"
        },
        {
            "address": "http://192.168.56.104:8080",
            'status': "Y"
        }
    ]
    
    route_table_queue.put(route_table)

    # nodes_info = create_monitor()

    server_index = 0


    # Create a separate process for process_for_monitor
    # monitor_process = multiprocessing.Process(target=process_for_monitor, args=(nodes_info, route_table_queue))
    # monitor_process.start()

    app = web.Application()
    app.router.add_post('/', handle_request)

    web.run_app(app, host='192.168.56.102', port=8080)