# client.py

import asyncio
from aiohttp import ClientSession

MIDDLE_SERVER_URL = 'http://localhost:8000/forward'


async def send_request(session: ClientSession, request_id):
    try:
        async with session.post(MIDDLE_SERVER_URL, json={'request_id': request_id}) as resp:
            data: dict = await resp.json()
            status = data.get("status", "")
            calculate_wait_time = data.get("calculate_wait_time", 0)
            real_wait_time = data.get("real_wait_time", 0)

            print(
                f"请求 {request_id}: 状态: {status}, 计算等待时间: {calculate_wait_time} 秒，真实等待时间 {real_wait_time} 秒")
    except Exception as e:
        print(f"请求 {request_id} 失败: {e}")


async def main():
    tasks_sum = 100
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
