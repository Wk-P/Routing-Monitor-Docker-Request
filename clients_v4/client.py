import time
import asyncio
import json
from aiohttp import TCPConnector, ClientTimeout, ClientSession, ClientResponse
from datetime import datetime
from tools.utils import write_json_file
from pathlib import Path
import uuid
import numpy as np
import matplotlib.pyplot as plt

WORK_DIR = Path(__file__).parent
SERVER_URL = "http://192.168.0.100:8199"

class Result:
    def __init__(self, **data):
        self.__dict__.update(data)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)

def draw_plot(filepath: Path, filename: str, data: dict, title: str, XLabel: str, YLabel: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)
    count = sum(1 for file in filepath.iterdir() if file.is_file() and file.suffix == '.png')
    filename = f"{filename}_{count}" if count > 0 else filename
    full_path = filepath / f"{filename}.png"
    x = list(data.keys())
    y = list(data.values())
    plt.figure(figsize=(16, 9))
    plt.plot(x, y, marker="o", label="Avg Response Time")
    plt.title(title)
    plt.xlabel(XLabel)
    plt.ylabel(YLabel)
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(full_path))
    plt.close()

def draw_bar(filepath: Path, filename: str, data: dict, title: str, XLabel: str, YLabel: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)
    count = sum(1 for file in filepath.iterdir() if file.is_file() and file.suffix == '.png')
    filename = f"{filename}_{count}" if count > 0 else filename
    full_path = filepath / f"{filename}.png"
    x_labels = data.get('x_labels')
    y_values = data.get('y_values')
    plt.bar(x_labels, y_values)
    plt.xticks(ticks=range(len(x_labels)), labels=x_labels)
    plt.xlabel(XLabel)
    plt.ylabel(YLabel)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(full_path)
    plt.close()

def generate_request_id():
    return f"{int(time.time() * 1000)}_{uuid.uuid4().hex}"

# 提交任务
async def submit_task(session: ClientSession, request_data: dict):
    url = f"{SERVER_URL}/submit_task"
    async with session.post(url, json=request_data) as resp:
        if resp.status != 200:
            text = await resp.text()
            print(f"Submit failed: {resp.status}, {text}")
            return None
        result = await resp.json()
        return result.get('task_id')

# 轮询任务结果
async def poll_result(session: ClientSession, task_id: str):
    url = f"{SERVER_URL}/get_result"
    params = {'task_id': task_id}
    start_time = time.perf_counter()
    while True:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                await asyncio.sleep(0.5)
                continue
            result = await resp.json()
            if result.get('status') == 'processing':
                await asyncio.sleep(0.5)
            elif result.get('status') == 'not_found':
                print(f"Task {task_id} not found.")
                return None
            else:
                response_time = time.perf_counter() - start_time
                return Result(
                    status_code="OK",
                    responese_time=response_time,
                    handle_worker=result.get('selected_worker_id')
                )

async def run_one_request(session: ClientSession, request_data: dict):
    task_id = await submit_task(session, request_data)
    if task_id:
        return await poll_result(session, task_id)
    await asyncio.sleep(0.05)
    return None

async def main(loop, folder_name: Path):
    batches = [10 for _ in range(1, 10)]
    all_results = []
    dir_path = folder_name / f'{loop}_results'

    for nr in batches:
        async with ClientSession(connector=TCPConnector(limit=0), timeout=ClientTimeout(None)) as session:
            tasks = [
                asyncio.create_task(run_one_request(session, {
                    "number": 200000,
                    "request_id": generate_request_id(),
                    "algo_name": "proposed"
                })) for _ in range(nr)
            ]
            await asyncio.sleep(2)
            results = await asyncio.gather(*tasks)

            batch_dispatch_data = {}
            for result in results:
                if isinstance(result, Result):
                    worker = result.to_dict().get('handle_worker')
                    batch_dispatch_data[worker] = batch_dispatch_data.get(worker, 0) + 1
                else:
                    print("One request failed.")

            parsed_result = {
                "request_sum": nr,
                "avg_response_time": float(np.mean([result.to_dict().get('responese_time', 0) for result in results if result])),
                "handle_worker": batch_dispatch_data
            }
            all_results.append(parsed_result)

    write_json_file(filepath=dir_path, filename=f'{len(batches)}_results', mode='a', data=all_results)

    parsed_all_results = {r['request_sum']: r['avg_response_time'] for r in all_results}
    draw_plot(filepath=dir_path, filename=f"comparison_{len(batches)}", data=parsed_all_results,
              title='Requests vs Response Time', XLabel="Requests", YLabel="Avg Response Time (s)")

    dispatches_data = {}
    for result in all_results:
        for worker_id, requests in result['handle_worker'].items():
            dispatches_data[worker_id] = dispatches_data.get(worker_id, 0) + requests

    return dispatches_data

async def run_main():
    loop = 1
    folder_name = WORK_DIR / 'results' / datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    all_dispatched_data = {}
    for l in range(1, loop + 1):
        dispatched_data = await main(l, folder_name)
        for worker_id, count in dispatched_data.items():
            all_dispatched_data[worker_id] = all_dispatched_data.get(worker_id, 0) + count

    draw_bar(filepath=folder_name, filename='all_dispatched_data',
             data={"x_labels": list(all_dispatched_data.keys()), "y_values": list(all_dispatched_data.values())},
             title='Tasks Assigned to Workers', XLabel='Worker', YLabel='Number of Requests')

if __name__ == "__main__":
    asyncio.run(run_main())
