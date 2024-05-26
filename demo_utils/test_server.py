import aiohttp
from aiohttp import web


async def handle(request):
    name = request.match_info.get('name', 'Anonymous')
    text = f"Hello, {name}"

    return web.Response(text=text)

app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{name}', handle)])


if __name__ == "__main__":
    web.run_app(app, host="192.168.56.107", port=8080)