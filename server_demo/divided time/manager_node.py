import aiohttp
import asyncio
import time

WORKER_NODES = [
    'http://192.168.0.150:8080/process',
    'http://192.168.0.151:8080/process',
    'http://192.168.0.152:8080/process',
]

# Global data structure for storing historical metrics
historical_metrics = {
    "request_preparation_time": [],
    "request_dispatch_time": [],
    "queue_waiting_time": [],
    "processing_time": [],
    "response_transmission_time": [],
    "total_response_time": [],
}

def update_metrics(metric_name, value):
    """Update global metrics with new data."""
    if metric_name in historical_metrics:
        historical_metrics[metric_name].append(value)
        # Limit the history size to avoid memory issues
        if len(historical_metrics[metric_name]) > 1000:
            historical_metrics[metric_name].pop(0)

def predict_response_time():
    """Predict the next response time based on historical metrics."""
    # Use simple averages for prediction
    predicted_time = sum(historical_metrics["total_response_time"]) / len(historical_metrics["total_response_time"]) if historical_metrics["total_response_time"] else 0
    return predicted_time

async def measure_worker_time(worker_url, payload):
    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Measure Request Preparation Time
            prep_start = time.perf_counter()
            prepared_payload = payload  # Simulate any preprocessing here
            prep_time = time.perf_counter() - prep_start
            update_metrics("request_preparation_time", prep_time)

            # Step 2: Measure Network Transmission Time (Request)
            request_start = time.perf_counter()
            async with session.post(worker_url, json=prepared_payload) as response:
                request_dispatch_time = time.perf_counter() - request_start
                update_metrics("request_dispatch_time", request_dispatch_time)

                # Step 3: Read Worker Response
                response_start = time.perf_counter()
                response_data = await response.json()
                response_receive_time = time.perf_counter() - response_start
                update_metrics("response_transmission_time", response_receive_time)

                total_response_time = time.perf_counter() - request_start
                update_metrics("total_response_time", total_response_time)

                # Extract additional times from worker response
                queue_waiting_time = response_data.get("queue_waiting_time", 0)
                processing_time = response_data.get("processing_time", 0)
                update_metrics("queue_waiting_time", queue_waiting_time)
                update_metrics("processing_time", processing_time)

            # Predict next response time
            predicted_time = predict_response_time()

            print(f"Worker URL: {worker_url}")
            print(f"Request Preparation Time: {prep_time:.4f}s")
            print(f"Request Dispatch Time: {request_dispatch_time:.4f}s")
            print(f"Queue Waiting Time: {queue_waiting_time:.4f}s")
            print(f"Processing Time: {processing_time:.4f}s")
            print(f"Response Transmission Time: {response_receive_time:.4f}s")
            print(f"Total Response Time: {total_response_time:.4f}s")
            print(f"Predicted Next Response Time: {predicted_time:.4f}s\n")

            return {
                "worker_url": worker_url,
                "prep_time": prep_time,
                "request_dispatch_time": request_dispatch_time,
                "queue_waiting_time": queue_waiting_time,
                "processing_time": processing_time,
                "response_transmission_time": response_receive_time,
                "total_response_time": total_response_time,
                "predicted_response_time": predicted_time,
            }

        except Exception as e:
            print(f"Error communicating with {worker_url}: {e}")
            return None

async def main():
    payload = {"number": 42}  # Example task payload
    tasks = [measure_worker_time(url, payload) for url in WORKER_NODES]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            print(result)

if __name__ == "__main__":
    asyncio.run(main())
