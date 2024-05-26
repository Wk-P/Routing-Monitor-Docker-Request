import aiohttp
from aiohttp import web


def prime(num):
    for i in range(2, num):
        if (num % i) == 0:
            return False
    return True


def prime_count(r):
    count = 0
    for i in range(2, r):
        if prime(i):
            count += 1
    return count


async def handle(request):
    headers = request.headers
    data = await request.json()

    task_type = headers["task-type"]
    result = 0
    if task_type == "C":
        result = prime_count(data['number'])

    return web.json_response({"success": 1, "result": result})


if __name__ == "__main__":
    app = web.Application()
    app.add_routes([web.post("/", handle)])
    web.run_app(app, host="127.0.0.1", port=8080)
