# test client
import glob
import requests
import time
import typing
import random
from openpyxl import Workbook # type: ignore
import sys
import aiohttp
import asyncio
from aiohttp import ClientTimeout
import os

finished_cnt = 0
requests_sum = 150

def to_excel(data, filename, dirpath):

    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active

    # | user-response-time | request-number | response-ip   | process-time  |
    # | 0.3                | 10000          | 192.168.0.150 | 14.523432     |
    # | 0.5                | 20000          | 192.168.0.151 | 9.5232642     |

    sheet.append(
        [
            "user_response_time",
            "request_number",
            "response_ip",
            "process_time",
            "node_wait_time",
            "jobs_cnt",
        ]
    )

    for row in data:
        sheet.append(row)

    workbook.save(filename=f"{dirpath}/{filename}.xlsx")


async def fetch(session: aiohttp.ClientSession, url, number):
    global finished_cnt
    global requests_sum
    data = {"number": number}
    headers = {"task-type": "C"}
    print(data)

    start_time = time.time()

    async with session.post(url, json=data, headers=headers) as response:
        data = await response.json()
        data["user_response_time"] = time.time()  - start_time

        finished_cnt += 1
        print(f'process information: {finished_cnt}/{requests_sum}')
        return data


async def main(args):
    host = "192.168.0.100"
    port = 8081
    url = f"http://{host}:{port}"

    tasks = list()
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=200),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        # split
        tasks = [fetch(session, url, arg) for arg in args]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return responses


async def run():
    global requests_sum
    filename = "nodeWaitQueueTest"
    dirpath = "excel4"
    data_table = list()
    # args = [random.randint(0, 1000000) for _ in range(requests_sum)]
    args = [500000 for _ in range(requests_sum)]

    print("---start fetch---")

    responses = await main(args)

    if responses:
        for response in responses:
            if response.get("success"):
                data_table.append(
                    [
                        response.get("user_response_time"),
                        response.get("num"),
                        response.get("ip"),
                        response.get("process_time"),
                        response.get("request_wait_time"),
                        response.get('waiting_cnt'),
                    ]
                )
            else:
                data_table.append(
                    [response.get("user_response_time"), response.get("num"), "-", "-"]
                )

        to_excel(data_table, filename, dirpath)
        print("Cover finished!")
    else:
        print("Error!")

if __name__ == "__main__":
    asyncio.run(run())
