from aiohttp import ClientSession, ClientTimeout, TCPConnector
import asyncio
import json
from pathlib import Path
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from time import perf_counter, sleep
import numpy as np
import uuid

algo_names = ['round-robin', 'proposed', 'least-connections']
request_start_time_table = {}
async_longest_response_time = {key: {} for key in algo_names}
worker_to_manager_response_time_acc = {key: {} for key in algo_names}
sum_of_manager_response_time = {key: {} for key in algo_names}
send_interval = 0.01

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
    # request_number = random.randint(a=config.get("request_num_range")[0], b=config.get('request_num_range')[1])
    request_id = config.get("request_id")
    url = config.get("url")
    session: ClientSession = config.get('session')
    # request_count = config.get('request_count')
    # request_sum = config.get('request_sum')
    # request_start_time = config.get("request_start_time", perf_counter())
    shared_progress: dict = config.get('shared_progress')
    algo_name = config.get('algo_name')

    request_start_time = perf_counter()
    request_start_time_table[request_id] = request_start_time

    async with session.post(url=url, json={"algo_name": algo_name, "request_id": request_id, "number": request_number, "request_start_time": request_start_time}) as response:
        response_data: dict = await response.json()
        # request_count += 1
        shared_progress['completed'] += 1
        

        """ send from same time and longest response time """
        async_response_time = perf_counter() - request_start_time_table[request_id]

        # response_data['request_number'] = request_number
        # response_data['request_id'] = request_id
        
        # print(response_data)
        # response_time = perf_counter() - response_time_table[response_data['request_id']]
        # response_data['response_time'] = response_time
    
        try:
            worker_id = response_data['selected_backend_id']
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
            sum_of_manager_response_time[algo_name][worker_id] = response_data.get('no_waiting_response_time')
        else:
            if worker_id not in sum_of_manager_response_time[algo_name]:
                sum_of_manager_response_time[algo_name][worker_id] = response_data.get('no_waiting_response_time')
            else:
                sum_of_manager_response_time[algo_name][worker_id] += response_data.get('no_waiting_response_time')

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


def write_response_json_file(filename: Path, data):
    filename = filename / "responses"
    if not filename.exists():
        filename.mkdir(parents=True, exist_ok=True)

    filename = filename / program_config.get("response_filename")

    with open(filename, 'w') as json_file:
        json.dump(data, json_file)



def draw_plot(filename: Path, data: dict, title: str):
    filename = filename / "figs"
    if not filename.exists():
        filename.mkdir(parents=True, exist_ok=True)

    filename = filename / program_config.get("figs_filename")

    plt.figure(figsize=(16, 9))
    
    for y_key, y in data.items():
        plt.plot(range(len(y)), y, marker="o", label=y_key)

    plt.title(title)
    plt.xlabel("Index")
    plt.ylabel("Seconds")
    plt.xticks(rotation=45)  # 日期标签旋转
    plt.grid(True)


    # 添加图例
    plt.legend()

    # 调整布局并显示图表
    plt.tight_layout()
    plt.savefig(str(filename))


def draw_bar(filename: Path, data: dict, title: str):
    filename = filename / 'figs'
    if not filename.exists():
        filename.mkdir(parents=True, exist_ok=True)

    filename = filename / program_config.get("figs_filename")

    plt.figure(figsize=(16, 9))
    
    for y_key, y in data.items():
        plt.bar(y_key, y, label=y_key)

    plt.title(title)
    plt.xlabel("total response time")
    plt.ylabel("algorithm name")
    plt.grid(True)


    # 添加图例
    plt.legend()

    # 调整布局并显示图表
    plt.tight_layout()
    plt.savefig(str(filename))
    plt.close()


