import time
import asyncio
import uuid
import numpy as np
import traceback
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from pathlib import Path
from datetime import datetime, timedelta
import json
from utils.tools import draw_plot

algo_name = 'proposed'
max_concurrency = 100
duration_hours = 12
send_interval = 0.02
semaphore = asyncio.Semaphore(max_concurrency)


class Record:
    def __init__(self, **data):
        self.__dict__.update(data)

    def to_dict(self):
        return self.__dict__
    
    def __str__(self):
        return json.dumps(self.__dict__, indent=4)

def custom_serializer(obj):
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable.")

def write_json_auto(filepath: Path, filename: str, data, mode: str = 'w'):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)
    # 自动加编号防止覆盖
    count = sum(1 for file in filepath.iterdir() if file.is_file() and file.suffix == '.json')
    filename = f"{filename}_{count}.json"
    full_path = filepath / filename
    with open(full_path, mode) as json_file:
        json.dump(data, json_file, indent=4, default=custom_serializer)
    return full_path


async def send_request(**config):
    request_number = config.get('request_number')
    request_id = config.get("request_id")
    url = config.get("url")
    session: ClientSession = config.get('session')
    algo_name = config.get('algo_name')

    async with semaphore:
        try:
            async with session.post(url=url, json={"algo_name": algo_name, "request_id": request_id, "number": request_number}) as response:
                response_data: dict = await response.json()
                print(response_data)
                return Record(
                    request_number=request_number,
                    selected_worker_id=response_data['selected_worker_id'],
                    contention_time=response_data['contention_time'],
                    real_all_waiting_time=response_data['real_all_waiting_time'],
                    predicted_waiting_time=response_data['predicted_waiting_time'],
                    real_process_time=response_data['real_process_time'],
                    cpu_spent_usage=response_data['cpu_spent_usage']
                )
        except Exception as e:
            print(f"[Error] Request failed: {traceback.format_exc()}")
            return Record(error=str(e), traceback=traceback.format_exc(), request_number=request_number)


async def main_batch(**program_config):
    request_sum = program_config.get('request_sum')
    request_num_list = program_config.get('request_num_list')
    url = program_config.get("url")
    algo_name = program_config.get('algo_name')
    send_interval = program_config.get('send_interval', 0.01)

    tasks = []
    session = ClientSession(timeout=ClientTimeout(None), connector=TCPConnector(limit=0))

    for request_index in range(request_sum):
        request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}"

        tasks.append(asyncio.create_task(
            send_request(session=session, 
                        url=url, 
                        request_id=request_id, 
                        request_sum=request_sum, 
                        algo_name=algo_name,
                        request_number=request_num_list[request_index]
                        )))
        
        await asyncio.sleep(send_interval)

    # same order of send request
    results: list[dict[str, float]] = await asyncio.gather(*tasks, return_exceptions=True)

    await session.close()
    return results


async def main():
    PARENT_DIR = Path(__file__).parent.parent
    start_time = datetime.now()
    total_duration = timedelta(minutes=10)      
    record_interval = timedelta(minutes=2) 
    
    next_record_time = start_time + record_interval
    end_time = start_time + total_duration
    
    timestamp: str = start_time.strftime("%Y%m%d-%H%M%S")
    folder_name = f"{timestamp}_{int(total_duration.total_seconds() // 60)}min_{int(record_interval.total_seconds() // 60)}min-interval_requests"


    last_path = None
    last_parsed_result = None

    print(f"Start simulation from {start_time} to {end_time}")
    
    draw_parsed_result = {}
    

    while datetime.now() < end_time:
        try:
            current_path = PARENT_DIR / folder_name / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            request_sum =  np.random.randint(10, 100)
            request_num_list = [ np.random.randint(0, 500000) for _ in range(request_sum) ]
            
            program_config = {
                "request_sum": request_sum,
                "request_num_list": request_num_list,
                "algo_name": algo_name,
                "url": "http://192.168.0.100:8199",
                "send_interval": send_interval,
            }

            write_json_auto(filepath=current_path, filename='config', data=program_config)

            start_perf = time.perf_counter()
            result_group: list[Record] =  await main_batch(**program_config)
            elapsed = time.perf_counter() - start_perf
            print(f"Batch finished in {elapsed:.2f}s, tasks: {len(result_group)}")        

            parsed_result = {}

            for record in result_group:
                if isinstance(record, Record):
                    for key, value in record.to_dict().items():
                        parsed_result.setdefault(key, []).append(value)
                else:
                    print(f"[Warning] Unexpected result: {record}")

            for key, values in parsed_result.items():
                draw_parsed_result.setdefault(key, []).extend(values)

            time.sleep(np.random.uniform(0, 1))

            if datetime.now() >= next_record_time:
                print(f"\n[Recording] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # draw   
                draw_plot(
                    filepath=current_path,
                    filename="summary.png",
                    data={
                        "predicted_waiting_time": draw_parsed_result.get("predicted_waiting_time", []),
                        "real_waiting_time": draw_parsed_result.get("real_all_waiting_time", [])
                    },
                    title=f"20min Performance Record {datetime.now().strftime('%H:%M')}"
                )

                # record
                write_json_auto(filepath=current_path, filename="record", data=parsed_result)
                next_record_time += record_interval

                # next record time
                next_record_time += record_interval

                # clear
                # draw_parsed_result.clear()


            last_path = current_path
            last_parsed_result = parsed_result

        except Exception as e:
            # 错误单独记录
            error_log_path = PARENT_DIR / folder_name / "error_logs"
            write_json_auto(filepath=error_log_path, filename="error", data={"error": str(e), "traceback": traceback.format_exc()})
            print(f"[ERROR LOGGED] {str(e)}")
    

    write_json_auto(filepath=last_path, filename="record", data=last_parsed_result)
    write_json_auto(filepath=last_path, filename='all_record', data=draw_parsed_result)
    
    print(f"Simulation finished after {total_duration} hours.")


if __name__ == "__main__":
    asyncio.run(main())
    
        

        