import re
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
    if count > 0:
        filename = f"{filename}_{count}"
    else:
        filename = f"{filename}"   

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
    if count > 0:
        filename = f"{filename}_{count}"
    else:
        filename = f"{filename}"   

    full_path = filepath / f"{filename}.png"

    x_labels = data.get('x_labels')
    y_values = data.get('y_values')

    x_ticks = list(range(len(x_labels)))

    plt.bar(x_labels, y_values)

    plt.xticks(ticks=x_ticks, labels=x_labels)
    plt.xlabel(XLabel)
    plt.ylabel(YLabel)
    plt.title(title)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(full_path)
    plt.close()




async def send_request(session: ClientSession, **kw):
    url = kw.get('url', None)
    _json = kw.get('json', None)

    if None in (url, _json):
        return None
    
    start_time = time.perf_counter()

    async with session.post(url=url, json=_json) as resp:
        resp: ClientResponse
        try:
            response: dict = await resp.json()
            print(response)
            return Result( 
                status_code="OK",
                responese_time=time.perf_counter() - start_time,
                handle_worker=response.get('selected_worker_id'),
            )

        except Exception as e:
            print(f"Error: {str(e)}")
            return {
                "error": str(e)
            }
    
def generate_request_id():
    return f"{int(time.time() * 1000)}_{uuid.uuid4().hex}"


async def main(loop, folder_name: Path):
    url = 'http://192.168.0.100:8199'
    batches = [ i for i in range(1, 30)]

    all_results = []

    dir_path = folder_name / f'{loop}_results'

    for nr in batches:
        async with ClientSession(connector=TCPConnector(limit=0), timeout=ClientTimeout(None)) as session:
            # one batch
            batch_tasks = []

            batch_tasks = [
                asyncio.create_task(send_request(session, url=url, json={
                    "number": 50000,
                    "request_id": generate_request_id(),
                    "algo_name": "proposed"
                }))
                for _ in range(nr)
            ]

            await asyncio.sleep(2)

            results = await asyncio.gather(*batch_tasks)

            batch_dispatch_data = {}

            for result in results:
                if isinstance(result, Result):
                    handle_worker = result.to_dict().get('handle_worker', None)
                    if handle_worker not in batch_dispatch_data:
                        batch_dispatch_data[handle_worker] = 1
                    else:
                        batch_dispatch_data[handle_worker] += 1
                else:
                    print(result.get('error'))

            parsed_result = {
                "request_sum": nr,
                "avg_response_time": float(np.mean(np.array([result.to_dict().get('responese_time', 0) for result in results]))),
                "handle_worker": batch_dispatch_data
            }
            
            all_results.append(parsed_result)

    write_json_file(filepath=dir_path, filename=f'{len(batches)}_results', mode='a', data=all_results)

    # draw 
    parsed_all_results = {}

    for result in all_results:
        parsed_all_results.update({
            result['request_sum']: result['avg_response_time']
        })

    draw_plot(filepath=dir_path, filename=f"comparison_{len(batches)}", data=parsed_all_results, title='The relationship between the number of requests and response time in a single batch', XLabel="N requests", YLabel="Avg resposne time (secondes)")
    
    dispatches_data = {}

    for result in all_results:
        for worker_id, requests in result.get('handle_worker').items():
            if worker_id not in dispatches_data.keys():
                dispatches_data[worker_id] = requests
            else:
                dispatches_data[worker_id] += requests

    print(dispatches_data)

    # draw_bar(filepath=dir_path, filename=f'dispathes_{len(batches)}', data={
    #             "x_labels": list(dispatches_data.keys()),
    #             "y_values": list(dispatches_data.values()),
    #         }, 
    #         title='The number of historical tasks assigned to each node', XLabel='Worker', YLabel='Number of requests')

    # write_json_file(filepath=dir_path, filename=f'{len(batches)}_dispatched', mode='w', data=dispatches_data)
    return dispatches_data

async def run_main():
    loop = 30
    folder_name = WORK_DIR / 'results' / datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    all_dispatched_data = {}
    for l in range(1, loop+1):
        dispatched_data = await main(l, folder_name)
        if all_dispatched_data == {}:
            all_dispatched_data = dispatched_data
        else:
            for worker_id, requests in dispatched_data.items():
                all_dispatched_data[worker_id] += requests

    draw_bar(filepath=folder_name, filename=f'all_dispathed_data', data={
                "x_labels": list(all_dispatched_data.keys()),
                "y_values": list(all_dispatched_data.values()),
            }, 
            title='The number of historical tasks assigned to each node', XLabel='Worker', YLabel='Number of requests')



if __name__ == "__main__":
    asyncio.run(run_main())