# test client
import time
import typing
import random
from openpyxl import Workbook # type: ignore
import aiohttp
import asyncio
import os

send_cnt = 0
finished_cnt = 0
requests_sum = 1200
filename = "response_information_v1(1200)"
dirpath = "excel4"

def to_excel(data, filename, dirpath, headers):

    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active

    # | user-response-time | request-number | response-ip   | process-time  |
    # | 0.3                | 10000          | 192.168.0.150 | 14.523432     |
    # | 0.5                | 20000          | 192.168.0.151 | 9.5232642     |

    sheet.append(
        [ header for header in headers ]
    )

    for row in data:
        sheet.append(row)

    workbook.save(filename=f"{dirpath}/{filename}.xlsx")


async def fetch(session: aiohttp.ClientSession, url, number):
    global finished_cnt
    global requests_sum
    global send_cnt
    data = {"number": number}
    headers = {"task-type": "C"}

    send_cnt += 1

    print(f"Send count: {send_cnt}/{requests_sum}")

    start_time = time.time()

    async with session.post(url, json=data, headers=headers) as response:
        data = await response.json()
        data["total_response_time"] = time.time()  - start_time
        data['trans_delay'] = data['total_response_time'] - data["wait_time_in_worker_node"] - data["process_in_worker_node"]


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
    # global variable
    global requests_sum
    global filename
    global dirpath
    

    # funciton
    def result_parse(responses: typing.List[typing.Dict[str, typing.Any]]) -> typing.Tuple[int, typing.Dict[str, typing.Any], typing.List]:
        data_table = list()
        response_keys = list()

        for res in responses:
            if res:
                response_keys = list(res.keys())

        try:
            if responses:
                for response in responses:
                    if response.get("success"):
                        data_table.append(
                            [value for key, value in response.items()]
                        )
                    else:
                        data_table.append(["-" for _ in range(len(response_keys))])
                print("--EXIT--")
                code = 0
            else:
                code = 1
                data_table = None
        except Exception as e:
            print(e)
            code = -1
            data_table = None
        finally:
            return code, data_table, response_keys
    


    # process
    # args = [random.randint(0, 1000000) for _ in range(requests_sum)]
    args = [500000 for _ in range(requests_sum)]

    print("---start fetch---")

    responses = await main(args)

    print("---generate data file---")

    # write into excel file
    code, data_table, col_headers = result_parse(responses)

    if data_table:
        to_excel(data_table, filename, dirpath, col_headers)
    else:
        print("None data_table")

    print(f"Cover finished\nExit code: {code}")


if __name__ == "__main__":
    asyncio.run(run())
