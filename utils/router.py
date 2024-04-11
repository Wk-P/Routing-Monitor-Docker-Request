import aiohttp
from aiohttp import web
import asyncio
import docker
import time
import subprocess
import logging
import requests
import json
import random
# from keras.models import load_model
# from sklearn.preprocessing import MinMaxScaler
import numpy as np
import multiprocessing
import concurrent.futures
from multiprocessing import Manager

# model = load_model("./mlp_model/predict_model.keras")


# def test_predict(x_data, time_steps):
#     def create_sequences_x(x_data):
#         if len(x_data) < time_steps:
#             x_sequence = np.title(x_data, (time_steps, 1))
#         return np.array(x_sequence)

#     scaler_x = MinMaxScaler()
#     x_data = scaler_x.fit_transform(x_data)

#     x_data = create_sequences_x(x_data)

#     prediction = model.predict(x_data)
#     print(prediction)

def fetch(client:dict):
    container = client['client'].containers()[0]
    return [client['client'].stats(container["Id"], stream=False), client['node_id']]


def collect_cpu_usage(route_table):
    global cpus
    print("-- collect_cpu_usage --")
    # global route_table
    clients_list = list()
    # print(route_table)
    # try:
    for node in route_table:
        if node['state'] == "ready" and node['availability'] == "active":
            clients_list.append({"client": node['node_client'], "node_id": node['node_id']})
    

    # concurrent for get cpu usage
    futures = list()
    results = list()
    # print(clients_list)
    try:
        with concurrent.futures.ProcessPoolExecutor(len(clients_list)) as execurtor:
            for client in clients_list:
                futures.append(execurtor.submit(fetch, client))


            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

                
                # log.info(
                #     f"Hostname {node.attrs['Description']['Hostname']} Node {node.id} Container {container['Names']} CPU Percent is {cpu_percent: .2f} %"
                # )


                # Update cpu usage for special node
            for i in range(len(results)):
                for k in range(len(route_table)):
                    if route_table[k]['node_id'] == results[i][1] and route_table[k]['state'] == "ready" and route_table[k]['availability'] == "active":
                        node = route_table[k]
                        
                        # Old implementation

                        pre_cpu_stats = node['times']
                        cpu_stats = results[i][0]["cpu_stats"]
                        
                        system_cpu_usage = cpu_stats["system_cpu_usage"]

                        # calculate
                        cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - pre_cpu_stats["total_usage"]
                        system_delta = system_cpu_usage - pre_cpu_stats["system_cpu_usage"]


                        # cpu usage (NOT GOOD)
                        # cpu_usage = results[i][0]['cpu_stats']['cpu_usage']['total_usage']
                        # cpu_system = results[i][0]['cpu_stats']['system_cpu_usage']

                        # calculate
                        cpu_percent = cpu_delta / system_delta * cpus
                        
                        node['times']['total_usage'] = cpu_stats["cpu_usage"]["total_usage"]
                        node['times']['system_cpu_usage'] = system_cpu_usage
                        node['cpu_usage'] = cpu_percent

                        route_table[k] = node

                        # memory stats
                        memory_stats = results[i][0]["memory_stats"]
                        memory_usage = memory_stats["usage"] / 1024 / 1024
                        memory_limit = memory_stats["limit"] / 1024 / 1024 / 1024
                        # print(f"Hostname {results[i][1]} CPU Percent is {100 * cpu_percent: .2f} %")
                        # print(f"Hostname {results[i][1]} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")
    except: 
        pass

    # horizontal scaling scheduler
    # hs_scheduler(cpu_usage_stats)

    # except Exception as e:
    #     print("Error in get_cpu_usage")
    #     print(e)


