import aiohttp
from aiohttp import web
import multiprocessing
import asyncio

# For changing by cpu usage, first time is random, next is to cpuUsage min 

async def handle_request(request):

    server_url = None

    table = route_table_queue.get()

    # while True:
    #     if table[server_index]['status'] == 'Y':
    #         server_url = table[server_index]['address']
    #         server_index = (server_index + 1) % len(route_table)
    #         break
    #     server_index = (server_index + 1) % len(route_table)

    cpu_usage_table = cpu_usage_queue.get()
    
    
    min_usage = 2
    for server in cpu_usage_table:
        if cpu_usage_table[server] < min_usage:
            server_url = server
            min_usage = cpu_usage_table[server]

    route_table_queue.put(table)
    cpu_usage_queue.put(cpu_usage_table)
    
    request_data = await request.json()
    
    response_to_client = None

    # send request to first server
    async with aiohttp.ClientSession() as session:
        # send request to others' servers
        for server in cpu_usage_table:
            if server != server_url:
                async with session.request(
                    method="HEAD",
                    url=server_url,
                    headers=request.headers,
                ) as response:
                    # to Json
                    response_data = await response.headers.items()

                    print(response_data)

                    # response
                    response = {
                        "data": response_data,
                        "server": server_url,
                    }

                    # add to list for update cpu_usage_table
                    cpu_usage_table = cpu_usage_queue.get()
                    cpu_usage_table[server_url] = response_data['data']['cpuPercent']
                    cpu_usage_queue.put(cpu_usage_table)

        # send post
        async with session.request(
            method=request.method,
            url=server_url,
            headers=request.headers,
            # get request body json data
            json=request_data
        ) as response:
            # to Json
            response_data = await response.json()

            # response
            response = {
                "data": response_data,
                "server": server_url,
            }

            response_to_client = response

            # add to list for update cpu_usage_table
            cpu_usage_table = cpu_usage_queue.get()
            cpu_usage_table[server_url] = response_data['data']['cpuUsage']
            cpu_usage_queue.put(cpu_usage_table)

            return web.json_response(response_to_client)



async def get_route_table(queue):
    while True:
        modified_route_table = queue.get()
        route_table = modified_route_table
        queue.put(route_table)

if __name__ == "__main__":
    route_table_queue = multiprocessing.Queue(1)
    cpu_usage_queue = multiprocessing.Queue(1)

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
    
    cpu_usage_table = dict()

    for server in route_table:
        cpu_usage_table[server['address']] = 0

    print(cpu_usage_table)

    route_table_queue.put(route_table)
    cpu_usage_queue.put(cpu_usage_table)

    server_index = 0


    app = web.Application()
    app.router.add_post('/', handle_request)

    web.run_app(app, host='192.168.56.102', port=8080)