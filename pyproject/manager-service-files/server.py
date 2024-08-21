import aiohttp
from aiohttp import web
import time
from datetime import datetime
from xgboost import Booster
from pathlib import Path
import numpy as np
import xgboost


# request queue enable
is_request_queue_enable = False


class WorkerNodeInfo():
    def __init__(self):
        self.ips = [
            "192.168.0.150",
            "192.168.0.151",
            "192.168.0.152",
        ]
        # self.ips = [
        #     "192.168.0.150",
        # ]
        self.cnt_group = {
            "192.168.0.150": {
                'received': 0,
                'processing': 0,
                'finished': 0
            },
            "192.168.0.151": {
                'received': 0,
                'processing': 0,
                'finished': 0
            },
            "192.168.0.152": {
                'received': 0,
                'processing': 0,
                'finished': 0
            },
        }

        self.port = 8080
        self.session = None
        self.current_index = 0

    async def start_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            limit=None), timeout=aiohttp.ClientTimeout(total=None))


def url_choose():
    global info_obj
    ip = info_obj.ips[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ips)
    return ip


def request_predict(request_number, tasks_number, model: Booster):
    X = np.array(
        [[request_number, tasks_number]]
    )
    X = xgboost.DMatrix(X)
    prediction = model.predict(X)
    prediction = float(prediction[0])
    return prediction


async def request_for_psutil(ip, port):
    global psutil_session

    def ip_to_url(ip, port):
        return f"http://{ip}:{port}"

    headers = {"task-type": "PS"}

    data = {"ip": ip, "url": ip_to_url(ip, port)}

    async with psutil_session.post(url=data['url'], headers=headers) as response:
        data = await response.json()
        return data


async def request_handler(request: web.Request):
    global info_obj
    global received_cnt
    global finished_cnt
    global waiting_queue_list
    global xgboost_model
    global psutil_session

    index = received_cnt
    manager_received_timestamp = time.time()

    # update processing
    processing_cnt = received_cnt - finished_cnt

    # index
    print("index: ", index)

    # received time
    print("received time: ", time.time())
    print("received index: ", received_cnt)
    received_cnt += 1

    # request for host resouces
    resources_status = list()
    for ip in info_obj.ips:
        resources_status.append(await request_for_psutil(ip, info_obj.port))

    print(resources_status)

    # url choose and create url
    ip = url_choose()

    info_obj.cnt_group[ip]['received'] += 1
    info_obj.cnt_group[ip]['processing'] = info_obj.cnt_group[ip]['received'] - \
        info_obj.cnt_group[ip]['finished']

    url = f"http://{ip}:{info_obj.port}"
    headers = request.headers
    request_data = await request.json()

    # add all waiting time
    # thread security

    for ip in info_obj.ips:
        _processing_cnt = info_obj.cnt_group[ip]['processing']
        prediction = request_predict(
            int(request_data['number']), _processing_cnt, xgboost_model)

    print(f"trans-forward to {ip}")

    try:
        async with info_obj.session.post(url=url, json=request_data, headers=headers) as response:
            data: dict = await response.json()
            response_received_timestamp = time.time()
            process_in_manager_node = response_received_timestamp - manager_received_timestamp
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            # update response data
            data["choosen_ip"] = ip
            data["processed_and_waited_time_on_manager_node"] = process_in_manager_node
            data['processed_time_on_worker_node'] = data.pop(
                "real_process_time")
            # waiting to be processed(transforward) and sended to worker node request
            data['processing_tasks_on_manager_node'] = processing_cnt
            data['manager_received_request_timestamp'] = manager_received_timestamp
            data['request_ordered_index'] = index
            data['response_received_timestamp_on_manager_node'] = response_received_timestamp
            data['prediction'] = prediction

            finished_cnt += 1
            index += 1

            info_obj.cnt_group[ip]['finished'] -= 1

            print("data: ", data)

            return web.json_response(data)

    except Exception as e:
        print("Error", e, data)
        return web.json_response({"error": str(e), "data": data})


async def start_psutil_session():
    global psutil_session
    psutil_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(
        limit=None), timeout=aiohttp.ClientTimeout(total=None))


async def server_app_init():
    global info_obj
    global psutil_session
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())
    app.on_startup.append(lambda psutil_session: start_psutil_session())

    return app


info_obj = WorkerNodeInfo()
received_cnt = 0
finished_cnt = 0
waiting_queue_list = list()
psutil_session = None


# model included
model_path = str(Path.cwd() / "xgb_tasks_time.json")
xgboost_model = Booster()
xgboost_model.load_model(model_path)


def server_run():
    try:
        app = server_app_init()
        web.run_app(app, host='0.0.0.0', port=8081)
    except Exception as e:
        print(f"[ {datetime.ctime(datetime.now())}]")
        print(e)


if __name__ == "__main__":
    server_run()
