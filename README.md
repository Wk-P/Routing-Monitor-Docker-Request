model compile and fitting code link
https://colab.research.google.com/drive/1yEa1be7TbpFCQLq5pcpkggb1Elthoenn?usp=sharing



## 2024-10-31
More algorithm and Distribution request numbers


## 2024-11-20
### Client
- python3.12
- aiohttp HTTP1.1

### Manager
- raspberrypi 4
- function: LB algorithm
- python3.11
- aiohttp HTTP1.1

### Worker
- raspberrpi 3
- function: Prime number count
- python3.12
- aiohttp HTTP1.1

### Issue
1. 现在 1000个请求只会返回639个，剩下的请求 Manager 虽然发送给后端，但是没有收到回复 [未解决]