def hs(route_table:list, _class):
    # for getting node id
    print("HS RUNNING...")
    password = "123321"

    # cpu_usage_stats = q.get()
    if _class == "up":
        for index in range(len(route_table)):
            temp_obj = route_table[index]
            if route_table[index]["availability"] == "drain" and route_table[index]["state"] == "ready":
                hs_active_command = f"echo '{password}' | sudo -S docker node update --availability active {route_table[index]['node_id']}"

                # scaling
                process = subprocess.Popen(
                    hs_active_command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                time.sleep(3)
                process.wait()
                print(f"return code: {process.returncode}")
                if process.returncode == 0:
                    print("UP")
                    temp_obj["availability"] = "active"
                    route_table[index] = temp_obj
                    print(f"s {route_table[index]}")

                return route_table

    elif _class == "down":
        active_num = 0
        for node in route_table:
            if node["availability"] == "active" and node["state"] == "ready":
                active_num += 1

        print(active_num)
        if active_num > 1:
            for index in range(len(route_table)):
                temp_obj = route_table[index]
                print(f"temp_obj: {temp_obj}")
                if route_table[index]["availability"] == "active" and route_table[index]["state"] == "ready":
                    hs_drain_command = f"echo '{password}' | sudo -S docker node update --availability drain {route_table[index]['node_id']}"
                    temp_obj["availability"] = "drain"
                    route_table[index] = temp_obj

                    process = subprocess.Popen(
                        hs_drain_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    time.sleep(3)
                    process.wait()
                    print(process.returncode)
                    # scaling
                    if process.returncode == 0:
                        print("DOWN")
                    return route_table

    else:
        print("Error in HS")

        return route_table



def init_route_table(manager:multiprocessing.Manager):
    port = 2375
    manager_ip = "192.168.56.107"
    swarm_client = docker.DockerClient(base_url=f"tcp://{manager_ip}:{port}")
    swarm_nodes = swarm_client.nodes.list()
    cpu_usage_stats = manager.list()
    container_port = 8080
    # declare

    # initialize lists
    for node in swarm_nodes:
        if node.attrs["Spec"]["Role"] == "worker":
            cpu_usage_stats.append({
                "node_client": docker.APIClient(base_url=f"tcp://{node.attrs['Status']['Addr']}:2375"),
                "node_id": node.id,
                    "name": node.attrs["Description"]["Hostname"],
                    "cpu_usage": 0,
                    "times": {
                        "total_usage": 0,
                        "system_cpu_usage": 0,
                    },
                    "availability": node.attrs["Spec"][
                        "Availability"
                    ],  # get availability for choosing drain node to HS
                    "state": node.attrs["Status"]["State"],
                    "address": node.attrs["Status"]["Addr"],
                    "port": container_port,
                    "node_object": node,
            })
    return cpu_usage_stats


# STOP USING
# def monitor_main():
#     global route_table
#     try:
#         print("Start Monitoring...")

#         handler = logging.FileHandler(filename="logs/hs-log.log")
#         monitor_log = logging.Logger(name="monitor", level=logging.INFO)
#         monitor_log.addHandler(handler)

#         while True:
#             for stats in route_table:
#                 collect_cpu_usage(
#                     stats,
#                     ip=stats["address"],
#                     node=stats["node_object"],
#                     log=monitor_log,
#                 )

#             monitor_log.info("--------------------------")
#             hs_scheduler(route_table)
#     except:
#         print("Error in monitor main function")


# declare an async function for send request
async def req_post_task(
    session: aiohttp.ClientSession,
    url,
    method,
    request: aiohttp.ClientRequest,
    request_data,
):

    if method == "POST":
        # send request to others' servers
        async with session.post(
            url=url, headers=request.headers, json=request_data
        ) as response:
            # to Json

            response_data = await response.json()

            usage = list()
            for u in route_table:
                if u["state"] == "ready" and u["availability"] == "active":
                    usage.append({u["name"]: u["cpu_usage"]})

            # response
            response = {
                "data": response_data,
                "server": url,
                "replicas_usage": usage,
            }

            # add to list for update route_table
            # for stats in route_table:
            #     if stats['address'] == url:
            #         stats['cpu_usage'] = response_data['cpuUsage']

    else:
        print("Error in req_task")
        response = None

    # put into queue for sync
    # await q.put(rt)

    return response






# For changing by cpu usage, first time is random, next is to cpuUsage min
async def handle_request(request: aiohttp.ClientRequest):
    global route_table
    global req_count
    global round_robin_index

    # get request data 
    request_data = await request.json()
    
    
    # temp_rt: list = route_table
    server_url = None

    ### cpu_usage algorithm
    min_usage = 2
    for stats in route_table:
        # print(f"{stats['address']} : {stats['cpu_usage']}")
        if stats["state"] == "ready" and stats["availability"] == "active":
            if float(stats["cpu_usage"]) <= min_usage:
                server_url = f"http://{stats['address']}:{stats['port']}"
                min_usage = stats["cpu_usage"]

    ### random algorithm
    # round_robin_index = random.randint(0, len(route_table) - 1)
    # server_url = route_table[round_robin_index]['address']

    ### round_robin algorithm
    # server_url = route_table[round_robin_index]['address']
    # round_robin_index = ( round_robin_index + 1 ) % len(route_table)


    # cpu predict
    # x_data = list()
    # x_data.append(request_data['number'])

    # create x_data list
    # for stats in route_table:
    #     if stats["state"] == "ready" and stats["availability"] == "active":
    #         # 1 2 3 No. of node add to x-training data 
    #         x_data.append()

    # test_predict(x_data)
    
    tasks = []

    # send request to first server
    async with aiohttp.ClientSession() as session:

        ### round_robin
        # for stats in route_table:
        #     if stats["state"] == "ready" and stats["availability"] == "active":
        #         if server_url == stats["address"]:
        #             tasks.append(
        #                 asyncio.create_task(
        #                     req_post_task(
        #                         session,
        #                         f"http://{stats['address']}:{stats['port']}",
        #                         "POST",
        #                         request,
        #                         request_data,
        #                         cpu_limit,
        #                     )
        #                 )
        #             )
        

        ### cpu_usage 
        tasks.append(
            asyncio.create_task(
                req_post_task(
                    session,
                    server_url,
                    "POST",
                    request,
                    request_data,
                )
            )
        )

        responses = await asyncio.gather(*tasks)

    return web.json_response(responses)


def server_proc():
    try:
        main_loop = asyncio.new_event_loop()

        app = web.Application()
        app.router.add_post("/", handle_request)

        web.run_app(app=app, host="192.168.56.107", port=8080, loop=main_loop)

    except asyncio.CancelledError:
        pass
    finally:
        pass


def hs_proc(route_table: list):
    global cpu_limit
    # global route_table

    handler = logging.FileHandler(filename="logs/hs-log.log", mode="w")
    monitor_log = logging.Logger(name="monitor", level=logging.INFO)
    monitor_log.addHandler(handler)

    enable_hs_up = 0
    enable_hs_down = -1

    max_node_list = list()
    max_usage_counter = 0

    try:

        for index in range(len(route_table)):
            temp_obj = route_table[index]
            if route_table[index]["state"] == "ready" and route_table[index]["availability"] == "drain":
                temp_obj["enable_hs"] = "up"
                route_table[index] = temp_obj
                enable_hs_up += 1
            elif route_table[index]["state"] == "ready" and route_table[index]["availability"] == "active":
                temp_obj["enable_hs"] = "down"
                route_table[index] = temp_obj
                enable_hs_down += 1

        while True:

            print(f"enable_hs_up: {enable_hs_up}")
            print(f"enable_hs_down: {enable_hs_down}")

            collect_cpu_usage(route_table)

            for index in range(len(route_table)):
                temp_obj = route_table[index]
                print(f"{route_table[index]['name']} CPU usage => : {100 * route_table[index]['cpu_usage']} %")
                if route_table[index]["state"] == "ready" and route_table[index]["availability"] == "active":
                    if route_table[index]["cpu_usage"] > 0.9 * cpu_limit and route_table[index]['node_id'] not in max_node_list:
                        max_usage_counter += 1
                    if route_table[index]["cpu_usage"] < 0.1 * cpu_limit:
                        max_usage_counter -= 1

                print(f"max_usage_counter: {max_usage_counter}")
                # hs up
                if max_usage_counter > 3:
                    max_usage_counter = 0
                    if enable_hs_up > 0 and route_table[index]['node_id'] not in max_node_list:
                        enable_hs_up -= 1
                        enable_hs_down += 1
                        route_table = hs(route_table, "up")
                        max_node_list.append(route_table[index]['node_id'])
                        print("add!")


                # hs down
                if max_usage_counter < -3:
                    if route_table[index]['node_id'] in max_node_list:
                        print("out!")
                        max_node_list.remove(route_table[index]['node_id'])
                    max_usage_counter = 0
                    if enable_hs_down > 0:
                        enable_hs_down -= 1
                        enable_hs_up += 1
                        route_table = hs(route_table, "down")

            for node in route_table:
                print(f"{node['name']}: {node['availability']}", end='\n')
    except:
        pass

if __name__ == "__main__":
    req_count = 0
    cpu_limit = 0.6
    cpus = 2

    # round robin
    round_robin_index = 0
    with multiprocessing.Manager() as manager:
        route_table = init_route_table(manager)
        # print(route_table)
        # server-process
        proc1 = multiprocessing.Process(target=server_proc)
        
        # hs-process
        proc2 = multiprocessing.Process(target=hs_proc, args=(route_table,))

        proc1.start()
        proc2.start()

        proc1.join()
        proc2.join()

    