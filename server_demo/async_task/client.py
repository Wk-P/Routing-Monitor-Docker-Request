# client.py

import asyncio
import traceback
from aiohttp import ClientSession
import random

from numpy import average




MIDDLE_SERVER_URL = 'http://localhost:8000/forward'


diff_times = {}


async def send_request(session: ClientSession, request_id):
    try:
        async with session.post(MIDDLE_SERVER_URL, json={'request_id': request_id, 'process_time': random.randint(3, 10)}) as resp:
            data: dict = await resp.json()
            status = data.get("status", "")
            calculate_wait_time = data.get("pending_time_estimated", 0)
            real_wait_time = data.get("real_wait_time", 0)

            print(
                f"请求 {request_id}: 状态: {status}, 计算等待时间: {calculate_wait_time} 秒，真实等待时间 {real_wait_time} 秒")
            diff_times[request_id] = calculate_wait_time - real_wait_time
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"请求 {request_id} 失败: {err_msg}")


async def main():
    tasks_sum = 500
    tasks = list()
    request_id = 1
    async with ClientSession() as session:
        for _ in range(tasks_sum):
            # while True:
            print(f"请求 {request_id} 发送")
            tasks.append(asyncio.create_task(
                send_request(session, request_id)))
            request_id += 1
            await asyncio.sleep(0.1)  # 每0.4秒发送一个请求

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("客户端停止发送请求。")


    max_diff = 0
    min_diff = 0
    for request_id, diff_time in diff_times.items():
        print(f"请求 {request_id}，计算的 pending time 和真实的 pending time 差距 {diff_time}")

        # 更新最大最小值
        if max_diff < diff_time:
            max_diff = diff_time
        if min_diff >  diff_time:
            min_diff = diff_time

    avg_diff = average(list(diff_times.values()))

    print(f"平均误差 {avg_diff} s")