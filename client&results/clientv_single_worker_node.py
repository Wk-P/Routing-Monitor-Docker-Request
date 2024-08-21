# test client
import time
import typing
import random
from openpyxl import Workbook  # type: ignore
from openpyxl import load_workbook
import aiohttp
import asyncio
import os
from datetime import datetime
from pathlib import Path

send_cnt = 0
finished_cnt = 0
loops = 50
requests_batch = 200

task_interval = 0.1
batch_interval = 0.03

client_name = __file__.split("\\")[-1].split(".")[0]
all_requests_sum = loops * requests_batch


# 随机生成请求内容开关
is_random_request_number = True


# 单元代码测试开关
is_unit_code_test = False


# 测试响应请求输出开关 （输出到控制台不写入文件）
is_test_response_print = False


# 单一请求设定开关
is_single_request_sum = False


def test():
    # TODO test code
    print(filename)
    pass


# filename = "response_information_v1(150)"
if is_random_request_number:
    filename = f'''RandomRequestNumber{client_name}#loops{loops}#requests_batch{requests_batch}#{datetime.ctime(datetime.now()).replace(' ', '-').replace(':', '-')}'''
else:
    filename = f'''{client_name}#loops{loops}#requests_batch{requests_batch}#{datetime.ctime(datetime.now()).replace(' ', '-').replace(':', '-')}'''


if is_single_request_sum:
    filename = f"#test"

dirpath = Path.cwd() / "excel_prediction_v1"


def to_excel(data, filename, dirpath, headers):
    print(headers)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    file_path = str(dirpath / f"{filename}.xlsx")

    if os.path.exists(file_path):
        # 如果文件存在，加载工作簿和活动工作表
        workbook = load_workbook(file_path)
        sheet = workbook.active

    else:
        # 如果文件不存在，创建新的工作簿和工作表
        workbook = Workbook()
        sheet = workbook.active
        # 写入表头
        sheet.append(headers)

    for row in data:
        sheet.append(row)

    workbook.save(file_path)


async def fetch(session: aiohttp.ClientSession, url, number, delay):
    global finished_cnt
    global requests_batch
    global send_cnt
    global loops

    await asyncio.sleep(delay)

    data = {"number": number}
    headers = {"task-type": "C"}

    send_cnt += 1

    print(f"send timestamp: {time.time()}")
    print(f"Send count: {send_cnt}/{all_requests_sum}")

    start_time = time.time()

    async with session.post(url, json=data, headers=headers) as response:
        data = await response.json()
        data["total_response_time"] = time.time() - start_time
        finished_cnt += 1
        print(f"process information: {finished_cnt}/{all_requests_sum}")
        print(data)
        return data


async def main(args):
    host = "192.168.0.100"
    port = 8081
    url = f"http://{host}:{port}"

    tasks = list()
    responses = list()
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=0),
        timeout=aiohttp.ClientTimeout(total=None),
    ) as session:
        # split
        for i, arg in enumerate(args):
            delay = i * task_interval
            task = asyncio.create_task(fetch(session, url, arg, delay))
            tasks.append(task)
        response = await asyncio.gather(*tasks)
        responses.append(response)

        return responses


async def run():
    # global variable
    global requests_batch
    global filename
    global dirpath
    global finished_cnt
    global is_random_request_number

    for _ in range(loops):
        # funciton
        def result_parse(responses: typing.List[typing.Dict[str, typing.Any]]) -> typing.Tuple[int, typing.Dict[str, typing.Any], typing.List]:
            data_table = list()
            response_keys = list()

            for res in responses:
                if type(res) is dict:
                    response_keys = list(res.keys())
                else:
                    raise Exception("Error")

            try:
                if responses:
                    for response in responses:
                        if response.get("success"):
                            data_table.append(
                                [value for key, value in response.items()]
                            )
                        else:
                            data_table.append(
                                ["-" for _ in range(len(response_keys))])
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
        if is_random_request_number:
            args = [random.randint(0, 500000) for _ in range(requests_batch)]
        else:
            args = [500000 for _ in range(requests_batch)]

        print("---start fetch---")

        responses = await main(args)

        for response in responses:
            for res in response:
                for k, v in res.items():
                    print(f"[{k}]: {v}")

        print("---generate data file---")

        # write into excel file
        for response in responses:
            code, data_table, col_headers = result_parse(response)

            if not is_test_response_print:
                if data_table:
                    to_excel(data_table, filename, dirpath, col_headers)
                else:
                    print("None data_table")

                print(f"Cover finished\nExit code: {code}")
            else:
                print(code)
                print(col_headers)
                print(data_table[-1])


if __name__ == "__main__":
    if is_unit_code_test:
        test()
    else:
        if is_single_request_sum:
            loops = 1
            requests_batch = 2

        asyncio.run(run())
    pass
