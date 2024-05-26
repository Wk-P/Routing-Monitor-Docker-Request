import requests
import time

def send_req(headers, data):
    return requests.post(url="http://127.0.0.1:8080", headers=headers, json=data).json()


if __name__ == "__main__":
    start = time.time()
    response = send_req({"task-type": "C"}, {"number": 10000000})
    print(response)
    print("Run time:", time.time() - start, "s") 
