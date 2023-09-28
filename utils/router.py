# round robin production

import aiohttp
import asyncio
from aiohttp import web
from monitor import start_monitor, create_monitor, active_node
import multiprocessing
import os

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

nodes_info = create_monitor()

server_index = 0

async def handle_request(request):
    # get request from client 
    global server_index
    server_url = None

    while True:
        if route_table[server_index]['status'] == 'Y':
            server_url = route_table[server_index]['address']
            break
        server_index = (server_index + 1) % len(route_table)
    
    server_index = (server_index + 1) % len(route_table)

    # print(server_url)
    async with aiohttp.ClientSession() as session:
        
        # request transform to target server and get response from this server
        async with session.request(
            method=request.method,
            url=server_url,
            headers=request.headers,
            data=await request.read()
        ) as response:
            
            # send request to client
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
            node_address = node['address'][7:-1]
    
    # if unactive node actived
    if node_address is not None:
        for node in nodes_info:
            if node['address'] == node_address and active_node(node['name']):
                node['status'] = 'Y'
                return {'name': node['name'], 'status': 'Start running success'}

        return {'type': 'text', 'msg': {'name': node['name'], 'status': 'Start running failed'}}
    else:
        return {'type': 'error', 'msg': "No mathcing node or node has been started"}


def process_for_monitor(nodes_info):
    # start monitor
    generator = start_monitor(nodes_info=nodes_info)
    while True:
        values = next(generator)
        for value in values:
            print(value)


if __name__ == "__main__":


    app = web.Application()
    app.router.add_get('/', handle_request)

    web.run_app(app, host='192.168.56.102', port=8080)

    monitor_process = multiprocessing.Process(target=process_for_monitor, args=((nodes_info,)))
    monitor_process.start()
    