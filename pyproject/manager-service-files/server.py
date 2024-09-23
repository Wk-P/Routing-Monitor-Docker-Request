import aiohttp
from aiohttp import web
import time
from datetime import datetime
import traceback
import asyncio
import logging
from pathlib import Path
logging.basicConfig(filename=str(Path.cwd() / 'log' /'server-output.log'), level=logging.INFO, filemode='w')

# multi IP addresses
class WorkerNodeInfo:
    def __init__(self, multi_ip=False):
        if multi_ip:
            self.ips = [
                "192.168.0.150",
                "192.168.0.151",
                "192.168.0.152",
            ]
        else:
            self.ips = [
                "192.168.0.150",
            ]

        self.cnt_group = {ip: {'received': 0, 'processing': 0, 'finished': 0} for ip in self.ips}
        self.locks = {ip: asyncio.Lock() for ip in self.ips}

        self.port = 8080
        self.sessions = None
        self.current_index = 0

    async def start_session(self):
        self.sessions = {ip: aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0),
            timeout=aiohttp.ClientTimeout(total=None)  # Custom timeout per session
        ) for ip in self.ips}


    async def close_sessions(self):
        for session in self.sessions.values():
            await session.close()

def url_choose():
    global info_obj
    ip = info_obj.ips[info_obj.current_index]
    info_obj.current_index = (info_obj.current_index + 1) % len(info_obj.ips)
    return ip



async def request_handler(request: web.Request):
    global info_obj, loop
    # global xgboost_proc_model

    manager_received_timestamp = time.time()
    request_data = await request.json()

    # received time
    logging.info(f"received time: {manager_received_timestamp}\n")

    # # predict request process time
    # _X = xgboost.DMatrix([[request_data['number']]])
    # prediction = xgboost_proc_model.predict(_X)[0]

    # url choose and create url
    ip = url_choose()

    # predict_waiting_time = 0

    async with info_obj.locks[ip]:  
        info_obj.cnt_group[ip]['received'] += 1
        info_obj.cnt_group[ip]['processing'] = info_obj.cnt_group[ip]['received'] - info_obj.cnt_group[ip]['finished']
        sub_processing_cnt = info_obj.cnt_group[ip]['processing']

    url = f"http://{ip}:{info_obj.port}"
    headers = request.headers

    logging.info(f"trans-forward to {ip}\n")

    try:
        data = dict()
        async with info_obj.sessions[ip].post(url=url, json=request_data, headers=headers) as response:
            data: dict = await response.json()
            async with info_obj.locks[ip]:
                info_obj.cnt_group[ip]['finished'] += 1
                info_obj.cnt_group[ip]['processing'] -= 1
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            # update response data
            data["choosen_ip"] = ip
            data['processed_time'] = data.pop("real_process_time")
            # data['jobs_on_worker_node'] = info_obj.cnt_group[ip]['processing']
            data['jobs_on_worker_node'] = sub_processing_cnt

            data['worker_wait_time'] =  data['start_process_time'] - manager_received_timestamp
            logging.info(f'{"-" * 40}')
            logging.info(f'{data}\n')
            logging.info(f"{'processing jobs:':<50}{sub_processing_cnt:<20}\n")
            logging.info(f"""{'info_obj.cnt_group[ip]["processing"]:':<50}{info_obj.cnt_group[ip]['processing']:<20}\n""")
            logging.info(f"{'worker wait time:':<50}{data['worker_wait_time']:<20}\n")
            logging.info(f"{'info_obj.cnt_group:':<50}{info_obj.cnt_group}\n")
            logging.info(f"{'Datetime:':<50}{datetime.ctime(datetime.now()) :<20}\n")
            logging.info(f'{"-" * 40}\n')

            return web.json_response(data)

    except Exception:
        error_message = traceback.format_exc()
        return web.json_response({"error": error_message, "data": data}, status=500)


async def on_shutdown(app):
    await info_obj.close_sessions()

async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())
    app.on_cleanup.append(on_shutdown)

    return app


info_obj = WorkerNodeInfo(multi_ip=False)
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