async def main(**program_config):
    request_sum = program_config.get('request_sum', 0)
    request_num_range: tuple = program_config.get('request_num_range', 0)
    request_poisson_list = [ int(np.random.poisson(lam=200000)) if num % 3 != 0 else int(np.random.poisson(lam=500000)) for num in range(request_sum) ] 
    send_interval = program_config.get('send_interval', 0.01)
    request_count = program_config.get('request_count', 0)
    url = program_config.get("url")
    filename = program_config.get("filename")
    shared_progress = program_config.get('shared_progress')
    algo_name = program_config.get('algo_name', None)

    updater_task = asyncio.create_task(process_updater(request_sum, shared_progress, interval=0.5))

    tasks = []

    write_config_json_file(filename, program_config)

    session = ClientSession(timeout=ClientTimeout(None), connector=TCPConnector(limit=0))

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
        
        # print(f"Send task {request_index}")
        await asyncio.sleep(send_interval)

    results: list[dict[str, float]] = await asyncio.gather(*tasks, return_exceptions=True)


    # results = []
    # for task in asyncio.as_completed(tasks):
    #     try:
    #         result = await task
    #         results.append(result)
    #     except:
    #         print(traceback.format_exc())
    #         continue

    await updater_task

    # # Prepare the response data
    # responses = {
    #     # "request_id": [result.get('request_id') for result in results],
    #     # "request_number": [float(result.get('request_number') / 100000) for result in results],
        
    #     # "predicted_processing_time": [result.get("predicted_processing_time") for result in results],
    #     "real_processing_time": [result.get("real_process_time") for result in results],
        
    #     # "predicted_response_time": [float(result.get("predicted_processing_time") + result.get("predicted_waiting_time")) for result in results],
    #     "predicted_waiting_time": [result.get("predicted_waiting_time") for result in results],

    #     "response_time": [result.get("response_time") for result in results],

    #     # "manager_response_time": [result.get("manager_response_time") for result in results],

    #     "waiting_jobs": [result.get("waiting_jobs") for result in results],
    #     "real_waiting_time": [result.get("waiting_time") for result in results],

    #     # "user_cpu_time": [result.get("user_cpu_time") for result in results],
    #     # "system_cpu_time": [result.get("system_cpu_time") for result in results],
    #     # "cpu_spent_usage": [result.get('cpu_spent_usage') for result in results]
    # }

    # # Write response JSON file
    # write_response_json_file(filename, responses)

    # # Prepare the trend data for plotting
    # trend = {
    #     # "request_id": [result.get('request_id') for result in results],
    #     # "request_number": [float(result.get('request_number') / 100000) for result in results],
        
    #     # "predicted_processing_time": [result.get("predicted_processing_time") for result in results],
    #     # "real_processing_time": [result.get("real_process_time") for result in results],
        
    #     # "predicted_response_time": [float(result.get("predicted_processing_time") + result.get("predicted_waiting_time")) for result in results],
    #     "predicted_waiting_time": [result.get("predicted_waiting_time") for result in results],

    #     # "response_time": [result.get("response_time") for result in results],

    #     # "manager_response_time": [result.get("manager_response_time") for result in results],

    #     # "waiting_jobs": [result.get("waiting_jobs") for result in results],
    #     "real_waiting_time": [result.get("waiting_time") for result in results],

    #     # "user_cpu_time": [result.get("user_cpu_time") for result in results],
    #     # "system_cpu_time": [result.get("system_cpu_time") for result in results],
    #     # "cpu_spent_usage": [result.get('cpu_spent_usage') for result in results]
    # }
    
    # title = "Predicted waiting time and real waiting time difference"
    # # Draw the trend comparison chart
    # draw_plot(filename, trend, title)

    await session.close()


    return results
    

if __name__ == "__main__":
    PARENT_DIR = Path(__file__).parent.parent
    loops = 3
    single_loop_task = 10

    algo_total_response_time_table = {} 

    for loop in range(1, loops + 1):
        time_temp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")
        program_config = {
                "request_sum": loop * single_loop_task,
                "request_num_range": (0, 500000),
                "url": "http://192.168.0.100:8199",
                "response_filename": "response.json",
                "figs_filename": "error.png",
                "config_filename": "config.json",
                "shared_progress": {"completed": 0},
                "filename": PARENT_DIR / "poisson_request_number" / "total_response_time_v1_5_5" / time_temp,
                "send_interval": send_interval,
            }

        print("New loop start")

        for algo_name in algo_names:
            algo_total_response_time_start = perf_counter()

            program_config["algo_name"] = algo_name
            program_config["request_count"] = 0
            program_config['shared_progress'] = {"completed": 0}


            results = asyncio.run(main(**program_config))
            
            
            algo_total_response_time = perf_counter() - algo_total_response_time_start
            algo_total_response_time_table[algo_name] = algo_total_response_time

            sleep(1)

            print(f"\n[{algo_name}] All total response time: {algo_total_response_time}\n Single response time acc: {async_longest_response_time[algo_name]}s \n")

            # save result into config.json
            result_info = {
                "total_response_time": algo_total_response_time,
                "single_response_time_acc": async_longest_response_time[algo_name],
                "sum_of_manager_response_time": sum_of_manager_response_time[algo_name]
            }

            if "results" not in program_config:
                program_config["results"] = {}
            program_config["results"][algo_name] = result_info
            write_config_json_file(program_config["filename"], program_config)

            print(f"Task count per worker: {len(results)} \n\n\n")

            # 清理历史
            request_start_time_table.clear()
        
        # 清理历史
        for algo in algo_names:
            async_longest_response_time[algo].clear()
            sum_of_manager_response_time[algo].clear()


        draw_bar(filename=program_config['filename'], data=algo_total_response_time_table, title=f"{len(algo_names)} total response difference")
        # 清理历史
        algo_total_response_time_table.clear()
        

        