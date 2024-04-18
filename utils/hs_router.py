import aiohttp
from aiohttp import web
import aiohttp.web_request
import asyncio
import docker
import subprocess
import logging
# from keras.models import load_model
# from sklearn.preprocessing import MinMaxScaler
import numpy as np
import multiprocessing
import concurrent.futures


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
    return [client['client'].stats(container["Id"], stream=False, one_shot=True), client['node_id']]

def collect_cpu_usage(route_table):
    global cpus
    print("-- collect_cpu_usage start --")
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
                        
                        # Old implementation

                        pre_cpu_stats = route_table[k]['times']
                        cpu_stats = results[i][0]["cpu_stats"]
                        
                        system_cpu_usage = cpu_stats["system_cpu_usage"]

                        # calculate
                        cpu_delta = cpu_stats["cpu_usage"]["total_usage"] - pre_cpu_stats["total_usage"]
                        system_delta = system_cpu_usage - pre_cpu_stats["system_cpu_usage"]


                        # cpu usage (NOT GOOD)
                        # cpu_usage = results[i][0]['cpu_stats']['cpu_usage']['total_usage']
                        # cpu_system = results[i][0]['cpu_stats']['system_cpu_usage']

                        # calculate
                        cpu_percent = max(round(cpu_delta / system_delta * cpus, 2), 0)
                        print(f"cpu_percent => {cpu_percent}")
                        route_table[k]['times']['total_usage'] = cpu_stats["cpu_usage"]["total_usage"]
                        route_table[k]['times']['system_cpu_usage'] = system_cpu_usage
                        route_table[k]['cpu_usage'] = cpu_percent
                        if len(route_table[k]['cpu_usage_history']) >= 10:
                            route_table[k]['cpu_usage_history'].pop(0)
                        route_table[k]['cpu_usage_history'].append(cpu_percent)

                        # memory stats
                        memory_stats = results[i][0]["memory_stats"]
                        memory_usage = memory_stats["usage"] / 1024 / 1024
                        memory_limit = memory_stats["limit"] / 1024 / 1024 / 1024
                        # print(f"Hostname {results[i][1]} CPU Percent is {100 * cpu_percent: .2f} %")
                        # print(f"Hostname {results[i][1]} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")
        print("-- collect_cpu_usage end --")
    except: 
        pass

    # horizontal scaling scheduler
    # hs_scheduler(cpu_usage_stats)

    # except Exception as e:
    #     print("Error in get_cpu_usage")
    #     print(e)


def hs(route_table:list, _class):
    # for getting node id
    print(f"HS {_class} RUNNING...")
    password = "123321"
    try:
        if _class == "up":
            for index in range(len(route_table)):
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
                    process.wait()
                    print(f"return code: {process.returncode}")
                    if process.returncode == 0:
                        print("UP")
                        route_table[index]["availability"] = "active"
                        route_table[index]["idle"] = "idle"
                        return route_table[index]['node_id']

        elif _class == "down":
            active_num = 0
            for node in route_table:
                if node["availability"] == "active" and node["state"] == "ready":
                    active_num += 1

            print("active_num =>", active_num)
            if active_num > 1:
                for index in range(len(route_table)):
                    if route_table[index]["availability"] == "active" and route_table[index]["state"] == "ready":
                        hs_drain_command = f"echo '{password}' | sudo -S docker node update --availability drain {route_table[index]['node_id']}"
                        route_table[index]["availability"] = "drain"
                        route_table[index]["cpu_status"] = "null"
                        process = subprocess.Popen(
                            hs_drain_command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )
                        process.wait()
                        print(f"return code: {process.returncode}")
                        # scaling
                        if process.returncode == 0:
                            print("DOWN")
                            return route_table[index]['node_id']

        else:
            print("Error at args")

            return None
    except Exception as e:
        print(e)
        exit(1)


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
            cpu_usage_stats.append(manager.dict({
                "node_client": docker.APIClient(base_url=f"tcp://{node.attrs['Status']['Addr']}:2375"),
                "node_id": node.id,
                "name": node.attrs["Description"]["Hostname"],
                "cpu_usage": 0,
                "times": manager.dict({
                    "total_usage": 0,
                    "system_cpu_usage": 0,
                }),
                "cpu_status": "idle",
                "cpu_usage_history": manager.list(),
                "availability": node.attrs["Spec"]["Availability"],  # get availability for choosing drain node to HS
                "state": node.attrs["Status"]["State"],
                "address": node.attrs["Status"]["Addr"],
                "port": container_port,
                "node_object": node,
            }))
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
async def reverse_proxy(request: aiohttp.web_request.Request):
    global route_table
    global req_count
    global round_robin_index
    async with aiohttp.ClientSession() as session:
        try:
            url = get_server_url(route_table=route_table, req_count=req_count, round_robin_index=round_robin_index)
            # send request to others' servers
            data = await request.post()
            # before packet fowarding
            usage = list()
            for u in route_table:
                if u["state"] == "ready" and u["availability"] == "active":
                    usage.append({u["name"]: u["cpu_usage"]})

            async with session.post(
                url=url, headers=request.headers, data=data
            ) as response:
                # to Json

                data = await response.json()

                # response
                response = {
                    "data": data,
                    "server": url,
                    "replicas_usage": usage,
                }

            # add to list for update route_table
            # for stats in route_table:
            #     if stats['address'] == url:
            #         stats['cpu_usage'] = response_data['cpuUsage']

        # put into queue for sync
        # await q.put(rt)

            return web.json_response(response)
        except Exception as e:
            print(e)



