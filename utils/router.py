import aiohttp
import asyncio
from aiohttp import web
import multiprocessing

# Initial route table with example entries
route_table = [
    {
        "address": "http://192.168.56.103:8080",
        'status': "N"
    },
    {
        "address": "http://192.168.56.104:8080",
        'status': "Y"
    }
]

def update_route_table(shared_route_table):
    # Update the shared route_table in the main process
    while True:
        # You can update the route_table here as needed
        # For example: shared_route_table[0]['status'] = 'Y'
        pass

async def web_app(shared_route_table):
    # Use the shared route_table in the coroutine
    while True:
        # Access the shared route_table here and process as needed
        await asyncio.sleep(1)

async def handle_request(request):
    # Use the shared route_table when handling requests
    global server_index
    server_url = None

    while True:
        if shared_route_table[server_index]['status'] == 'Y':
            server_url = shared_route_table[server_index]['address']
            break
        server_index = (server_index + 1) % len(shared_route_table)

    # The rest of the request handling logic remains unchanged
    return web.Response(text=f"Forwarded to {server_url}")

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    shared_route_table = manager.list(route_table)  # Create a shared list

    # Start a process to update the route_table
    update_process = multiprocessing.Process(target=update_route_table, args=(shared_route_table,))
    update_process.start()

    # Create an event loop
    loop = asyncio.get_event_loop()

    # Start the web_app coroutine
    web_app_task = loop.create_task(web_app(shared_route_table))

    app = web.Application()
    app.router.add_post('/', handle_request)

    server_index = 0  # This variable needs to be declared globally

    web.run_app(app, host='192.168.56.102', port=8080)
