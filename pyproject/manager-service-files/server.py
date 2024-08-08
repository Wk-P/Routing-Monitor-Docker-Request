import aiohttp
from aiohttp import web
import time
from queue import Queue
from xgboost import XGBRegressor #type: ignore
from pathlib import Path
import threading
from typing import List, Dict


class WorkerNodeInfo:
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
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0),
            timeout=aiohttp.ClientTimeout(total=None),
        )


def url_choose():
    global info_obj
    ip = info_obj.ips[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ips)
    return ip


async def request_handler(request: web.Request):
    global info_obj
    global received_cnt
    global finished_cnt
    global waiting_queue_list
    global model

    index = received_cnt
    manager_received_timestamp = time.time()

    # index
    print("index: ", index)

    # received time
    print("received time: ", time.time())
    print("received index: ", received_cnt)
    received_cnt += 1

    # url choose
    ip = url_choose()
    headers = request.headers
    data = await request.json()

    # add all waiting time
    # thread security
    lock = threading.Lock()

    waiting_tasks: List[Dict[str, float]] = list()
    sums = dict()

    with lock:
        # 复制队列的内容用以计算等待时间
        waiting_tasks = waiting_queue_list.copy()
        if waiting_tasks:
            for task in waiting_tasks:
                _k = task.get("worker_node_ip")
                _v: float = task.get("response_pred_time_for_every_worker_node")
                if _k and _v:
                    if _k not in sums:
                        sums[_k] = _v
                    else:
                        sums[_k] += _v
        del waiting_tasks

    waiting_queue_list.append(
        {
            "request_index": index,
            "request_num": data["number"],
            "response_pred_time_for_every_worker_node": float(
                model.predict([[data["number"]]]).tolist()[0]
            ),
            "worker_node_ip": ip,
        }
    )

    received_into_manager_node = time.time()

    # create url
    url = f"http://{ip}:{info_obj.port}"
    print(f"trans-forward to {ip}")

    try:
        # update processing
        processing_cnt = received_cnt - finished_cnt

        async with info_obj.session.post(
            url=url, json=data, headers=headers
        ) as response:
            data: dict = await response.json()
            response_received_timestamp = time.time()
            process_in_manager_node = (
                response_received_timestamp - received_into_manager_node
            )
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            # update response data
            data["choosen_ip"] = ip
            data["processed_and_waited_time_on_manager_node"] = (
                process_in_manager_node
                - data["real_process_time"]
                - data["wait_time_on_worker_node"]
            )
            data["processed_time_on_worker_node"] = data.pop("real_process_time")
            data["processing_tasks_on_manager_node"] = (
                processing_cnt  # waiting to be processed(transforward) and sended to worker node request
            )
            data["manager_received_request_timestamp"] = manager_received_timestamp
            data["request_ordered_index"] = index
            data["response_received_timestamp_on_manager_node"] = (
                response_received_timestamp
            )

            for key, value in sums.items():
                _key = f"response_predicted_time_for_{key}"
                data[_key] = value

            request_object = list(
                filter(lambda task: task["request_index"] == index, waiting_queue_list)
            )[0]
            waiting_queue_list.remove(request_object)

            finished_cnt += 1
            index += 1

            print("data: ", data)

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
waiting_queue_list = list()


# 模型预测
model_name = "xgb_number_time.json"
model_path = str(Path.cwd() / model_name)


print(model_path)


model = XGBRegressor()
model.load_model(model_path)


waiting_time_sums = dict()


if __name__ == "__main__":
    try:
        app = server_app_init()
        web.run_app(app, host="0.0.0.0", port=8081)
    except Exception as e:
        print(e)
