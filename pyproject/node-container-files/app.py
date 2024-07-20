import aiohttp
from aiohttp import web
from concurrent.futures import ProcessPoolExecutor
import psutil
import os
import time
import asyncio


# Global process pool
executor = ProcessPoolExecutor()

# jobs counter
jobs_cnt = 0


def get_cpu_times(pid):
    process = psutil.Process(pid)
    cpu_times = process.cpu_times()
    user_times = cpu_times.user
    system_times = cpu_times.system

    return user_times, system_times

def is_prime(num):
    if num <= 1:
        return False
    if num == 2:
        return True
    if num % 2 == 0:
        return False
    for i in range(3, int(num**0.5) + 1, 2):
        if num % i == 0:    
            return False
        
    return True


def prime_count(num):
    start_time = time.time()
    
    # get child pid
    child_pid = os.getpid()
    
    start_user_times, start_system_times = get_cpu_times(child_pid)

    sum = 0
    for i in range(2, num):
        if is_prime(i):
            sum += 1


    # fetch cpu data
    end_user_times, end_system_times = get_cpu_times(child_pid)
    user_times_diff = end_user_times - start_user_times
    system_times_diff = end_user_times - start_system_times

    return {"num": num, "sum": sum, "user": user_times_diff, "system": system_times_diff, "child_pid": child_pid, "start_process_timestamp": start_time, "process_time": time.time() - start_time}


async def handle(request):
    global jobs_cnt
    try:
        # jobs cnt update
        jobs_cnt += 1

        # time record
        arrival_time = time.time()
        
        response_data = None


        headers = request.headers
        data = await request.json()
    
        task_type = headers["task-type"]
        

        # record current number of jobs
        jobs_temp_cnt = jobs_cnt
        jobs_temp_cnt1 = len(asyncio.all_tasks())

        if task_type == "C":
            # future = executor.submit(prime_count, data["number"])
            # response_data = future.result()
            response_data = prime_count(data['number'])
        
        jobs_cnt -= 1

        # test
        print(response_data)
        
        response_data["request_wait_time"] = response_data["start_process_timestamp"] - arrival_time
        response_data["jobs_cnt"] = jobs_temp_cnt1

        return web.json_response(response_data)
    except Exception as e:
        return web.json_response({"error": str(e)})


if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("", handle)
    web.run_app(app, host="0.0.0.0", port=8080)
