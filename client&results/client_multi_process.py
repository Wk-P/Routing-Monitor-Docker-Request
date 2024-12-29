#
# multi-processes
#
import time
import random
import asyncio
import aiohttp
from multiprocessing import Process, Manager
from datetime import datetime
from pathlib import Path

class ClientParams:
    def __init__(self, *args, **kw) -> None:
        self.send_cnt = 0
        self.finished_cnt = 0
        self.loops = kw.get('loops')
        self.group = kw.get('group')
        self.sum_args_min = kw.get("sum_args_min")
        self.sum_args_max = kw.get("sum_args_max")
        self.tasks_batches = kw.get('_sum_requests')
        self.task_interval = kw.get('task_interval')
        self.group_interval = kw.get('group_interval')
        self.loops_interval = kw.get('loops_interval')
        if self.loops < 2:
            self.loops_interval = 0
        
        if self.group_interval < 2:
            self.group_interval = 0

        if self.task_interval < 2:
            self.task_interval = 0

        self.client_name = __file__.split("\\")[-1].split(".")[0]
        self.all_requests_sum = self.loops * self.tasks_batches * self.group

        self.random_int_max = kw.get("random_int_max")
        self.random_int_min = kw.get('random_int_min')

        # random request number switch
        self.is_random_request_number = kw.get("is_random_request_number")

        # unit code test switch
        self.is_unit_code_test = kw.get('is_unit_code_test')

        # response console print withou excel
        self.is_test_response_print = kw.get('is_test_response_print')

        # single request for test
        self.is_single_request_sum = kw.get('is_single_request_sum')

        # request number data from file
        self.is_read_from_file = kw.get('is_read_from_file')


        if self.is_single_request_sum:
            self.loops = 1
            self.tasks_batches = [20]
            self.all_requests_sum = self.loops * self.tasks_batches * self.group
        
        if self.is_read_from_file:
            self._args = read_numbers_from_file()
            self.all_requests_sum = self.tasks_batches

        if self.is_random_request_number:
            self.filename = f'''RAND{self.client_name}-L{self.loops}-G{self.group}-RB{self.tasks_batches}''' + kw.get('filenamekw')
        else:
            self.filename = f'''{self.client_name}-L{self.loops}-G{self.group}-RB{self.tasks_batches}''' + kw.get('filenamekw')

        if self.is_single_request_sum:
            self.filename = f"#test"

        self.dirpath = kw.get('dirpath')

client_params = ClientParams(
    loops = 1,
    group = 1,
    task_interval = 0.3,
    loops_interval = 4,
    group_interval = 5,
    sum_args_min = 1,
    sum_args_max = 500,
    _sum_requests = 400,
    is_random_request_number = False,
    is_unit_code_test = False,
    is_test_response_print = False,
    is_single_request_sum = False,
    is_read_from_file = True,
    dirpath = Path.cwd() / "RR-RSN5",
    random_int_max = 500000,
    random_int_min = 1,
    filenamekw = f'''-DT{datetime.ctime(datetime.now()).replace(' ', '').replace(':', '')}'''
)

def read_numbers_from_file():
    with open('args.txt', 'r') as file:
        args_from_file = [int(line.strip()) for line in file]
        return args_from_file

async def fetch(session: aiohttp.ClientSession, url, number, client_params, shared_list):
    data = {"number": number}
    headers = {"task-type": "C"}

    client_params['send_cnt'] += 1

    print(f"send timestamp: {time.time()}", end='\t')
    print(f"Send count: {client_params['send_cnt']}/{client_params['requests_sum']}, {round(100 * client_params['send_cnt']/client_params['requests_sum'], 2)}%")

    start_time = time.time()
    try:
        async with session.post(url, json=data, headers=headers) as response:
            data = await response.json()
            data["total_response_time"] = time.time() - start_time
            client_params['finished_cnt'] += 1
            shared_list.append(data)  # Add result to shared list
            print(f"{'start timestamp:':<50}{start_time:<20}")
            print(f"{'process timestamp:':<50}{time.time():<20}", end='\t')
            hint_str = f"{client_params['finished_cnt']}/{client_params['requests_sum']}, {round(100 * client_params['finished_cnt']/client_params['requests_sum'], 2)}%"
            print(f"{'process information:':<50}{hint_str:<20}")
    finally:
        response.release()

async def main(args, shared_list, client_params):
    host = "192.168.0.100"
    port = 8081
    url = f"http://{host}:{port}"

    tasks = []

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=0),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        _index = 0
        for arg in args:
            if _index == client_params['group_limit']:
                _index = 0
                await asyncio.sleep(client_params['group_interval'])
            task = asyncio.create_task(fetch(session, url, arg, client_params, shared_list))
            tasks.append(task)
            await asyncio.sleep(client_params['task_interval'])
            _index += 1

        await asyncio.gather(*tasks)

def run_in_process(args, shared_list, client_params):
    asyncio.run(main(args, shared_list, client_params))

def run_multiprocess(client_params, num_processes=4):
    manager = Manager()
    shared_list = manager.list()  # Use Manager list to share data between processes
    processes = []
    requests_per_process = client_params.requests_sum // num_processes

    for i in range(num_processes):
        # Generate different args for each process
        args = [random.randint(client_params.random_int_min, client_params.random_int_max) for _ in range(requests_per_process)]
        process_params = {
            'send_cnt': 0,
            'finished_cnt': 0,
            'requests_sum': requests_per_process,
            'task_interval': client_params.task_interval,
            'group_limit': client_params.group_limit,
            'group_interval': client_params.group_interval,
        }
        p = Process(target=run_in_process, args=(args, shared_list, process_params))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    # Print shared list of results from all processes
    print("Results:", list(shared_list))


if __name__ == "__main__":
    run_multiprocess(client_params, num_processes=4)
