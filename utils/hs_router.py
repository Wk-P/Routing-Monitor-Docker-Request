import aiohttp
from aiohttp import web
import aiohttp.web_request
import asyncio
import docker
import subprocess
import logging
import time
# from keras.models import load_model
# from sklearn.preprocessing import MinMaxScaler
import numpy as np
import multiprocessing
import concurrent.futures
import paramiko
import re


handler = logging.FileHandler(filename="./logs/hs-log_v3.log", mode="w")
monitor_log = logging.Logger(name="monitor", level=logging.INFO)
monitor_log.addHandler(handler)

errHandler = logging.FileHandler(filename="./logs/err-log_v1.log", mode="w")
errLog = logging.Logger(name='error log', level=logging.INFO)
errLog.addHandler(errHandler)


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


def ssh_command(host, port, username, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=username, password=password)
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    client.close()
    return output, error




def fetch(client:dict):
    output, error = ssh_command(client['address'], 22, "soar", "123321", "df --total /var/lib/docker/")
    matches = re.findall(r"([\d]+)% -", output)
    if matches:
        hdd_usage = float(matches[0]) / 100
    else:
        hdd_usage = 0

    container = client['client'].containers(filters={'status': "running"})
    if len(container):
        return [client['client'].stats(container[0]["Id"], stream=False, one_shot=True), client['node_id'], hdd_usage]


def collect_cpu_usage(route_table, manager_client):
    global cpus
    print("-- collect_cpu_usage start --")

    # global route_table
    clients_list = list()

    for node in route_table:
        if node['state'] == "ready" and node['availability'] == "active":
            clients_list.append({"client": node['node_client'], "node_id": node['node_id'], "address": node['address']})
    

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
                log_str = ""
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
                        cpu_percent = max(0, round(cpu_delta / system_delta * cpus, 4))
                        print(f"cpu_percent => {cpu_percent}")
                        route_table[k]['times']['total_usage'] = cpu_stats["cpu_usage"]["total_usage"]
                        route_table[k]['times']['system_cpu_usage'] = system_cpu_usage
                        route_table[k]['cpu_usage'] = cpu_percent
                        if len(route_table[k]['cpu_usage_history']) >= 10:
                            route_table[k]['cpu_usage_history'].pop(0)
                        route_table[k]['cpu_usage_history'].append(cpu_percent)

                        # memory stats

                        # log
                        memory_stats = results[i][0]["memory_stats"]
                        memory_usage = memory_stats["usage"]
                        memory_limit = memory_stats["limit"]
                        memory_percent = round(memory_usage / memory_limit, 4)


                        # "memory": manager.dict({
                        #     "memory_percent": 0,
                        #     "memory_usage": 0,
                        #     "memory_limit": 0
                        # }),


                        # log
                        route_table[k]['memory']['memory_percent'] = memory_percent
                        route_table[k]['memory']['memory_usage'] = memory_usage
                        route_table[k]['memory']['memory_limit'] = memory_limit


                        # hdd stats
                        # log 
                        hdd_usgae = results[i][2]
                        route_table[k]['hdd_usage'] = hdd_usgae

                        log_str += f"[{route_table[k]['name']}] => mem: {memory_percent} | hdd: {hdd_usgae} | timestamp: {time.time()} "
                        
                monitor_log.info(log_str)
                        # print(f"Hostname {results[i][1]} CPU Percent is {100 * cpu_percent: .2f} %")
                        # print(f"Hostname {results[i][1]} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")
        print("-- collect_cpu_usage end --")
    except Exception as e: 
        print("135", e)
        errLog.exception(e)
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

    client = docker.DockerClient(base_url="tcp://10.0.2.15:2375")
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
                    wait_task_running(node_id=route_table[index]['node_id'], client=client)
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
                        # wait for start
                        wait_task_exiting(node_id=route_table[index]['node_id'], client=client)
                        print(f"return code: {process.returncode}")
                        # scaling
                        if process.returncode == 0:
                            print("DOWN")
                            return route_table[index]['node_id']

        else:
            print("Error at args")

            return None
    except Exception as e:
        print("208", e)
        errLog.exception(e)
        exit(1)


def wait_task_running(node_id, client:docker.DockerClient):
    while True:
        service = client.services.get('node-service')

        tasks = service.tasks()

        for task in tasks:
            if task['Status']['State'] == "running" and task['NodeID'] == node_id:
                return
        time.sleep(1)


