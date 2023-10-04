# round robin production

import aiohttp
import asyncio
from aiohttp import web
from monitor import create_monitor, active_node, monitor_node
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

    print(route_table)
    while True:
        if route_table[server_index]['status'] == 'Y':
            server_url = route_table[server_index]['address']
            server_index = (server_index + 1) % len(route_table)
            break
        
        server_index = (server_index + 1) % len(route_table)
    

    async with aiohttp.ClientSession() as session:
        
        # request transform to target server and get response from this server
        async with session.request(
            method="GET",
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
            node_address = node['address'][7:-5]
            node['status'] = 'Y'
    
    print(route_table)

    # if unactive node actived
    if node_address is not None:
        for node in nodes_info:
            if node['address'][:-5] == node_address and active_node(node['name']):
                return {'name': node['name'], 'status': 'Start running success'}

        return {'type': 'text', 'msg': {'name': node['name'], 'status': 'Start running failed'}}
    else:
        return {'type': 'error', 'msg': "No mathcing node or node has been started"}


def process_for_monitor(nodes_info):
    # start monitor

    while True:
        values = monitor_node(nodes_info=nodes_info)
        for value in values:
            if value['HS'] == 'up':
                retvalue = active_one_node(nodes_info=nodes_info)
                print("retvalue : ", retvalue)
            else:
                pass

if __name__ == "__main__":

    monitor_process = multiprocessing.Process(target=process_for_monitor, args=((nodes_info,)))
    monitor_process.start()

    app = web.Application()
    app.router.add_post('/', handle_request)

    web.run_app(app, host='192.168.56.102', port=8080)
