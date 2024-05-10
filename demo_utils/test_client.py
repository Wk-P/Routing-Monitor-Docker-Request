# test client
import requests
import concurrent.futures
import time
import typing
import pandas as pd


def send(n):
    try:
        host = "10.0.2.7"
        port = 8080
        
        headers = {'task_type': "C"}
        data = {"number": n}

        requests.post(url=f"http://{host}:{port}", headers=headers, data=data).json()

    except Exception as e:
        print(e)


def process():
    print("Request process start.")
    recv_result = 0
    with concurrent.futures.ProcessPoolExecutor() as e:
        futures:typing.List[concurrent.futures.Future] = []
        for _ in range(1):
            futures.append(e.submit(send))
            
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
            recv_result += 1
    
    print(recv_result)

    print("Request process closed.")




if __name__ == "__main__":

    # process()
    print("Running...")
    numbers = [100000, 10000000]
    cpu = 0
    data = []
    for num in numbers:
        for _ in range(10):
            start_time = time.time()
            send(num)
            runtime = round(time.time() - start_time, 5)
            data.append({
                "number": num,
                "cpu": cpu, 
                "time": runtime,
            })
        df = pd.DataFrame(data)
    
    df.to_excel("cpu0_output.xlsx", index=False)
