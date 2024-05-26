# test client
import requests
import concurrent.futures
import typing
import time

def query_prometheus(query: str):
    prometheus_url = "http://192.168.0.100:9090/api/v1/query"

    params = {'query': query}

    response = requests.get(prometheus_url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data['data']['result']
    else:
        print("Error: Unable to fetch data from Prometheus")
        return None



def send(n):
    try:
        host = "10.0.2.9"
        port = 8081

        headers = {"task_type": "C"}
        data = {"number": n}

        start = time.time()
        response = requests.post(
            url=f"http://{host}:{port}", headers=headers, data=data
        ).json()

        return {
            "response": response,
            "run-time": time.time() - start,
        }

    except Exception as e:
        print(e)


def process():
    print("Request process start.")
    recv_result = 0
    with concurrent.futures.ProcessPoolExecutor() as e:
        futures: typing.List[concurrent.futures.Future] = []
        for _ in range(20):
            futures.append(e.submit(send, 10000000))
            time.sleep(1)

        for future in concurrent.futures.as_completed(futures):
            print(future.result())
            recv_result += 1

    print(recv_result)

    print("Request process closed.")


if __name__ == "__main__":

    # process()
    print("Running...")

    process()
