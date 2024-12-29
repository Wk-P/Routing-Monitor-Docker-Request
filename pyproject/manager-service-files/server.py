import aiohttp
from aiohttp import web
import time
from datetime import datetime
import traceback
import asyncio
from asyncio import Queue
import logging
from pathlib import Path
import random
from xgboost import Booster
import xgboost


# xgboost model
process_model_path = str(Path.cwd() / "xgb_number_time.json")
xgboost_proc_model = Booster()
xgboost_proc_model.load_model(process_model_path)


# LOG file
log_path = Path.cwd() / 'log' / f"{__file__}.log"
print("Log Path:", log_path)
logging.basicConfig(filename=log_path, level=logging.INFO, filemode='w')

# tasks waiting queue
# for all tasks waiting timer
class Task:
    def __init__(self, **kwargs):
        # request data
        self.request_data: dict = kwargs.get('request_data')
        self.headers: dict = kwargs.get('headers')
        self.worker: Worker = None
        self.target_url = None
        self.pred_processed_time = self.predict_processed_time()
        self.serving_worker_number = None
        self.wait_time = float(0)
        # record how long time until receive response
        self.until_response_time = 0

        # resource usage
        self.hdd_usage = 0
        self.mem_usage = 0


    def predict_processed_time(self):
        data = xgboost.DMatrix([[self.request_data.get('number')]])
        prediction = xgboost_proc_model.predict(data)
        return float(prediction[0])

class Worker:
    def __init__(self, **kwargs):
        self.ip = kwargs.get('ip')
        self.port = kwargs.get('port')
        self.url = f'http://{self.ip}:{self.port}'
        self.lock = asyncio.Lock()
        
        self.update_interval = kwargs.get('update_interval')
        self.wait_time = float(0)

        self.current_task = None

        # every status tasks sum on worker
        self.processing_cnt = 0
        self.received_cnt = 0
        self.finished_cnt = 0

        # tasks queue on manager ( to calculate not to control )
        self.tasks_queue = Queue()

        # resource usage
        self.hdd_usage = 0
        self.mem_usage = 0

        self.max_hdd_usage = 0
        self.max_mem_usage = 0

        # session for worker connector
        self.session = None

    async def start_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0), timeout=aiohttp.ClientTimeout(total=None))

    async def close_session(self):
        await self.session.close()

    # update timer with 
    async def update_wait_time(self):
        while True:
            await asyncio.sleep(self.update_interval)
            self.wait_time -= self.update_interval
            if self.wait_time < 0:
                self.wait_time = 0


UPDATE_INTERVAL = 0.001

WORKERS = [
    Worker(ip='192.168.0.150', port=8080, update_interval=UPDATE_INTERVAL),
    Worker(ip='192.168.0.151', port=8080, update_interval=UPDATE_INTERVAL),
    Worker(ip='192.168.0.152', port=8080, update_interval=UPDATE_INTERVAL),
]

ROUND_ROUBIN_WORKER_INDEX = 0

async def start_sessions():
    global WORKERS
    for worker in WORKERS:
        await worker.start_session()


# multi IP addresses
def choose_url_algorithm(name=None):
    global WORKERS, ROUND_ROUBIN_WORKER_INDEX
    if not name or name == 'round-robin': # round robin
        worker_index = ROUND_ROUBIN_WORKER_INDEX
        ROUND_ROUBIN_WORKER_INDEX = (ROUND_ROUBIN_WORKER_INDEX + 1) % len(WORKERS)
        return WORKERS[worker_index]
    else:
        pass



async def handle_new_task(request_data: dict, headers: dict):
    global WORKERS
    new_task = Task(request_data=request_data, headers=headers)
    
    # set new_task params
    # ...
    # ...
    # predict process time
    
    # algorithm 
    chosen_worker = choose_url_algorithm()

    new_task.worker = chosen_worker
    new_task.target_url = chosen_worker.url
    new_task.serving_worker_number = WORKERS.index(chosen_worker)
    
    new_task.wait_time = chosen_worker.wait_time
    
    chosen_worker.current_task = new_task

    # add waiting time
    # 将预测处理时间加入 wait_time
    async with chosen_worker.lock:
        chosen_worker.wait_time += new_task.pred_processed_time
        chosen_worker.processing_cnt += 1

    # put into worker queue
    await chosen_worker.tasks_queue.put(new_task)

    return chosen_worker, new_task

# handle request main function
async def request_handler(request: web.Request):
    try:
        # received time
        manager_received_timestamp = time.time()
        logging.info(f"received time: {manager_received_timestamp}\n")

        # generate task and put into manager tasks queue
        request_data = await request.json()
        choosen_worker, new_task = await handle_new_task(request_data, request.headers)
        
        processing_cnt = choosen_worker.processing_cnt
        # fetch queue first task and send
        
        print('-' * 40, end='\n')
        print("Before", time.time(), f"Request number {new_task.request_data.get('number')}")
        print(f"task prediction process time {new_task.pred_processed_time}")
        print(f"worker node nummber:{new_task.serving_worker_number}")
        print("processing_cnt:", choosen_worker.processing_cnt)
        print("task wait time", new_task.wait_time)
        print("total predict response time", new_task.wait_time + new_task.pred_processed_time)
        total_response_time_prediction = new_task.wait_time + new_task.pred_processed_time

        before_forward_time = time.time() - manager_received_timestamp

        await choosen_worker.tasks_queue.get()

        # send this task to worker node
        async with choosen_worker.session.post(url=choosen_worker.url, json=new_task.request_data, headers=new_task.headers) as response:
            data: dict = await response.json()

            # 记录任务结束时间

            async with choosen_worker.lock:
                choosen_worker.finished_cnt += 1
                choosen_worker.processing_cnt -= 1
            if "error" in data.keys():
                data["success"] = 0
            else:
                data["success"] = 1

            # update response data
            data["choosen_ip"] = choosen_worker.ip
            data['processed_time'] = data.pop("real_process_time")
            data['jobs_on_worker_node'] = processing_cnt
            data['total_response_time_prediction'] = total_response_time_prediction
            data['worker_wait_time'] =  data['start_process_time'] - manager_received_timestamp
            data['before_forward_time'] = before_forward_time

            logging.info(f'{"-" * 40}\n')
            logging.info(f'{data}\n')
            logging.info(f"{'Before waiting jobs:':<50}{processing_cnt:<20}\n")
            logging.info(f"{'worker wait time:':<50}{data['worker_wait_time']:<20}\n")
            logging.info(f"{'Datetime:':<50}{datetime.ctime(datetime.now()) :<20}\n")

            print('-' * 40, end='\n')
            print("After", time.time(), f"Request number {new_task.request_data.get('number')}")
            print(f"worker node nummber:{new_task.serving_worker_number}")
            print("processing_cnt:", choosen_worker.processing_cnt)
            
            return web.json_response(data)

    except Exception:
        error_message = traceback.format_exc()
        print(error_message)
        return web.json_response({"error": error_message, "data": data}, status=500)


async def on_shutdown(app):
    global WORKERS
    for worker in WORKERS:
        await worker.close_session()

async def server_app_init():
    global WORKERS
    for worker in WORKERS:
        asyncio.create_task(worker.update_wait_time())

    print("Workers' timer has started")

    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: start_sessions())
    app.on_cleanup.append(on_shutdown)

    return app

def server_run():
    try:
        app = server_app_init()
        web.run_app(app, host='0.0.0.0', port=8100)
    except Exception as e:
        print(f"[ {datetime.ctime(datetime.now()) }]")
        print(e)


if __name__ == "__main__":
    server_run()
