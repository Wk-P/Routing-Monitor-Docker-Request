import aiohttp
import asyncio
from aiohttp import web
import multiprocessing
from monitor import create_monitor, active_node, monitor_node
# Create a multiprocessing Manager for shared data
manager = multiprocessing.Manager()

# Use a Manager list for route_table to make it shared between processes
route_table = manager.list([
    {
        "address": "http://192.168.56.103:8080",
        'status': "N"
    },
    {
        "address": "http://192.168.56.104:8080",
        'status': "Y"
    }
])

nodes_info = create_monitor()

server_index = 0

async def handle_request(request):
    global server_index
    server_url = None

    while True:
        if route_table[server_index]['status'] == 'Y':
            server_url = route_table[server_index]['address']
            break
        server_index = (server_index + 1) % len(route_table)

    async with aiohttp.ClientSession() as session:
        async with session.request(
            method="GET",
            url=server_url,
            headers=request.headers,
            data=await request.read()
        ) as response:
            response_data = await response.read()

            response_data = {
                "data": response_data.decode('utf-8'),
                "server": server_url
            }

            forwarded_response = web.json_response(response_data)

            return forwarded_response

def active_one_node(nodes_info):
    node_address = None
    for node in route_table:
        if node['status'] == 'N':
            node_address = node['address'][7:-5]
            node['status'] = 'Y'

    if node_address is not None:
        for node in nodes_info:
            if node['address'][:-5] == node_address and active_node(node['name']):
                return {'name': node['name'], 'status': 'Start running success'}

        return {'type': 'text', 'msg': {'name': node['name'], 'status': 'Start running failed'}}
    else:
        return {'type': 'error', 'msg': "No matching node or node has been started"}

def process_for_monitor(nodes_info, shared_route_table):
    while True:
        print(shared_route_table)  # Access shared route_table
        values = monitor_node(nodes_info=nodes_info)
        for value in values:
            if value['HS'] == 'up':
                retvalue = active_one_node(nodes_info=nodes_info)
                print("retvalue : ", retvalue)
            else:
                pass

if __name__ == "__main__":
    # Create a separate process for process_for_monitor
    monitor_process = multiprocessing.Process(target=process_for_monitor, args=(nodes_info, route_table))
    monitor_process.start()

    app = web.Application()
    app.router.add_post('/', handle_request)

    web.run_app(app, host='192.168.56.102', port=8080)
