import aiohttp
from aiohttp import web
import time


class WorkerNodeInfo():
    def __init__(self):
        self.ips = [
            "192.168.0.150",
            "192.168.0.151",
            "192.168.0.152",
        ]
        self.port = 8080
        self.session = None
        self.current_index = 0

    async def start_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0), timeout=aiohttp.ClientTimeout(total=None))


def url_choose():
    global info_obj
    ip = info_obj.ips[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ips)
    return ip


async def request_handler(request: web.Request):
    global info_obj
    global received_cnt
    global finished_cnt

    index = received_cnt
    manager_received_timestamp = time.time()

    # index
    print("index: ", index)

    # received time
    print("received time: ", time.time())
    print("received index: ", received_cnt)
    received_cnt += 1



    ip = url_choose()
    headers = request.headers
    data = await request.json()
    
    received_into_manager_node = time.time()

    # url choose
    # ip = url_choose()
    url = f"http://{ip}:{info_obj.port}"
    print(f"trans-forward to {ip}")
    
    try:
        processing_cnt = received_cnt - finished_cnt
        async with info_obj.session.post(url=url, json=data, headers=headers) as response:
            data:dict = await response.json()
            response_received_timestamp = time.time()
            process_in_manager_node = response_received_timestamp - received_into_manager_node
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1


            # update response data
            data["ip"] = ip
            data["wait_time_in_worker_node"] = data.pop("request_wait_time")
            data['waiting_tasks_in_worker_node'] = data.pop('waiting_cnt')
            data["process_in_manager_node"] = process_in_manager_node - data['process_time'] - data['wait_time_in_worker_node']
            data.pop('start_process_timestamp')
            data['process_in_worker_node'] = data.pop("process_time")
            data['processing_tasks_in_worker_node'] = processing_cnt
            data['manager_received_timestamp'] = manager_received_timestamp
            data['request_ordered_index'] = index
            data['response_received_timestamp'] = response_received_timestamp

            finished_cnt += 1
            index += 1
            return web.json_response(data)

    

    except Exception as e:
        print("Error", e, data)



async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())

    return app
    

info_obj = WorkerNodeInfo()
received_cnt = 0
finished_cnt = 0


if __name__ == "__main__":
    try:
        app = server_app_init()
        web.run_app(app, host='0.0.0.0', port=8081)
    except Exception as e:
        print(e)
