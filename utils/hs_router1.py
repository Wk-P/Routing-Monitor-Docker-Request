import aiohttp
from aiohttp import web
import multiprocessing

class Info():
    def __init__(self):
        self.ips = [
            "10.0.2.7",
            "10.0.2.6",
            "10.0.2.8"
        ]
        self.port = 8080
        self.session = None

    async def start_session(self):
        self.session = aiohttp.ClientSession()


info_obj = Info()

async def request_handler(request: web.Request):
    global info_obj
    headers = request.headers
    data = await request.post()

    # url choose
    url = f"http://{info_obj.ips[2]}:{info_obj.port}"

    print(url)
    print(info_obj.session)

    async with info_obj.session.post(url=url, data=data, headers=headers) as response:
        
        response_data = await response.json()

        return web.json_response({"success": 1, "response": response_data})



async def server_app_init():
    global info_obj
    app = web.Application()
    app.router.add_post("", request_handler)
    app.on_startup.append(lambda app: info_obj.start_session())

    return app
    


def server_proc():
    app = server_app_init()
    web.run_app(app, host='10.0.2.9', port=8081)


if __name__ == "__main__":
    server = multiprocessing.Process(target=server_proc)
    server.start()

    server.join()