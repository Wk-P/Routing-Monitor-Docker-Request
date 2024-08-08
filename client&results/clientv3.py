# test client
import requests
import concurrent.futures
import time
import typing
import random
from openpyxl import Workbook
import sys


recv_sum = 0


def to_excel(data, filename):
    workbook = Workbook()
    sheet = workbook.active

    # | runtime | request-number | response-ip   | 192.168.0.150 | 192.168.0.151 | 192.168.0.152 |
    # | 0.3     | 10000          | 192.168.0.150 | 14.523432     | 14.523432     | 14.523432     | %
    # | 0.5     | 20000          | 192.168.0.151 | 9.5232642     | 14.523432     | 14.523432     | %

    sheet.append(
        [
            "runtime",
            "request-number",
            "response-ip",
            "192.168.0.150",
            "192.168.0.151",
            "192.168.0.152",
        ]
    )

    for row in data:
        sheet.append(row)

    workbook.save(filename=f"excel2/{filename}.xlsx")


def send(n):
    try:
        host = "192.168.0.100"
        port = 8081

        headers = {"task-type": "C"}
        data = {"number": n}

        print(data)

        start = time.time()
        response = requests.post(
            url=f"http://{host}:{port}", headers=headers, json=data
        ).json()

        return {
            "data": response,
            "run-time": time.time() - start,
        }

    except Exception as e:
        print(e)


def send_process(requests_sum):
    print("Request process start...")

    args = [random.randint(0, 999999) for _ in range(requests_sum)]
    results = list()
    futures = list()
    try:
        with concurrent.futures.ProcessPoolExecutor() as e:
            for arg in args:
                future = e.submit(send, arg)
                futures.append(future)
                time.sleep(5)

            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        return results
    except KeyboardInterrupt:
        print("Process Interrupted.")
        sys.exit(1)


if __name__ == "__main__":

    filename = "outputv2_5_wait_5s_3(300)"
    sum_tasks = 300

    # process()
    print("Running...")
    results = send_process(sum_tasks)

    # | runtime | request-number | response-ip   | 192.168.0.150 | 192.168.0.151 | 192.168.0.152 |
    # | 0.3     | 10000          | 192.168.0.150 | 14.523432     | 14.523432     | 14.523432     | %
    # | 0.5     | 20000          | 192.168.0.151 | 9.5232642     | 14.523432     | 14.523432     | %

    datatable = list()

    for result in results:
        data: dict = result.get("data")
        if data.get('response').get('success'):
            run_time: float = round(result.get("run-time"), 4)
            ip = data.get("ip")
            request_number = float(data.get('response').get('result').get('num'))
            # request_result = float(data.get("response").get('result').get("sum"))
            # total_cpu_times = response.get('result').get('user') + response.get('result').get('system')
            u1 = round(data.get("usages").get("192.168.0.150"), 4)
            u2 = round(data.get("usages").get("192.168.0.151"), 4)
            u3 = round(data.get("usages").get("192.168.0.152"), 4)

            datatable.append([run_time, request_number, ip, u1, u2, u3])

        else:
            datatable.append(['-', request_number, '-', '-', '-', '-'])

    to_excel(datatable, filename)
    print("Cover finished!")
