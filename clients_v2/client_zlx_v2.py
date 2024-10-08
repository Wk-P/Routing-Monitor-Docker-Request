import aiohttp
import asyncio
import random
from typing import List


TASK_NUMBER_RANGE = (0, 500000)
TASKS_SUM = 10
MANAGER_AGENT_IP = "192.168.0.100"
MANAGER_AGENT_PORT = 8100
URL = f"http://{MANAGER_AGENT_IP}:{MANAGER_AGENT_PORT}"
HEADERS = {"task-type": "C"}

class Task:
    def __init__(self, **kw):
        self.headers = kw.get("headers") or dict()
        self.data = kw.get('data') or dict()
        self.url = kw.get('url')


class CustomClient:
    def __init__(self, **kw):
        self.loops = kw.get('loop') or 0
        self.loop_interval = kw.get('loop_interval') or 0

        self.tasks: List[Task] = kw.get('tasks')
        self.task_interval = kw.get('task_interval') or 0

        self.tasks_corotine_list = list()

        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0), timeout=aiohttp.ClientTimeout(total=None))

        self.responses: List[dict] = list()

    async def run_task(self, task: Task):
        print(task.data)
        async with self.session.post(url=task.url, json=task.data, headers=task.headers) as response:
            response_data = await response.json()
            
            return response_data

    async def run_tasks(self):
        index = 0
        for task in self.tasks:
            self.tasks_corotine_list.append(asyncio.create_task(self.run_task(task)))
            print(f"Send Task {index}")
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
    global TASKS_SUM
    client = CustomClient(loop=1, loop_interval=1, tasks=gen_tasks(is_random=True, n=TASKS_SUM), task_interval=0, single_url=URL)

    for loop in range(client.loops):
        
        await client.run_tasks()

        for response in client.responses:
            for k, v in response.items():
                print(k, v)

        await asyncio.sleep(client.loop_interval)    

if __name__ == "__main__":
    asyncio.run(main())

