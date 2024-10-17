import aiohttp
import asyncio
import random
from typing import List
import time
from time_graph import generate_graph as figplt
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
        global FINISH_CNT, TASKS_SUM, LOOPS
        async with self.session.post(url=task.url, json=task.data, headers=task.headers) as response:
            response_data = await response.json()
            FINISH_CNT += 1
            print(f"{FINISH_CNT}/{TASKS_SUM * LOOPS}")
            return response_data

    async def run_tasks(self):
        index = 0
        for task in self.tasks:
            self.tasks_corotine_list.append(asyncio.create_task(self.run_task(task)))
            print(f"Send Task {index}")
            await asyncio.sleep(self.task_interval)
            index += 1

        self.responses = await asyncio.gather(*self.tasks_corotine_list, return_exceptions=True)

def gen_tasks(is_random: bool, n, *args):
    global URL, HEADERS
    tasks = list()
    headers = HEADERS
    url: str = URL
    if is_random:
        tasks = [Task(url=url, headers=headers, data={"number": random.randint(TASK_NUMBER_RANGE[0], TASK_NUMBER_RANGE[1])}) for _ in range(n)]
    else:
        tasks = [Task(url=url, headers=headers, data={"number": arg}) for arg in args]
    
    return tasks


async def main():
    global TASKS_SUM, LOOPS, LOOP_INTERVAL, TASK_INTERVAL, FINISH_CNT, TASKS, ALGO_NAMES

    time_results = dict().fromkeys(ALGO_NAMES, [])

    for algo_name in ALGO_NAMES:
        HEADERS['algo_name'] = algo_name

        client = CustomClient(loops=LOOPS, loop_interval=LOOP_INTERVAL, tasks=TASKS, task_interval=TASK_INTERVAL, single_url=URL)

        all_time_list = list()

        for loop in range(client.loops):
            print(f"LOOP: {loop} | ALGO_NAME: {algo_name}")
            start = time.time()
            await client.run_tasks()
            
            end = time.time()
            all_time_list.append(end - start)
            await asyncio.sleep(client.loop_interval)    

        time_results[algo_name] = all_time_list

        await client.session.close()

        FINISH_CNT = 0

    figplt.main([[figplt.Data(all_time_list, f'{algo_name} response time') for algo_name, all_time_list in time_results.items()]], [[algo_name for algo_name in time_results.keys()]], direction='row', fig_name=f'result.png', fig_dir_path=Path.cwd())
    figplt.print_avg(all_time_list, name='average of response time')



TASK_NUMBER_RANGE = (0, 500000)
TASKS_SUM = 15
TASK_INTERVAL = 0.03
LOOPS = 5
LOOP_INTERVAL = 0.01
MANAGER_AGENT_IP = "192.168.0.100"
MANAGER_AGENT_PORT = 8199
URL = f"http://{MANAGER_AGENT_IP}:{MANAGER_AGENT_PORT}"
HEADERS = {"task-type": "C"}
FINISH_CNT = 0
TASKS = gen_tasks(is_random=True, n=TASKS_SUM)
ALGO_NAMES = ['round-robin', 'shortest']


if __name__ == "__main__":
    asyncio.run(main())

