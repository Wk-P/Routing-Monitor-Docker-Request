import aiohttp
from aiohttp import web
import requests
import time
import asyncio


class Info():
    def __init__(self):
        self.ips = {
            "192.168.0.150": 0,
            "192.168.0.151": 0,
            "192.168.0.152": 0,
        }
        self.ipsl = [
            "192.168.0.150",
            "192.168.0.151",
            "192.168.0.152",
        ]
        self.port = 8080
        self.session = None
        self.current_index = 0

    async def start_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=200), timeout=aiohttp.ClientTimeout(total=None))


def query_prometheus(query: str):
    prometheus_url = "http://192.168.0.100:9090/api/v1/query"

    params = {'query': query}

    response = requests.get(prometheus_url, params=params)

    print(response.status_code)

    if response.status_code == 200:
        data = response.json()
        print(data)
        return data['data']['result']
    else:
        print("Error: Unable to fetch data from Prometheus")
        return None



def url_choose():
    global info_obj
    ip = None
    # query_time = 1
    # query_expression = f"100 * (1 - sum(increase(node_cpu_seconds_total{{mode='idle'}}[{query_time}s])) by (instance) / sum(increase(node_cpu_seconds_total[{query_time}s])) by (instance))"
    # results = query_prometheus(query_expression)
    # min_usage = 100
    # min_usage_index = 0

    # for i in range(len(results)):
        # info_obj.ips[results[i]['metric']['instance'][:-5]] = float(results[i]['value'][1])
        # if float(results[i]['value'][1]) < min_usage:
            # min_usage = float(results[i]['value'][1])
            # min_usage_index = i
    
    # ip = results[min_usage_index]['metric']['instance'][:-5]
    
    # round roubin
    ip = info_obj.ipsl[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ipsl)

    return ip


info_obj = Info()


async def request_handler(request: web.Request):
    global info_obj

    ip = url_choose()
    headers = request.headers
    data = await request.json()
    
    # await asyncio.sleep(3)

    # url choose
    # ip = url_choose()
    url = f"http://{ip}:{info_obj.port}"

    # query_expression = r"100 - (avg by (instance) (irate(node_cpu_seconds_total{job='ubuntuDockerWorker',mode='idle'}[10m])) * 100)"
    # usages_list = query_prometheus(query_expression)
   
    # start = time.time()
    # await asyncio.sleep(3)

    print(f"trans-forward to {ip}")
    
    try:
        async with info_obj.session.post(url=url, json=data, headers=headers) as response:
            data = await response.json()
            print(data)
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            data["ip"] = ip
            print("DATA from backend:", data)
            
            # usages = info_obj.ips
            # res.update({'usages': usages})
            
            return web.json_response(data)

    

    except Exception as e:
        print("Error", e, data)



async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())

    return app
    


if __name__ == "__main__":
    try:
        app = server_app_init()
        web.run_app(app, host='0.0.0.0', port=8081)
    except Exception as e:
        print(e)
