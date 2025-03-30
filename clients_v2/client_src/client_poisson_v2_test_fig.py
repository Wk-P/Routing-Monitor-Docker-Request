import time
from aiohttp import ClientSession, ClientTimeout, TCPConnector, ContentTypeError
import asyncio
import json
from pathlib import Path
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from time import perf_counter, sleep
import numpy as np
import uuid
import typing

from clients_v2.client_src.utils.tools import draw

# algo_names = ['round-robin', 'proposed', 'least-connections']
algo_names = ['round-robin']
request_start_time_table = {}
async_longest_response_time = {key: {} for key in algo_names}
worker_to_manager_response_time_acc = {key: {} for key in algo_names}
sum_of_manager_response_time = {key: {} for key in algo_names}
send_interval = 0.01

DATA_PATH = Path(__file__).parent / 'data'
FIG_PATH = Path(__file__).parent / 'temp_figs'

def stdout_results(results: typing.List[typing.Dict[typing.AnyStr, typing.Any]]):
    for result in results:
        print("== RESULT ==")
        for key, value in result.items():
            print(f"{key}: {value}")
        print('\n')


def write_into_json(results: typing.List[typing.Dict[typing.AnyStr, typing.Any]]):
    process_time_table: typing.Dict[int, float] = {}
    for result in results:
        process_time_table[result.get('request_number')] = result.get('real_process_time')

    try:
        with open(DATA_PATH / 'data.json', 'r') as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {}

    existing_data.update(process_time_table)

    with open(DATA_PATH / 'data.json', 'w') as f:
        json.dump(existing_data, f, indent=4)

def parse_results(results: typing.List[typing.Dict[typing.AnyStr, typing.Any]]):
    global FIG_PATH
    x_labels = [key for key in results[0].keys() if key not in ('selected_worker_id', 'request_number', 'result', 'cpu_spent_usage', 'contention_time', 'system_cpu_time', 'request_id')]
    data_for_plot = []
    save_path = FIG_PATH
    
    for field in x_labels:
        try:
            values = [float(r[field]) for r in results]
            data_for_plot.append({
                'label': field,
                'values': values
            })
        except (ValueError, TypeError):
            continue  

    x_ticks = [r['request_number'] for r in results]

    draw(
        x_labels=x_ticks,
        data=data_for_plot,
        save_path=save_path,
    )

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
        try:
            response_data: dict = await response.json()
            response_receive_time = time.time()
            # request_count += 1
            shared_progress['completed'] += 1
            
            # print(response_data)

            """ send from same time and longest response time """
            async_response_time = time.time() - request_start_time_table[request_id]

            # response_data['request_number'] = request_number
            # response_data['request_id'] = request_id
            
            # print(response_data)
            # response_time = perf_counter() - response_time_table[response_data['request_id']]
            # response_data['response_time'] = response_time
        
            try:
                worker_id = response_data['selected_worker_id']
            except:
                print(response_data.get('error'))
                # print(traceback.format_exc())
                await session.close()
                exit(1)


            """ version 0.0.1 (not single response time sum) """
            if algo_name not in async_longest_response_time:
                async_longest_response_time[algo_name] = {}
                async_longest_response_time[algo_name][worker_id] = async_response_time
            else:
                if worker_id not in async_longest_response_time[algo_name]:
                    async_longest_response_time[algo_name][worker_id] = async_response_time
                else:
                    async_longest_response_time[algo_name][worker_id] = async_response_time


            """ version 0.0.2 (sum of manager response time) """
            if algo_name not in async_longest_response_time:
                sum_of_manager_response_time[algo_name] = {}
                sum_of_manager_response_time[algo_name][worker_id] = response_data.get('predicted_processing_time')
            else:
                if worker_id not in sum_of_manager_response_time[algo_name]:
                    sum_of_manager_response_time[algo_name][worker_id] = response_data.get('predicted_processing_time')
                else:
                    sum_of_manager_response_time[algo_name][worker_id] += response_data.get('predicted_processing_time')
            
            return response_data
        except ContentTypeError as e:
            print(f"⚠️ ContentTypeError: {e}")
            results.append({'error': 'ContentTypeError', 'message': str(e)})


async def main(**program_config):
    request_sum = program_config.get('request_sum', 0)
    request_num_range: tuple = program_config.get('request_num_range', 0)
    request_poisson_list = program_config.get('request_poisson_list')
    
    # temp [test]
    # temp_list = [ n for n in range(request_num_range[0], request_num_range[1], 50000)]
    # temp_list = [ int(np.random.randint(request_num_range[0], request_num_range[1])) for _ in range(request_sum)]
    # request_poisson_list = temp_list
    # request_sum = len(temp_list)


    send_interval = program_config.get('send_interval', 0.01)
    request_count = program_config.get('request_count', 0)
    url = program_config.get("url")
    filename: dict = program_config.get("filename")
    shared_progress = program_config.get('shared_progress')
    algo_name = program_config.get('algo_name', None)

    updater_task = asyncio.create_task(process_updater(request_sum, shared_progress, interval=0.5))

    tasks = []


    session = ClientSession(timeout=ClientTimeout(None), connector=TCPConnector(limit=50))

    for request_index in range(request_sum):
        request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}"

        tasks.append(asyncio.create_task(
            send_request(session=session, 
                        url=url, 
                        shared_progress=shared_progress, 
                        request_num_range=request_num_range, 
                        request_id=request_id, 
                        request_sum=request_sum, 
                        request_count=request_count, 
                        algo_name=algo_name,
                        request_number=request_poisson_list[request_index]
                        )))
        
        await asyncio.sleep(send_interval)

    results: list[dict[str, float]] = await asyncio.gather(*tasks, return_exceptions=True)

    # stdout_results(results)
    parse_results(results)
    # write_into_json(results)

    await updater_task

    await session.close()

    return results
    

if __name__ == "__main__":
    PARENT_DIR = Path(__file__).parent.parent
    loops = 1
    single_loop_task = 10

    algo_total_response_time_table = {}


    for loop in range(1, loops + 1):
        time_temp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
        folder_name = "222[test]"
        default_path =  PARENT_DIR / "poisson_request_number" / folder_name / time_temp
        request_sum = loop * single_loop_task
        program_config = {
                "request_sum": request_sum,
                "request_num_range": (0, 500000),
                "url": "http://192.168.0.100:8199",
                "response_filename": "response.json",
                "figs_filename": "error.png",
                "config_filename": "config.json",
                "shared_progress": {"completed": 0},
                "filename": 
                    {
                        "default": default_path,
                        "total_response_time": default_path / "total",
                        "difference_total_predicted_processing_time_and_total_real_processing_time":  default_path / "diff",
                    },
                "send_interval": send_interval,
                "request_poisson_list": [ int(np.random.poisson(lam=200000)) if num % 3 != 0 else int(np.random.poisson(lam=500000)) for num in range(request_sum) ] 
            }

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


            print(f"Task count per worker: {len(results)} \n\n\n")
            print(program_config)