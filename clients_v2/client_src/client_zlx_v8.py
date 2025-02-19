from aiohttp import ClientSession, ClientTimeout, TCPConnector
import asyncio
import random
import json
from pathlib import Path
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import traceback
from time import perf_counter, sleep, time

response_time_table = {}


async def process_updater(total_tasks, shared_progress, interval=0.5):
    while True:
        done = shared_progress['completed']
        percent = 100.0 * done / total_tasks
        sys.stdout.write(f"\r => Completed {percent:.2f} %                ")
        sys.stdout.flush()
        if done >= total_tasks:
            break
        await asyncio.sleep(interval)
    
    print()

async def send_request(**config):
    request_number = random.randint(a=config.get("request_num_range")[0], b=config.get('request_num_range')[1])
    request_id = config.get("request_id")
    url = config.get("url")
    session: ClientSession = config.get('session')
    # request_count = config.get('request_count')
    # request_sum = config.get('request_sum')
    shared_progress: dict = config.get('shared_progress')
    request_start_time = config.get("request_start_time", perf_counter())

    response_time_table[request_id] = request_start_time

    async with session.post(url=url, json={"request_id": request_id,"number": request_number, "request_start_time": request_start_time}) as response:
        response_data: dict = await response.json()
        # request_count += 1
        shared_progress['completed'] += 1

    # response_data['request_number'] = request_number
    # response_data['request_id'] = request_id
    
    print(response_data)

    response_time = perf_counter() - response_time_table[response_data['request_id']]

    response_data['response_time'] = response_time

    print(response_data)
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



def draw(filename: Path, data: dict, title: str):
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


async def main(**program_config):
    request_sum = program_config.get('request_sum', 0)
    request_num_range: tuple = program_config.get('request_num_range', 0)
    request_count = program_config.get('request_count', 0)
    url = program_config.get("url")
    filename = program_config.get("filename")
    shared_progress = program_config.get('shared_progress')

    updater_task = asyncio.create_task(process_updater(request_sum, shared_progress, interval=0.5))

    tasks = []

    write_config_json_file(filename, program_config)

    session = ClientSession(timeout=ClientTimeout(None), connector=TCPConnector(limit=0))

    for request_index in range(request_sum):
        request_id = request_index + 1
        request_start_time = perf_counter()
        tasks.append(asyncio.create_task(send_request(session=session, url=url, shared_progress=shared_progress, request_num_range=request_num_range, request_id=request_id, request_sum=request_sum, request_count=request_count, request_start_time=request_start_time)))
        
        print(f"Send task {request_index}")
        await asyncio.sleep(0.1)

    # results: list[dict[str, float]] = await asyncio.gather(*tasks)


    results = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            results.append(result)
        except:
            print(traceback.format_exc())
            continue

    await updater_task

    # Prepare the response data
    responses = {
        # "request_id": [result.get('request_id') for result in results],
        # "request_number": [float(result.get('request_number') / 100000) for result in results],
        
        # "predicted_processing_time": [result.get("predicted_processing_time") for result in results],
        "real_processing_time": [result.get("real_process_time") for result in results],
        
        # "predicted_response_time": [float(result.get("predicted_processing_time") + result.get("predicted_waiting_time")) for result in results],
        "predicted_waiting_time": [result.get("predicted_waiting_time") for result in results],

        "response_time": [result.get("response_time") for result in results],

        # "manager_response_time": [result.get("manager_response_time") for result in results],

        "waiting_jobs": [result.get("waiting_jobs") for result in results],
        "real_waiting_time": [result.get("waiting_time") for result in results],

        # "user_cpu_time": [result.get("user_cpu_time") for result in results],
        # "system_cpu_time": [result.get("system_cpu_time") for result in results],
        # "cpu_spent_usage": [result.get('cpu_spent_usage') for result in results]
    }

    # Write response JSON file
    write_response_json_file(filename, responses)

    # Prepare the trend data for plotting
    trend = {
        # "request_id": [result.get('request_id') for result in results],
        # "request_number": [float(result.get('request_number') / 100000) for result in results],
        
        # "predicted_processing_time": [result.get("predicted_processing_time") for result in results],
        # "real_processing_time": [result.get("real_process_time") for result in results],
        
        # "predicted_response_time": [float(result.get("predicted_processing_time") + result.get("predicted_waiting_time")) for result in results],
        "predicted_waiting_time": [result.get("predicted_waiting_time") for result in results],

        # "response_time": [result.get("response_time") for result in results],

        # "manager_response_time": [result.get("manager_response_time") for result in results],

        # "waiting_jobs": [result.get("waiting_jobs") for result in results],
        "real_waiting_time": [result.get("waiting_time") for result in results],

        # "user_cpu_time": [result.get("user_cpu_time") for result in results],
        # "system_cpu_time": [result.get("system_cpu_time") for result in results],
        # "cpu_spent_usage": [result.get('cpu_spent_usage') for result in results]
    }
    
    title = "Predicted waiting time and real waiting time difference"
    # Draw the trend comparison chart
    draw(filename, trend, title)

    await session.close()

if __name__ == "__main__":
    PARENT_DIR = Path(__file__).parent.parent
    for loop in range(1, 5, 1):
        program_config = {
            "request_sum": loop * 20,
            "request_count": 0,
            "request_num_range": (0, 500000),
            "url": "http://192.168.0.100:8199",
            "filename": PARENT_DIR / "client_v4_data" / datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S"),
            "response_filename": "response.json",
            "figs_filename": "error.png",
            "config_filename": "config.json",
            "shared_progress": {"completed": 0}
        }

        asyncio.run(main(**program_config))

        sleep(1)