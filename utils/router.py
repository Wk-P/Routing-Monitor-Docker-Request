import aiohttp
from aiohttp import web
import multiprocessing
import asyncio
import monitor_thr

# declare an async function for send request
async def req_task(session: aiohttp.ClientSession, url, method, request, request_data, route_table: list, cpu_limit):
    async with asyncio.Lock():
        if method == "HEAD":
        # send request to others' servers
            async with session.head(
                url=url,
            ) as response:
                # get headers

                headers = response.headers
                mem = headers.get('mem')
                cpuUsage = float(headers.get('data'))
                
                response = {
                    "data": {
                        'cpuUsage': cpuUsage * cpu_limit,
                        'mem': mem
                    },
                    "server": url
                }

                # add to list for update route_table
                async with asyncio.Lock():
                    for server in route_table:
                        if server['address'] == url:
                            server['cpu_usage'] = cpuUsage * cpu_limit


        # Now Just Head
        elif method == 'POST':
                        # send request to others' servers
            async with session.post(
                url=url,
                headers=request.headers,
                json=request_data
            ) as response:
                # to Json

                response_data = await response.json()
                response_data['cpuUsage'] = response_data['cpuUsage'] * cpu_limit

                # response
                response = {
                    "data": response_data,
                    "server": url,
                }

                # add to list for update route_table
                for server in route_table:
                    if server['address'] == url:
                        server['cpu_usage'] = response_data['cpuUsage']


        else:
            print("Error")
            response = None

        return response


# For changing by cpu usage, first time is random, next is to cpuUsage min 

async def handle_request(request):

    server_url = None
    cpu_limit = 0.5
    async with asyncio.Lock():
        min_usage = 2
        for server in route_table:
            if server['status'] == 'Y':
                if float(server['cpu_usage']) < min_usage:
                    server_url = server['address']
                    min_usage = float(server['cpu_usage'])
    
    request_data = await request.json()
    
    tasks = []

    # send request to first server
    async with aiohttp.ClientSession() as session:
        for server in route_table:
            if server['status'] == 'Y':
                if server_url == server['address']:
                    tasks.append(asyncio.create_task(req_task(session, server['address'], "POST", request, request_data, route_table, cpu_limit)))
                else:
                    tasks.append(asyncio.create_task(req_task(session, server['address'], "HEAD", request, request_data, route_table, cpu_limit)))

        responses = await asyncio.gather(*tasks)

        # Here solve the HS and VS
        
        return web.json_response(responses)



if __name__ == "__main__":
    # Use a Manager l    shared_memory_name = data_memory.name
    route_table = [
        {
            "role": "worker1",
            "name": 'ubuntuDockerWorker1',
            "address": "http://192.168.56.103:8080",
            'status': "Y",
            'cpu_usage': 0
        },
        {
            "role": "worker",
            "name": 'ubuntuDockerWorker',
            "address": "http://192.168.56.105:8080",
            'status': "N",
            'cpu_usage': 0
        },
        {
            "role": "worker",
            "name": 'ubuntuDockerWorker2',
            "address": "http://192.168.56.106:8080",
            'status': "Y",
            'cpu_usage': 0
        },
        {
            "role": "worker",
            "name": 'ubuntuDockerWorker3',
            "address": "http://192.168.56.104:8080",
            'status': "N",
            'cpu_usage': 0
        }
    ]

    server_index = 0

    app = web.Application()
    app.router.add_post('/', handle_request)

    web.run_app(app, host='192.168.56.107', port=8080)

    monitor_thr.main()