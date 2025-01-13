from aiohttp import web
import time
import asyncio

async def process_task(request):
    try:
        data = await request.json()
        arrival_time = time.perf_counter()

        # Step 1: Simulate Queue Waiting Time
        await asyncio.sleep(0.2)  # Simulate waiting in queue
        queue_waiting_time = time.perf_counter() - arrival_time

        # Step 2: Simulate Resource Contention Time
        contention_start = time.perf_counter()
        await asyncio.sleep(0.1)  # Simulate resource contention
        resource_contention_time = time.perf_counter() - contention_start

        # Step 3: Simulate Task Processing Time
        processing_start = time.perf_counter()
        number = data.get("number", 0)
        result = number * number  # Example processing
        await asyncio.sleep(0.5)  # Simulate processing delay
        processing_time = time.perf_counter() - processing_start

        return web.json_response({
            "result": result,
            "queue_waiting_time": queue_waiting_time,
            "resource_contention_time": resource_contention_time,
            "processing_time": processing_time,
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def create_app():
    app = web.Application()
    app.router.add_post('/process', process_task)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host='0.0.0.0', port=8080)
