# test client
import requests
import concurrent.futures
import time
import typing



def send():
    try:
        host = "10.0.2.7"
        port = 8080
        
        headers = {'task_type': "C"}
        data = {"number": 1}

        return requests.post(url=f"http://{host}:{port}", headers=headers, data=data).json()

    except Exception as e:
        print(e)


def process():
    start_time = time.time()
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
    print("response time:", time.time() - start_time, " s")



if __name__ == "__main__":
    process()