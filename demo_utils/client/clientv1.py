# test client
import requests
import concurrent.futures
import time
import typing
import random
from openpyxl import Workbook


def to_excel(data):
    workbook = Workbook()
    sheet = workbook.active

    # | runtime | request-number | response-ip   | 192.168.0.150 | 192.168.0.151 | 192.168.0.152 |
    # | 0.3     | 10000          | 192.168.0.150 | 14.523432     | 14.523432     | 14.523432     | %
    # | 0.5     | 20000          | 192.168.0.151 | 9.5232642     | 14.523432     | 14.523432     | %

    sheet.append(['runtime', 'request-number', 'response-ip', '192.168.0.150', '192.168.0.151', '192.168.0.152'])

    for row in data:
        sheet.append(row)

    workbook.save(filename="excel/output1.xlsx")


def send(n):
    try:
        host = "192.168.0.100"
        port = 8081
        
        headers = {'task-type': "C"}
        data = {"number": n}
        

        start = time.time()
        response = requests.post(url=f"http://{host}:{port}", headers=headers, json=data).json()

        return {
            'request-number': n,
            "response": response,
            "run-time": time.time() - start,
        }

    except Exception as e:
        print(e)


def process():
    print("Request process start.")
    recv_sum = 0
    results = list()
    requests_sum = 10

    with concurrent.futures.ProcessPoolExecutor() as e:
        futures:typing.List[concurrent.futures.Future] = []
        for _ in range(requests_sum):
            futures.append(e.submit(send, random.randint(2000, 10000)))
            time.sleep(2)

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            recv_sum += 1

    print("Request process closed.")

    print("Sended:",  requests_sum)
    print("Received:", recv_sum)

    return results

if __name__ == "__main__":
    # process()
    print("Running...")
    results = process()

    # | runtime | request-number | response-ip   | 192.168.0.150 | 192.168.0.151 | 192.168.0.152 |
    # | 0.3     | 10000          | 192.168.0.150 | 14.523432     | 14.523432     | 14.523432     | %
    # | 0.5     | 20000          | 192.168.0.151 | 9.5232642     | 14.523432     | 14.523432     | %

    datatable = list()

    for result in results:
        datatable.append(
            [
                result["run-time"],
                result["request-number"],
                result["response"]["ip"],
                result["response"]["usages"]["192.168.0.150"],
                result["response"]["usages"]["192.168.0.151"],
                result["response"]["usages"]["192.168.0.152"],
            ]
        )

    to_excel(datatable)

    print("Cover finished!")
