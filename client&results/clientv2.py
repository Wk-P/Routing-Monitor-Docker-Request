# test client
import requests
import concurrent.futures
import time
import typing
import random
from openpyxl import Workbook
import sys


recv_sum = 0


def to_excel(data):
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

    filename = "outputv13"

    workbook.save(filename=f"excel2/{filename}.xlsx")


def send(n):
    global recv_sum
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

        print("RESPONSE", response)

        recv_sum += 1

        return {
            "response": response,
            "run-time": time.time() - start,
        }

    except Exception as e:
        print(e)


def send_process():
    global recv_sum
    print("Request process start...")

    results = list()
    requests_numbers = list()

    requests_sum = 100

    try:
        with concurrent.futures.ProcessPoolExecutor() as e:
            futures: typing.List[concurrent.futures.Future] = []
            for _ in range(requests_sum):
                requests_numbers.append(random.randint(0, 10000000))
                futures.append(e.submit(send, requests_numbers[-1]))
                time.sleep(0.2)

            for future in futures:
                results.append(future.result())
                recv_sum += 1
                # Print progress
                print(f"\rProgress: {recv_sum}/{requests_sum} tasks completed.", end='')
                
        print("\nRequest process closed.")

        print("Sended:", requests_sum)
        print("Received:", recv_sum)

        return results, requests_numbers
    except KeyboardInterrupt:
        print("Process Interrupted.")
        sys.exit(1)


if __name__ == "__main__":
    # process()
    print("Running...")
    results, requests_numbers = send_process()

    # | runtime | request-number | response-ip   | 192.168.0.150 | 192.168.0.151 | 192.168.0.152 |
    # | 0.3     | 10000          | 192.168.0.150 | 14.523432     | 14.523432     | 14.523432     | %
    # | 0.5     | 20000          | 192.168.0.151 | 9.5232642     | 14.523432     | 14.523432     | %

    datatable = list()

    print(results)

    # for i in range(len(results)):
    #     result = results[i]
    #     if result:
    #         datatable.append(
    #             [
    #                 result["run-time"],
    #                 requests_numbers[i],
    #                 result["response"]["ip"],
    #                 result["response"]["usages"]["192.168.0.150"],
    #                 result["response"]["usages"]["192.168.0.151"],
    #                 result["response"]["usages"]["192.168.0.152"],
    #             ]
    #         )
    #     else:
    #         datatable.append(
    #             [
    #                 "-",
    #                 requests_numbers[i],
    #                 "-",
    #                 "-",
    #                 "-",
    #                 "-",
    #             ]
    #         )

    # to_excel(datatable)

    # print("Cover finished!")
