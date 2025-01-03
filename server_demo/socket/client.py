# client.py
import aiohttp
import asyncio

async def send_request(server_host, server_port, message):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://{server_host}:{server_port}/handle", json=message) as resp:
            response = await resp.text()
            print(f"Response: {response}")

if __name__ == "__main__":
    async def main():
        tasks = [
            send_request("localhost", 4000, {"task": f"Task {i}", "estimated_time": i % 3 + 1})
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

    asyncio.run(main())