def get_server_url(route_table, round_robin_index=None, req_count=None):
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


    return server_url


def server_proc():
    try:
        app = web.Application()
        app.router.add_post('/', reverse_proxy)
        web.run_app(app=app, host="192.168.56.107", port=8080)

    except asyncio.CancelledError:
        pass
    finally:
        print("END")

def hs_proc(route_table: list, manager:multiprocessing.Manager):
    global cpu_limit
    # global route_table

    handler = logging.FileHandler(filename="logs/hs-log.log", mode="w")
    monitor_log = logging.Logger(name="monitor", level=logging.INFO)
    monitor_log.addHandler(handler)

    enable_hs_up = 0
    enable_hs_down = -1
    active_nodes_set = manager.list()
    busy_nodes_set = manager.list()
    idle_nodes_set = manager.list()
    load_nodes_set = manager.list()

    try:
        # init status set
        for index in range(len(route_table)):
            if route_table[index]["state"] == "ready" and route_table[index]["availability"] == "drain":
                enable_hs_up += 1
            elif route_table[index]["state"] == "ready" and route_table[index]["availability"] == "active":
                active_nodes_set.append(route_table[index]['node_id'])
                if route_table[index]['cpu_status'] == "idle":
                    idle_nodes_set.append(route_table[index]['node_id'])
                elif route_table[index]['cpu_status'] == "busy":
                    busy_nodes_set.append(route_table[index]['node_id'])
                else:
                    load_nodes_set.append(route_table[index]['node_id'])
                enable_hs_down += 1

        while True:
            collect_cpu_usage(route_table)

            print(f"enable_hs_up: {enable_hs_up}")
            print(f"enable_hs_down: {enable_hs_down}")
            print(f"cpu_limit =>", cpu_limit)


            # change cpu usage to cpu status label
            for index in range(len(route_table)):
                print(f"{route_table[index]['name']} CPU usage => : {100 * route_table[index]['cpu_usage']} %")
                if route_table[index]["state"] == "ready" and route_table[index]["availability"] == "active":
                    if len(route_table[index]['cpu_usage_history']) >= 10:
                        cpu_usage_avg = sum(route_table[index]['cpu_usage_history']) / len(route_table[index]['cpu_usage_history'])
                        if cpu_usage_avg > cpu_limit * 0.8:
                            route_table[index]['cpu_status'] = 'busy'
                            # change node status node
                            if route_table[index]['node_id'] not in busy_nodes_set:
                                busy_nodes_set.append(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in idle_nodes_set:
                                    idle_nodes_set.remove(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in load_nodes_set:
                                    load_nodes_set.remove(route_table[index]['node_id'])
                        elif cpu_usage_avg < cpu_limit * 0.2:
                            route_table[index]['cpu_status'] = 'idle'
                            if route_table[index]['node_id'] not in idle_nodes_set:
                                idle_nodes_set.append(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in busy_nodes_set:
                                    busy_nodes_set.remove(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in load_nodes_set:
                                    load_nodes_set.remove(route_table[index]['node_id'])
                        else:
                            route_table[index]['cpu_status'] = 'load'
                            if route_table[index]['node_id'] not in load_nodes_set:
                                load_nodes_set.append(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in busy_nodes_set:
                                    busy_nodes_set.remove(route_table[index]['node_id'])
                                if route_table[index]['node_id'] in idle_nodes_set:
                                    idle_nodes_set.remove(route_table[index]['node_id'])
                        
                    
            # hs up
            if len(busy_nodes_set) >= len(active_nodes_set) and enable_hs_up:
                enable_hs_up -= 1
                enable_hs_down += 1
                hs(route_table, "up")
                print("Horizontal scaling")


            # hs down
            if len(idle_nodes_set) >= len(active_nodes_set) and enable_hs_down:
                enable_hs_down -= 1
                enable_hs_up += 1
                node_id = hs(route_table, "down")
                if node_id in busy_nodes_set:
                    busy_nodes_set.remove(node_id)
                elif node_id in idle_nodes_set:
                    idle_nodes_set.remove(node_id)
                elif node_id in load_nodes_set:
                    load_nodes_set.remove(node_id)
                print("Horizontal scaling down")

            for node in route_table:
                print(f"{node['name']}: {node['availability']}", end='\n')
    except Exception as e:
        print(e)
        exit(1)

if __name__ == "__main__":
    req_count = 0
    cpu_limit = 0.8
    cpus = 2
    session = None

    # round robin
    round_robin_index = 0
    with multiprocessing.Manager() as manager:
        route_table = init_route_table(manager)
        # print(route_table)
        # server-process
        proc1 = multiprocessing.Process(target=server_proc)
        
        # hs-process
        proc2 = multiprocessing.Process(target=hs_proc, args=(route_table, manager))

        proc1.start()
        proc2.start()

        proc1.join()
        proc2.join()
    
    session.close()

    