#  Test for poisson distribution to three algorithm


import aiohttp
import asyncio
import random
from typing import List
import time
from clients_v2.time_graph.generate_graph import BarChartCanvas, LinearChartCanvas
from pathlib import Path
import numpy as np
import logging

# log file config
PARENT_DIR = Path(__file__).parent
log_path = PARENT_DIR / 'logs' / f"{Path(__file__).stem}.log"

log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.touch(exist_ok=True)
logging.basicConfig(filename=log_path, level=logging.INFO, filemode='w')


class Task:
    def __init__(self, **kw):
        self.headers = kw.get("headers") or dict()
        self.data = kw.get('data') or dict()
        self.url = kw.get('url')


class CustomClient:
    def __init__(self, **kw):
        self.loop_interval = kw.get('loop_interval') or 0

        self.tasks: List[Task] = kw.get('tasks')
        self.task_interval = kw.get('task_interval') or 0

        self.tasks_corotine_list = list()

        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0), timeout=aiohttp.ClientTimeout(total=None))

        self.responses: List[dict] = list()

    async def run_task(self, task: Task, tasks_sum: int):
        global FINISH_CNT, LOOPS, LOOP_FINISH_CNT, ERROR

        # recoard task start time
        start = time.time()
        async with self.session.post(url=task.url, json=task.data, headers=task.headers) as response:
            response_data = await response.json()
            FINISH_CNT += 1
            LOOP_FINISH_CNT += 1
            print(f"\r{FINISH_CNT}/{tasks_sum * len(ALGO_NAMES) * LOOPS} {LOOP_FINISH_CNT}/{tasks_sum}")
            print(f"\r{100 * FINISH_CNT/(tasks_sum * len(ALGO_NAMES) * LOOPS):.2f}% {100 * LOOP_FINISH_CNT/tasks_sum:.2f}%")
            response_data['response_time'] = time.time() - start        # recoard task end time

            logging.info(f"DIFF: {response_data['pred_task_wait_time'] - response_data['real_task_wait_time']}")
            ERROR.append(response_data['pred_task_wait_time'] - response_data['real_task_wait_time'])
            return response_data

    async def run_tasks(self, tasks_sum: int):
        index = 0
        for task in self.tasks:
            self.tasks_corotine_list.append(asyncio.create_task(self.run_task(task, tasks_sum)))
            print(f"\rSend Task {index + 1}")
            await asyncio.sleep(self.task_interval)
            index += 1

        # request order
        self.responses = await asyncio.gather(*self.tasks_corotine_list, return_exceptions=True)


        # # response order
        # self.responses = []
        # for completed_task in asyncio.as_completed(self.tasks_corotine_list):
        #     result = await completed_task
        #     self.responses.append(result)


def gen_tasks(is_random: bool, n, *args, **kwargs):
    global URL, HEADERS

    num_args = kwargs.get('num_args')
    tasks = list()
    headers = HEADERS
    url: str = URL
    if is_random:
        for _ in range(n):
            data = {"number": random.randint(TASK_NUMBER_RANGE[0], TASK_NUMBER_RANGE[1])}
            tasks.append(Task(url=url, headers=headers, data=data))
    else:
        tasks = [Task(url=url, headers=headers, data={"number": arg}) for arg in num_args]
    
    return tasks



def result_parse(results: dict):
    parsed_results = []
    for value in results.values():
        parsed_results.append(value)

    return parsed_results



def gen_tasks_poisson_1(n, *args, **kwargs):
    global URL, HEADERS, TASK_NUMBER_RANGE
    TASK_NUMBER_LAMBDA = (TASK_NUMBER_RANGE[0] + TASK_NUMBER_RANGE[1]) // 2
    tasks = list()
    headers = HEADERS
    url: str = URL
    # 使用泊松分布生成 num_args 列表
    # generate num_args list with poisson
    num_args = np.random.poisson(lam=TASK_NUMBER_LAMBDA, size=n).tolist()
    # 生成任务列表
    # generate tasks list
    tasks = [Task(url=url, headers=headers, data={"number": arg}) for arg in num_args]
    
    return tasks