def wait_task_exiting(node_id, client:docker.DockerClient):
    while True:
        service = client.services.get('node-service')

        tasks = service.tasks()

        for task in tasks:
            if task['Status']['State'] == "shutdown" and task['NodeID'] == node_id:
                return
        time.sleep(1)


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
                "memory": manager.dict({
                    "memory_percent": 0,
                    "memory_usage": 0,
                    "memory_limit": 0
                }),
                "hdd_usage": 0,
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
            url, hostname = get_server_url(route_table=route_table, req_count=req_count, round_robin_index=round_robin_index)
            # send request to others' servers
            data = await request.post()             # application/x-www-form-urlencoded
            # before packet fowarding
            _cpu = dict()
            _mem = dict()
            _hdd = dict()
            _timestamp = time.time()
            for node in route_table:
                if node["state"] == "ready" and node["availability"] == "active":
                    _cpu[node["name"]] = node["cpu_usage"]
                    _mem[node["name"]] = node["memory"]["memory_percent"]
                    _hdd[node["name"]] = node["hdd_usage"]
            try:
                async with session.post(
                    url=url, headers=request.headers, data=data
                ) as response:
                    # to Json
                    data = await response.json()

                    # response
                    response = {
                        "data": data,
                        "server": url,
                        "hostname": hostname,
                        "timestamp": _timestamp,
                        "replicas_resources": {
                            "cpu": _cpu,
                            "mem": _mem,
                            "hdd": _hdd,
                        },
                    }

                return web.json_response(response)
            except Exception as e:
                print("371", e)
                errLog.exception(e)

            # add to list for update route_table
            # for stats in route_table:
            #     if stats['address'] == url:
            #         stats['cpu_usage'] = response_data['cpuUsage']

        # put into queue for sync
        # await q.put(rt)

            
        except Exception as e:
            print("393", e)
            errLog.exception(e)
            return web.json_response({"error": 1})



def get_server_url(route_table, round_robin_index=None, req_count=None):
    try:
        server_url = None
        hostname = None
        ### cpu_usage algorithm
        min_usage = 2
        for stats in route_table:
            if stats["state"] == "ready" and stats["availability"] == "active":
                if float(stats["cpu_usage"]) <= min_usage:
                    server_url = f"http://{stats['address']}:{stats['port']}"
                    min_usage = stats["cpu_usage"]
                    hostname = stats["name"]


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


        return server_url, hostname
    except Exception as e:
        errLog.exception(e)
        for stats in route_table:
            if stats["state"] == "ready" and stats["availability"] == "active":
                server_url = f"http://{stats['address']}:{stats['port']}"
                hostname = stats["name"]
                return server_url, hostname

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
            collect_cpu_usage(route_table, monitor_log)

            # print(f"enable_hs_up: {enable_hs_up}")
            # print(f"enable_hs_down: {enable_hs_down}")
            # print(f"cpu_limit =>", cpu_limit)


            # change cpu usage to cpu status label
            for index in range(len(route_table)):
                # print(f"{route_table[index]['name']} CPU usage => : {100 * route_table[index]['cpu_usage']} %")
                if route_table[index]["state"] == "ready" and route_table[index]["availability"] == "active":
                    if len(route_table[index]['cpu_usage_history']) >= 10:
                        cpu_usage_avg = sum(route_table[index]['cpu_usage_history']) / len(route_table[index]['cpu_usage_history'])
                        if cpu_usage_avg >= cpu_limit * 0.8:
                            route_table[index]['cpu_status'] = 'busy'
                            # change node status node
                            if route_table[index]['node_id'] not in busy_nodes_set:
                                busy_nodes_set.append(route_table[index]['node_id'])
                            if route_table[index]['node_id'] in idle_nodes_set:
                                idle_nodes_set.remove(route_table[index]['node_id'])
                            if route_table[index]['node_id'] in load_nodes_set:
                                load_nodes_set.remove(route_table[index]['node_id'])
                        elif cpu_usage_avg <= cpu_limit * 0.2:
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
            print(len(busy_nodes_set) >= len(active_nodes_set))
            if len(busy_nodes_set) >= len(active_nodes_set) and enable_hs_up:
                enable_hs_up -= 1
                enable_hs_down += 1
                hs(route_table, "up")
                print("Horizontal scaling")

            print(len(idle_nodes_set) >= len(active_nodes_set))
            # hs down
            if len(idle_nodes_set) >= len(active_nodes_set) and enable_hs_down:
                enable_hs_down -= 1
                enable_hs_up += 1
                node_id = hs(route_table, "down")
                if node_id in active_nodes_set:
                    active_nodes_set.remove(node_id)
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
        print("495", e)
        errLog.exception(e)
        exit(1)

if __name__ == "__main__":
    req_count = 0
    cpu_limit = 1
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

    