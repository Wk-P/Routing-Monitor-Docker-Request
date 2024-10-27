import re
import aiohttp
import asyncio
import random
from typing import List
import time
from clients_v2.time_graph.generate_graph import Cavans
from pathlib import Path


class Task:
    def __init__(self, **kw):
        self.headers = kw.get("headers") or dict()
        self.data = kw.get('data') or dict()
        self.url = kw.get('url')


class CustomClient:
    def __init__(self, **kw):
        self.loops = kw.get('loops') or 0
        self.loop_interval = kw.get('loop_interval') or 0

        self.tasks: List[Task] = kw.get('tasks')
        self.task_interval = kw.get('task_interval') or 0

        self.tasks_corotine_list = list()

        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0), timeout=aiohttp.ClientTimeout(total=None))

        self.responses: List[dict] = list()

    async def run_task(self, task: Task):
        global FINISH_CNT, TASKS_SUM, LOOPS, LOOP_FINISH_CNT

        # recoard task start time
        start = time.time()
        async with self.session.post(url=task.url, json=task.data, headers=task.headers) as response:
            response_data = await response.json()
            FINISH_CNT += 1
            LOOP_FINISH_CNT += 1
            print(f"{FINISH_CNT}/{TASKS_SUM * LOOPS} {LOOP_FINISH_CNT}/{TASKS_SUM}")
            response_data['response_time'] = time.time() - start        # recoard task end time
            return response_data

    async def run_tasks(self):
        index = 0
        for task in self.tasks:
            self.tasks_corotine_list.append(asyncio.create_task(self.run_task(task)))
            print(f"Send Task {index + 1}")
            await asyncio.sleep(self.task_interval)
            index += 1

        self.responses = await asyncio.gather(*self.tasks_corotine_list, return_exceptions=True)


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




async def main():
    global TASKS_SUM, LOOPS, LOOP_INTERVAL, TASK_INTERVAL, FINISH_CNT, ALGO_NAMES, LOOP_FINISH_CNT, TASK_NUMBER_RANGE

    time_results = {algo_name: [] for algo_name in ALGO_NAMES}
    tasks = gen_tasks(is_random=False, num_args=[150000 if num % 3 != 0 else 450000 for num in range(TASKS_SUM)], n=TASKS_SUM)
    # tasks = gen_tasks(is_random=True, n=TASKS_SUM, x_n=5)
    for algo_name in ALGO_NAMES:
        HEADERS['algo_name'] = algo_name

        client = CustomClient(loops=LOOPS, loop_interval=LOOP_INTERVAL, tasks=tasks, task_interval=TASK_INTERVAL, single_url=URL)
        for loop in range(client.loops):
            print(f"LOOP: {loop + 1} | ALGO_NAME: {algo_name}")
            await client.run_tasks()
            await asyncio.sleep(client.loop_interval)    
            LOOP_FINISH_CNT = 0

        await client.session.close()

        FINISH_CNT = 0
        
        for response_data in client.responses:
            time_results[algo_name].append(response_data['response_time'])

    print(time_results)

    # Cavans
    data = {
        "x_list": [
            [task for task in range(TASKS_SUM)]
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
            "Tasks Index",
        ],
        "ylabels": [
            "Response Time"
        ],
        "legends": [
            name for name in time_results.keys()
        ]
    }
    cavans = Cavans(**data)
    cavans.save(Path.cwd() / 'clients_v2' / 'zlx_figs' / f'fig_{time.strftime("%X")}'.replace(':', ''))



TASK_NUMBER_RANGE = (10, 500000)
TASKS_SUM = 100
TASK_INTERVAL = 1
LOOPS = 1
LOOP_INTERVAL = 2
MANAGER_AGENT_IP = "192.168.0.100"
MANAGER_AGENT_PORT = 8199
URL = f"http://{MANAGER_AGENT_IP}:{MANAGER_AGENT_PORT}"
HEADERS = {"task-type": "C"}
FINISH_CNT = 0
LOOP_FINISH_CNT = 0
ALGO_NAMES = ['proposed', 'round-robin']
TEST_GROUPS_SUM = 1


if __name__ == "__main__":
    for group in range(TEST_GROUPS_SUM):
        asyncio.run(main())
