# -- run in container --
# DON'T RUN in other enviroment
from aiohttp import web
from concurrent.futures import ProcessPoolExecutor
import psutil  # type: ignore
import os
import time
import traceback

# Global process pool
executor = ProcessPoolExecutor()


# jobs counters
received_cnt = 0
processing_cnt = 0
finished_cnt = 0


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

    global processing_cnt
    processing_cnt += 1

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
    system_times_diff = end_system_times - start_system_times

    processing_cnt -= 1
    return {"request_num": num, "return_result": sum, "user_cpu_time": user_times_diff, "system_cpu_time": system_times_diff, "worker_node_child_pid": child_pid, "worker_node_start_process_timestamp": start_time, "real_process_time": time.time() - start_time}


async def handle(request: web.Request):
    global received_cnt
    global processing_cnt
    global finished_cnt

    def get_disk_usage():
        partitions = psutil.disk_partitions()
        print("Disk Partitions and Usage:")
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
        return {
            "unit": "bytes",
            "total/limit": usage.total,
            "used": usage.used,
            "free": usage.free,
        }

    def get_mem_usage():
        virtual_memory = psutil.virtual_memory()
        return {
            "unit": "bytes",
            "total/limit": virtual_memory.total,
            "used": virtual_memory.used,
            "free": virtual_memory.free
        }

    received_cnt += 1
    # update waiting jobs count
    if received_cnt - processing_cnt - finished_cnt < 0:
        waiting_cnt = 0
    else:
        waiting_cnt = received_cnt - processing_cnt - finished_cnt

    try:
        # time record
        headers = request.headers
        task_type = headers["task-type"]
        response_data = dict()

        # record current number of jobs
        if task_type == "C":
            data = await request.json()
            arrival_time = time.time()
            response_data = {}
            # update finished count
            processing_cnt -= 1
            finished_cnt += 1
            # future = executor.submit(prime_count, data["number"])
            # response_data = future.result()
            response_data = prime_count(data['number'])
            response_data["wait_time_on_worker_node"] = response_data["worker_node_start_process_timestamp"] - arrival_time
            response_data["waiting_queue_length_on_worker_node"] = waiting_cnt
        elif task_type == "PS":
            disk_stats = get_disk_usage()
            mem_stats = get_mem_usage()
            response_data['disk_stats'] = disk_stats
            response_data['mem_stats'] = mem_stats

        return web.json_response(response_data)
    except Exception as e:
        error_message = traceback.format_exc()
        return web.json_response({"error": error_message}, status=500)


if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("", handle)
    web.run_app(app, host="0.0.0.0", port=8080)
