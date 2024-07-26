import aiohttp
from aiohttp import web
import multiprocessing
import requests


class Info():
    def __init__(self):
        self.ips = {
            "10.0.2.7": 0,
            "10.0.2.8": 0,
            "10.0.2.5": 0,
        }
        self.port = 8080
        self.session = None

    async def start_session(self):
        self.session = aiohttp.ClientSession()


def query_prometheus(query: str):
    prometheus_url = "http://localhost:9090/api/v1/query"

    params = {'query': query}

    response = requests.get(prometheus_url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data['data']['result']
    else:
        print("Error: Unable to fetch data from Prometheus")
        return None



def url_choose():
    global info_obj
    ip = None
    query_expression = r"100 - (avg by (instance) (irate(node_cpu_seconds_total{job='ubuntuDockerWorker',mode='idle'}[10m])) * 100)"
    results = query_prometheus(query_expression)
    min_usage = 100
    min_usage_index = 0

    for i in range(len(results)):
        info_obj.ips[results[i]['metric']['instance'][:-5]] = float(results[i]['value'][1])
        if float(results[i]['value'][1]) < min_usage:
            min_usage = float(results[i]['value'][1])
            min_usage_index = i
    
    ip = results[min_usage_index]['metric']['instance'][:-5]


    return ip


info_obj = Info()


async def request_handler(request: web.Request):
    global info_obj
    headers = request.headers
    data = await request.post()

    # url choose
    ip = url_choose()
    url = f"http://{ip}:{info_obj.port}"

    # query_expression = r"100 - (avg by (instance) (irate(node_cpu_seconds_total{job='ubuntuDockerWorker',mode='idle'}[10m])) * 100)"
    # usages_list = query_prometheus(query_expression)
    usages = info_obj.ips
   

    async with info_obj.session.post(url=url, json=data, headers=headers) as response:
        
        data = await response.json()
        res = {"success": 1, "response": data, "ip": ip}
        res.update({'usages':usages})
        return web.json_response(res)



async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())

    return app
    


def server_proc():
    app = server_app_init()
    web.run_app(app, host='192.168.56.107', port=8081)


if __name__ == "__main__":
    server = multiprocessing.Process(target=server_proc)
    server.start()

    server.join()