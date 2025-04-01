import time
import asyncio
import json
from aiohttp import TCPConnector, ClientTimeout, ClientSession, ClientResponse
from datetime import datetime
from tools.utils import write_json_file
from pathlib import Path
import uuid
import numpy as np
import matplotlib.pyplot as plt

WORK_DIR = Path(__file__).parent


class Result:
    def __init__(self, **data):
        self.__dict__.update(data)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.__dict__, indent=4)



def draw_plot(filepath: Path, filename: str, data: dict, title: str, XLabel: str, YLabel: str):
    if not filepath.exists():
        filepath.mkdir(parents=True, exist_ok=True)
    
    count = sum(1 for file in filepath.iterdir() if file.is_file() and file.suffix == '.png')
    if count > 0:
        filename = f"{filename}_{count}"
    else:
        filename = f"{filename}"   

    file_path = filepath / f"{filename}.png"

    x = list(data.keys())
    y = list(data.values())

    plt.figure(figsize=(16, 9))
    plt.plot(x, y, marker="o", label="Avg Response Time")

    plt.title(title)
    plt.xlabel(XLabel)
    plt.ylabel(YLabel)
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(str(file_path))
    plt.close()



async def send_request(session: ClientSession, **kw):
    url = kw.get('url', None)
    _json = kw.get('json', None)

    if None in (url, _json):
        return None
    
    start_time = time.perf_counter()

    async with session.post(url=url, json=_json) as resp:
        resp: ClientResponse
        try:
            response: dict = await resp.json()
            return Result( 
                status_code="OK",
                responese_time=time.perf_counter() - start_time
            )

        except Exception as e:
            print(f"Error: {str(e)}")
            return {
                "error": str(e)
            }
    

async def main():
    url = 'http://192.168.0.100:8199'
    batches = [ i for i in range(1, 100)]

    all_results = []

    for nr in batches:
        async with ClientSession(connector=TCPConnector(limit=0), timeout=ClientTimeout(None)) as session:
            # one batch
            batch_tasks = [asyncio.create_task(send_request(session, url=url, json={
                "number": 50000,
                "request_id": f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}",
                "algo_name": "proposed"
            })) for _ in range(nr)]

            results = await asyncio.gather(*batch_tasks)

            parsed_result = {
                "request_sum": nr,
                "avg_response_time": float(np.mean(np.array([result.to_dict().get('responese_time', 0) for result in results])))
            }
            
            all_results.append(parsed_result)


    write_json_file(filepath=WORK_DIR / 'results', filename=f'{nr}_results', mode='a', data=all_results)

    parsed_all_results = {}

    for result in all_results:
        parsed_all_results.update({
            result['request_sum']: result['avg_response_time']
        })

    draw_plot(filepath=WORK_DIR / 'results', filename=f"comparison", data=parsed_all_results, title='requests sum and avg response time', XLabel="N requests", YLabel="Avg resposne time (secondes)")

if __name__ == "__main__":
    asyncio.run(main())