import time
from aiohttp import ClientSession, ClientTimeout, TCPConnector
import asyncio
import json
from pathlib import Path
import sys
from datetime import datetime
from time import perf_counter, sleep
import numpy as np
import uuid
import traceback
from utils.tools import *

algo_names = ['round-robin', 'proposed', 'least-connections']
request_start_time_table = {}
async_longest_response_time = {key: {} for key in algo_names}
worker_to_manager_response_time_acc = {key: {} for key in algo_names}
sum_of_manager_response_time = {key: {} for key in algo_names}
send_interval = 0.02

async def process_updater(total_tasks, shared_progress, interval=0.5):
    while True:
        done = shared_progress['completed']
        percent = 100.0 * done / total_tasks
        sys.stdout.write(f"\r => Completed {percent:.2f} %                ")
        sys.stdout.flush()
        if done >= total_tasks:
            break
        await asyncio.sleep(interval)


async def send_request(**config):
    request_number = config.get('request_number')
    request_id = config.get("request_id")
    url = config.get("url")
    session: ClientSession = config.get('session')
    shared_progress: dict = config.get('shared_progress')
    algo_name = config.get('algo_name')

    request_start_time = time.time()
    request_start_time_table[request_id] = request_start_time

    async with session.post(url=url, json={"algo_name": algo_name, "request_id": request_id, "number": request_number, "request_start_time": request_start_time}) as response:
        response_data: dict = await response.json()
        shared_progress['completed'] += 1

        try:
            worker_id = response_data['selected_worker_id']
            print(f"Task processed by {worker_id}")
        except Exception as e:
            print(response_data.get('error'))
            print(traceback.format_exc())
            await session.close()
            exit(1)
        
        return response_data

def custom_serializer(obj):
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable.")

def write_config_json_file(filename: Path, data):
    filename = filename / "config"
    if not filename.exists():
        filename.mkdir(parents=True, exist_ok=True)

    filename = filename / program_config.get("config_filename")

    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4, default=custom_serializer)


async def main(**program_config):
    request_sum = program_config.get('request_sum', 0)
    # request_num_range: tuple = program_config.get('request_num_range', 0)
    request_num_list = program_config.get('request_num_list', 0)
    send_interval = program_config.get('send_interval', 0.01)
    request_count = program_config.get('request_count', 0)
    url = program_config.get("url")
    shared_progress = program_config.get('shared_progress')
    algo_name = program_config.get('algo_name', None)

    # updater_task = asyncio.create_task(process_updater(request_sum, shared_progress, interval=0.5))

    tasks = []
    
    
    # !!! DON'T RUN !!!
    # write_config_json_file(Path(program_config.get("file_path_config")) / algo_name, program_config)

    session = ClientSession(timeout=ClientTimeout(None), connector=TCPConnector(limit=0))

    for request_index in range(request_sum):
        request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}"

        tasks.append(asyncio.create_task(
            send_request(session=session, 
                        url=url, 
                        shared_progress=shared_progress, 
                        request_id=request_id, 
                        request_sum=request_sum,
                        request_count=request_count, 
                        algo_name=algo_name,
                        request_number=request_num_list[request_index]
                    )))
        
        # print(f"Send task {request_index}")
        await asyncio.sleep(send_interval)

    results: list[dict[str, float]] = await asyncio.gather(*tasks, return_exceptions=True)
    # await updater_task

    if algo_name == "proposed":
        # # Prepare the trend data for plotting
        trend = {
            "predicted_waiting_time": [result.get("predicted_waiting_time") for result in results],
            "real_waiting_time": [result.get("real_all_waiting_time") for result in results],
        }
        
        title = "Predicted waiting time and real waiting time difference"
        # # Draw the trend comparison chart
        draw_plot(filepath=Path(program_config.get('file_path_config')['waiting_time']['path']) / algo_name, filename=program_config.get('file_path_config')['waiting_time']['filename'], data=trend, title=title)

    await session.close()


    return results
    

if __name__ == "__main__":
    PARENT_DIR = Path(__file__).parent.parent
    loops = 8
    single_loop_task = 10

    algo_total_response_time_table = {} 


    for loop in range(1, loops + 1):
        time_temp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = "[result]_v2.0.0"
        default_path =  PARENT_DIR / "poisson_request_number" / folder_name / time_temp
        request_sum = loop * single_loop_task
        # request_sum = np.random.randint(10, 200)
        request_num_list = [ np.random.randint(0, 500000) for _ in range(request_sum) ]
        program_config = {
                "request_sum": request_sum,
                "request_num_list": request_num_list,
                # "request_num_range": (0, 500000),
                "url": "http://192.168.0.100:8199",
                "response_filename": "response.json",
                "config_filename": "config.json",
                "shared_progress": {"completed": 0},
                "file_path_config": 
                    {
                        "default": {
                            "path": default_path / "default",
                            "filename": "default_graph.png",
                        },
                        "total_response_time": {
                            "path": default_path / "total",
                            "filename": "total.png",
                        },
                        "difference_total_predicted_processing_time_and_total_real_processing_time": {
                            "path": default_path / "diff",
                            "filename": "diff.png"
                        },
                        "waiting_time": {
                            "path": default_path / "waiting_time",
                            "filename": "waiting_time.png"
                        }
                    },
                "send_interval": send_interval,
            }
        if loop == 1:
            program_config['request_sum'] = 3
        print("New loop start")

        for algo_name in algo_names:
            algo_total_response_time_start = perf_counter()

            program_config["algo_name"] = algo_name
            program_config["request_count"] = 0
            program_config['shared_progress'] = {"completed": 0}

            results = asyncio.run(main(**program_config))
            
            # total response time of all requests for single algorithm
            algo_total_response_time = perf_counter() - algo_total_response_time_start
            algo_total_response_time_table[algo_name] = algo_total_response_time

            sleep(1)

            # save result into config.json
            result_info = {
                "total_response_time": algo_total_response_time,
                "single_response_time_acc": async_longest_response_time[algo_name],
                "sum_of_manager_response_time": sum_of_manager_response_time[algo_name]
            }

            if "results" not in program_config:
                program_config["results"] = {}
            program_config["results"][algo_name] = result_info


            # history clear
            request_start_time_table.clear()
        
        # history clear
        for algo in algo_names:
            async_longest_response_time[algo].clear()
            sum_of_manager_response_time[algo].clear()
        
        # history clear
        algo_total_response_time_table.clear()
        

        