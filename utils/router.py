import aiohttp
import asyncio
from aiohttp import web
import multiprocessing
from monitor import create_monitor, active_node, monitor_node


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


# update routing table function
def active_one_node(nodes_info, queue):
    table = queue.get()

    node_address = None
    for node in table:
        if node['status'] == 'N':
            node_address = node['address'][7:-5]
            node['status'] = 'Y'
            print(f"In active {table}") 

    queue.put(table)

    if node_address is not None:
        for node in nodes_info:
            if node['address'][:-5] == node_address and active_node(node['name']):
                return {'name': node['name'], 'status': 'Start running success'}
        
        return {'type': 'text', 'msg': {'name': node['name'], 'status': 'Start running failed'}}
    else:
        return {'type': 'error', 'msg': "No matching node or node has been started"}


async def get_route_table(queue):
    while True:
        modified_route_table = queue.get()
        route_table = modified_route_table
        queue.put(route_table)

# update routing table update routing table
def process_for_monitor(nodes_info, queue):
    while True:
        # print(f"In monitor {table}")  # Access shared route_table
        values = monitor_node(nodes_info=nodes_info)
        for value in values:
            if value['HS'] == 'up':
                active_one_node(nodes_info=nodes_info, queue=queue)
            else:
                pass

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