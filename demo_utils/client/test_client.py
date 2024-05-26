# test client
import requests
import concurrent.futures
import time
import typing


def send(n):
    try:
        host = "10.0.2.9"
        port = 8081
        
        headers = {'task_type': "C"}
        data = {"number": n}
        

        start = time.time()
        response = requests.post(url=f"http://{host}:{port}", headers=headers, data=data).json()

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
        futures:typing.List[concurrent.futures.Future] = []
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
    # numbers = [100000, 10000000]
    # cpu = 50
    # data = []
    
    process()