from aiohttp import web
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil  # type: ignore
import os
import time
import traceback
import asyncio

# Global process pool
thread_executor = ThreadPoolExecutor(max_workers=1)
process_executor = ProcessPoolExecutor(max_workers=1)

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
    system_times_diff = end_system_times - start_system_times

    return {"request_num": num, "return_result": sum, "user_cpu_time": user_times_diff, "system_cpu_time": system_times_diff, "real_process_time": time.time() - start_time, "start_process_time": start_time, "finish_time": time.time()}


async def handle(request: web.Request):
    data = await request.json()

    try:
        # Run the blocking task
        loop = asyncio.get_event_loop()
        response_data = await loop.run_in_executor(thread_executor, prime_count, data["number"])
        # response_data = await loop.run_in_executor(process_executor, prime_count, data["number"])

        return web.json_response(response_data, status=200)
    except Exception as e:
        error_message = traceback.format_exc()
        return web.json_response({"error": error_message}, status=500)

async def main():
    global lock
    lock = asyncio.Lock()

    app = web.Application()
    app.router.add_post("", handle)

    # Run the web application
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    # Keep the application running
    while True:
        # Adjust as needed for your application's lifecycle
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())