def gen_tasks_poisson_2(n, *args, **kwargs):
    tasks = list()
    headers = HEADERS
    url: str = URL

    # 使用泊松分布波动生成任务参数
    # generate task request number with poisson
    num_args = [
        int(np.random.poisson(lam=200000)) if num % 3 != 0 else int(np.random.poisson(lam=500000))
        for num in range(n)
    ]
    tasks = [Task(url=url, headers=headers, data={"number": arg}) for arg in num_args]

    return tasks

async def main(tasks_sum: List[int]):
    global LOOPS, LOOP_INTERVAL, TASK_INTERVAL, FINISH_CNT, ALGO_NAMES, LOOP_FINISH_CNT, TASK_NUMBER_RANGE

    time_results = { algo_name: [] for algo_name in ALGO_NAMES }
    
    # random
    # tasks = gen_tasks(is_random=False, num_args=[150000 if num % 3 != 0 else 450000 for num in range(tasks_sum)], n=tasks_sum)
    

    # poisson 1
    tasks = gen_tasks_poisson_1(n=tasks_sum)
    
    # poisson 2
    # tasks = gen_tasks_poisson_2(n=tasks_sum)
    
    client = CustomClient(loop_interval=LOOP_INTERVAL, task_interval=TASK_INTERVAL, single_url=URL)
    for tasks_sum in TASKS_SUM:
        client.tasks = tasks

        
        for algo_name in ALGO_NAMES:
            start_time = time.time()
            HEADERS['algo_name'] = algo_name
            
            start_time = time.time()

            print(f"LOOP: {TASKS_SUM.index(tasks_sum) + 1} | ALGO_NAME: {algo_name}")
            await client.run_tasks(tasks_sum)
            await asyncio.sleep(client.loop_interval)    
            LOOP_FINISH_CNT = 0

            time_results[algo_name].append(time.time() - start_time)
    await client.session.close()
        
    # Canvas
    data = {
        "x_list": [
            [loop for loop in range(LOOPS)]
        ],
        "y_lists": [
            result_parse(time_results),
            # more figures
            # ...
        ],
        "titles": [
            "Respons time comparison",
        ],
        "xlabels": [
            "Loops Index",
        ],
        "ylabels": [
            "Response Time"
        ],
        "smooth": False,
        "window_size": 2,
        "legends": [
            name for name in time_results.keys()
        ]
    }
    canvas = BarChartCanvas(**data)
    # canvas = LinearChartCanvas(**data)
    
    canvas.save(Path.cwd() / 'clients_v2' / 'zlx_figs' / 'fig_v2' / 'poisson_n' / f'fig_{time.strftime("%X")}_{tasks_sum}_random_v5'.replace(':', ''))


TASK_NUMBER_RANGE = (100000, 500000)
TASKS_SUM = [30]
# TASKS_SUM = [1000]
TASK_INTERVAL = 0
LOOPS = 4
LOOP_INTERVAL = 0
MANAGER_AGENT_IP = "192.168.0.100"
MANAGER_AGENT_PORT = 8199
URL = f"http://{MANAGER_AGENT_IP}:{MANAGER_AGENT_PORT}"
HEADERS = {"task-type": "C"}
FINISH_CNT = 0
LOOP_FINISH_CNT = 0
ALGO_NAMES = ['proposed', 'round-robin', 'leatest']

ERROR = []


if __name__ == "__main__":
    for loop in range(LOOPS):
        asyncio.run(main(TASKS_SUM))

        # ERROR BarChart
        data= {
            "x_list": [
                [n for n in range(len(ERROR))], 
            ],
            "y_lists": [
                [ ERROR ],
            ],
            "titles": [
                "Difference of time for real and pred",
            ],
            "xlabels": [
                "Seconds",
            ],
            "ylabels": [
                "Task Index", 
            ],
            "legends": [
                "Difference of time",
            ],
        }

        canvas = BarChartCanvas(**data)
        canvas.save(Path.cwd() / 'clients_v2' / 'zlx_figs' / 'fig_test' / 'diff')
