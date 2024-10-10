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
        global FINISH_CNT, TASKS_SUM
        async with self.session.post(url=task.url, json=task.data, headers=task.headers) as response:
            response_data = await response.json()
            FINISH_CNT += 1
            print(f"{FINISH_CNT}/{TASKS_SUM}")
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
    global TASKS_SUM, LOOPS, LOOP_INTERVAL, TASK_INTERVAL, FINISH_CNT, TASKS

    for i in range(2):
        if i == 0:
            HEADERS['algo_name'] = 'round-robin'
        else:
            HEADERS['algo_name'] = 'shortest'

        client = CustomClient(loops=LOOPS, loop_interval=LOOP_INTERVAL, tasks=TASKS, task_interval=TASK_INTERVAL, single_url=URL)

        all_time_list = list()

        for loop in range(client.loops):
            start = time.time()
            await client.run_tasks()
            
            FINISH_CNT = 0

            end = time.time()
            all_time_list.append(end - start)
            await asyncio.sleep(client.loop_interval)    

        figplt.main([[figplt.Data(all_time_list, 'response time')]], ["Response Time"], direction='row', fig_name=f'test_{i}{HEADERS['algo_name']}.png', fig_dir_path=Path.cwd())
        figplt.print_avg(all_time_list, name='average of response time')

    await client.session.close()

TASK_NUMBER_RANGE = (0, 500000)
TASKS_SUM = 300
TASK_INTERVAL = 0.3
LOOPS = 1
LOOP_INTERVAL = 0.3
MANAGER_AGENT_IP = "192.168.0.100"
MANAGER_AGENT_PORT = 8199
URL = f"http://{MANAGER_AGENT_IP}:{MANAGER_AGENT_PORT}"
HEADERS = {"task-type": "C"}
FINISH_CNT = 0
TASKS = gen_tasks(is_random=True, n=TASKS_SUM)


if __name__ == "__main__":
    asyncio.run(main())

