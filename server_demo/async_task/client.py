import asyncio
import traceback
from aiohttp import ClientSession, ClientTimeout
import random
import matplotlib.pyplot as plt
import sys
from time import sleep
from pathlib import Path

MIDDLE_SERVER_URL = 'http://localhost:8000/forward'

results_set = {}
finish_tasks = 0  # 全局变量

async def send_request(session: ClientSession, request_id, loop, tasks_sum):
    global results_set, finish_tasks
    try:
        process_time = random.randint(1, 5)
        async with session.post(MIDDLE_SERVER_URL, json={'request_id': request_id, 'process_time': process_time}) as resp:
            data: dict = await resp.json()
            results_set[loop].append(data)

            # 更新全局任务计数并打印进度
            finish_tasks += 1
            percent = finish_tasks / tasks_sum * 100
            sys.stdout.write(f'\rProgress: {percent:.2f}% Completed.')
            sys.stdout.flush()
            if finish_tasks == tasks_sum:
                print()  # 完成后换行

    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"请求 {request_id} 失败: {err_msg}")

async def main(tasks_sum, loop):
    global finish_tasks
    finish_tasks = 0  # 每次主任务运行前重置计数
    tasks = []
    request_id = 1
    async with ClientSession(timeout=ClientTimeout(None)) as session:
        for _ in range(tasks_sum):
            tasks.append(asyncio.create_task(
                send_request(session, request_id, loop, tasks_sum)
            ))
            request_id += 1
            await asyncio.sleep(random.randint(1, 10) / 10)  # 模拟异步操作

        await asyncio.gather(*tasks)

def setup(loops):
    global results_set
    for loop in range(loops):
        results_set[loop] = []  # list[dict[str, float]]

def table_make(data_set: dict, filename):
    y = data_set.get('error')

    plt.figure(figsize=(10, 6))
    plt.plot(range(len(y)), y, marker='o', linestyle='-', label='Error')

    plt.title("Error vs Index")
    plt.xlabel("Index")
    plt.ylabel("Error")
    plt.grid(True)
    plt.legend()
    plt.savefig(filename)

if __name__ == '__main__':
    try:
        loops = 20
        setup(loops)

        for loop in range(loops):
            tasks_sum = random.randint(20, 50)
            asyncio.run(main(tasks_sum, loop))

            table_data = [result['error'] for result in results_set[loop]]
            table_make({"error": table_data}, f"{str(Path(__file__).parent / 'figs' / f'{loop}')}.png")

            sleep(2)

    except KeyboardInterrupt:
        print("客户端停止发送请求。")
