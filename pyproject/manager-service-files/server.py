import aiohttp
from aiohttp import web
import time
from datetime import datetime
from xgboost import Booster             # type: ignore  
from pathlib import Path
import xgboost                  # type: ignore
import traceback
import asyncio

# multi IP addresses
is_multi_ip = False

class WorkerNodeInfo:
    def __init__(self, multi_ip=True):
        if multi_ip:
            self.ips = [
                "192.168.0.150",
                "192.168.0.151",
                "192.168.0.152",
            ]
            # self.cnt_group = {
            #     "192.168.0.150": {
            #         'waiting_time': 0,
            #         'received': 0,
            #         'processing': 0,
            #         'finished': 0,
            #     },
            #     "192.168.0.151": {
            #         'waiting_time': 0,
            #         'received': 0,
            #         'processing': 0,
            #         'finished': 0,
            #     },
            #     "192.168.0.152": {
            #         'waiting_time': 0,
            #         'received': 0,
            #         'processing': 0,
            #         'finished': 0,
            #     },
            # }
        else:
            self.ips = [
                "192.168.0.150",
            ]
            self.cnt_group = {
                "192.168.0.150": {
                    'received': 0,
                    'processing': 0,
                    'finished': 0,
                },
            }

        self.port = 8080
        self.session = None
        self.current_index = 0

    async def start_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            limit=0), timeout=aiohttp.ClientTimeout(total=None))


def url_choose():
    global info_obj
    ip = info_obj.ips[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ips)
    return ip



async def request_handler(request: web.Request):
    global info_obj
    global _lock
    global loop
    # global xgboost_proc_model

    manager_received_timestamp = time.time()
    request_data = await request.json()

    # received time
    print("received time: ", manager_received_timestamp)

    # # predict request process time
    # _X = xgboost.DMatrix([[request_data['number']]])
    # prediction = xgboost_proc_model.predict(_X)[0]

    # url choose and create url
    ip = url_choose()

    # predict_waiting_time = 0

    async with _lock:
        info_obj.cnt_group[ip]['received'] += 1
        info_obj.cnt_group[ip]['processing'] = info_obj.cnt_group[ip]['received'] - info_obj.cnt_group[ip]['finished']
        sub_processing_cnt = info_obj.cnt_group[ip]['processing']

    url = f"http://{ip}:{info_obj.port}"
    headers = request.headers

    print(f"trans-forward to {ip}")


    try:
        manager_transforward_timestamp = time.time()
        async with info_obj.session.post(url=url, json=request_data, headers=headers) as response:
            async with _lock:
                info_obj.cnt_group[ip]['finished'] += 1
                info_obj.cnt_group[ip]['processing'] -= 1

            data: dict = await response.json()
            response_received_timestamp = time.time()
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            # update response data
            data["choosen_ip"] = ip
            data['processed_time'] = data.pop("real_process_time")
            data['jobs_on_worker_node'] = sub_processing_cnt

            data['worker_wait_time'] = response_received_timestamp - manager_received_timestamp - data['processed_time']
            print("-" * 40)
            print(data)
            print(f"{'processing jobs:':<50}{sub_processing_cnt:<20}")
            print(f"{'worker wait time:':<50}{data['worker_wait_time']:<20}")
            print(f"{'info_obj.cnt_group:':<50}{info_obj.cnt_group}")
            print("-" * 40)


            return web.json_response(data)

    except Exception as e:
        error_message = traceback.format_exc()
        return web.json_response({"error": error_message, "data": data}, status=500)


async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())

    return app


info_obj = WorkerNodeInfo(multi_ip=is_multi_ip)
_lock = asyncio.Lock()
sum_waiting_time = 0
loop = asyncio.get_event_loop()

# model included
# wait_model_path = str(Path.cwd() / "xgb_tasks_time.json")
# xgboost_wait_model = Booster()
# xgboost_wait_model.load_model(wait_model_path)


# process_model_path = str(Path.cwd() / "xgb_number_time.json")
# xgboost_proc_model = Booster()
# xgboost_proc_model.load_model(process_model_path)


def server_run():
    try:
        app = server_app_init()
        web.run_app(app, host='0.0.0.0', port=8081)
    except Exception as e:
        print(f"[ {datetime.ctime(datetime.now()) }]")
        print(e)


if __name__ == "__main__":
    server_run()
