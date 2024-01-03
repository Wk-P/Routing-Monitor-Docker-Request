import aiohttp
from aiohttp import web
import asyncio
import docker
import time
import subprocess
import logging
import multiprocessing
import threading
import requests
import json


def get_cpu_usage(cpu_usage_stats, ip, node, log):
    try:
        if node.attrs["Status"]["State"] != "ready":
            return None

        client = docker.api.APIClient(base_url=f"tcp://{ip}:2375")
        for container in client.containers():
            stats = client.stats(container["Id"], stream=False)

            pre_cpu_stats = stats["precpu_stats"]
            cpu_stats = stats["cpu_stats"]

            cpu_usage = cpu_stats["cpu_usage"]
            # print(cpu_usage)
            pre_cpu_usage = pre_cpu_stats["cpu_usage"]

            system_cpu_usage = cpu_stats["system_cpu_usage"]
            online_cpus = cpu_stats["online_cpus"]

            # calculate
            cpu_delta = cpu_usage["total_usage"] - pre_cpu_usage["total_usage"]
            system_delta = system_cpu_usage - pre_cpu_stats["system_cpu_usage"]

            # cpu_percent = 0.0
            if system_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

            # memory stats
            memory_stats = stats["memory_stats"]
            memory_usage = memory_stats["usage"] / 1024 / 1024
            memory_limit = memory_stats["limit"] / 1024 / 1024 / 1024

            log.info(
                f"Hostname {node.attrs['Description']['Hostname']} Node {node.id} Container {container['Names']} CPU Percent is {cpu_percent: .2f} %"
            )
            # print(f"Node {node.id} Container {container['Names']} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")

            # cpu_usage_stats: list = q.get()
            # Update cpu usage for special node
            for stats in cpu_usage_stats:
                if stats["node_id"] == node.id:
                    stats["cpu_usage"] = cpu_percent
            # q.put(cpu_usage_stats)

        # horizontal scaling scheduler
        # hs_scheduler(cpu_usage_stats)

    except Exception as e:
        print("Error in get_cpu_usage")
        print(e)

    return cpu_usage_stats


def hs(rout_table, _class):
    # for getting node id
    print("HS RUNNING...")
    password = "123321"

    # cpu_usage_stats = q.get()
    if _class == "up":
        for s in rout_table:
            if s["availability"] == "drain" and s["state"] == "ready":
                hs_active_command = f"echo '{password}' | sudo -S docker node update --availability active {s['node_id']}"

                # scaling
                process = subprocess.Popen(
                    hs_active_command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                print("UP")

                time.sleep(3)
                process.wait()
                print(f"return code: {process.returncode}")
                if process.returncode == 0:
                    s["availability"] = "active"

                return

    elif _class == "down":
        active_num = 0
        for node in rout_table:
            if node["availability"] == "active" and node["state"] == "ready":
                active_num += 1

        print(active_num)
        if active_num > 1:
            for s in rout_table:
                if s["availability"] == "active" and s["state"] == "ready":
                    hs_drain_command = f"echo '{password}' | sudo -S docker node update --availability drain {s['node_id']}"
                    s["availability"] = "drain"
                    time.sleep(3)

                    process = subprocess.Popen(
                        hs_drain_command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    process.wait()
                    print(process.returncode)
                    # scaling
                    if process.returncode == 0:
                        print("DOWN")
                    return

    else:
        print("Error in HS")

        return
    # q.put_nowait(cpu_usage_stats)


def hs_scheduler(cpu_usage_stats: list):
    if hs_up_check(cpu_usage_stats, 40):
        hs(cpu_usage_stats, "up")
    elif hs_down_check(cpu_usage_stats, 0):
        hs(cpu_usage_stats, "down")
        time.sleep(2)
    else:
        pass


def hs_down_check(cpu_usage_stats: list, hs_under_limit_cpu_usage: float):
    flag = 0
    cm = 0  # last one container can not be remove
    count = 0

    # if hs count will equal to flag

    for stats in cpu_usage_stats:
        if stats["availability"] == "active" and stats["state"] == "ready":
            cm += 1

    if cm <= 1:
        return 0

    for stats in cpu_usage_stats:
        if stats["availability"] == "active" and stats["state"] == "ready":
            count += 1
            if stats["cpu_usage"] <= hs_under_limit_cpu_usage:
                flag += 1
    # q.put_nowait(cpu_usage_stats)
    if flag == count:
        return 1
    return 0


def hs_up_check(cpu_usage_stats: list, hs_over_limit_cpu_usage: float):
    flag = 0
    # cpu_usage_stats = q.get()
    count = 0

    # if hs count will equal to flag

    for stats in cpu_usage_stats:
        if stats["availability"] == "active" and stats["state"] == "ready":
            count += 1
            if stats["cpu_usage"] > hs_over_limit_cpu_usage:
                flag += 1
    # q.put_nowait(cpu_usage_stats)
    if flag == count:
        return 1
    return 0


def init_route_table():
    port = 2375
    manager_ip = "192.168.56.107"
    swarm_client = docker.DockerClient(base_url=f"tcp://{manager_ip}:{port}")
    swarm_nodes = swarm_client.nodes.list()
    cpu_usage_stats = list()
    container_port = 8080
    # declare

    # initialize lists
    for node in swarm_nodes:
        if node.attrs["Spec"]["Role"] == "worker":
            cpu_usage_stats.append(
                {
                    "node_id": node.id,
                    "name": node.attrs["Description"]["Hostname"],
                    "times": {
                        "prev_total": 0,
                        "prev_user": 0,
                        "prev_sys": 0,
                    },
                    "cpu_usage": 0,
                    "availability": node.attrs["Spec"][
                        "Availability"
                    ],  # get availability for choosing drain node to HS
                    "state": node.attrs["Status"]["State"],
                    "address": node.attrs["Status"]["Addr"],
                    "port": container_port,
                    "node_object": node,
                }
            )
    return cpu_usage_stats


def monitor_main():
    global route_table
    try:
        print("Start Monitoring...")

        handler = logging.FileHandler(filename="logs/hs-log.log")
        monitor_log = logging.Logger(name="monitor", level=logging.INFO)
        monitor_log.addHandler(handler)

        while True:
            for stats in route_table:
                get_cpu_usage(
                    route_table,
                    ip=stats["address"],
                    node=stats["node_object"],
                    log=monitor_log,
                )

            monitor_log.info("--------------------------")
            hs_scheduler(route_table)
    except:
        print("Error in monitor main function")


# declare an async function for send request
async def req_post_task(
    session: aiohttp.ClientSession,
    url,
    method,
    request: aiohttp.ClientRequest,
    request_data,
    cpu_limit,
):
    if method == "HEAD":
        # send request to others' servers
        async with session.head(
            url=url,
        ) as response:
            # get headers

            headers = response.headers
            mem = headers.get("mem")
            cpuUsage = float(headers.get("data"))

            response = {
                "data": {"cpuUsage": cpuUsage * cpu_limit, "mem": mem},
                "server": url,
            }

            # add to list for update route_table
            # for stats in route_table:
            #     if stats['address'] == url:
            #         stats['cpuUsage'] = cpuUsage * cpu_limit

    # Now Just Head
    elif method == "POST":
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


async def send_head_request():
    global cpu_limit
    global route_table

    handler = logging.FileHandler(filename="logs/hs-log.log", mode="w")
    monitor_log = logging.Logger(name="monitor", level=logging.INFO)
    monitor_log.addHandler(handler)

    hs_up_time_count = 0
    hs_down_time_count = 0
    enable_hs_up = 0
    enable_hs_down = -1
    for node in route_table:
        if node["state"] == "ready" and node["availability"] == "drain":
            enable_hs_up += 1
        elif node["state"] == "ready" and node["availability"] == "active":
            enable_hs_down += 1

    log_time = 0
    while True:
        print("-------------")
        for node in route_table:
            if node["state"] == "ready" and node["availability"] == "active":
                with requests.head(
                    url=f"http://{node['address']}:{node['port']}"
                ) as response:
                    headers = response.headers
                    mem = headers.get("mem")
                    cpus_dict = json.loads(headers.get("data"))

                    print(cpus_dict)

                    current_total = 0
                    current_user = 0
                    current_sys = 0

                    for cpu in cpus_dict:
                        current_total += (
                            cpu["times"]["user"]
                            + cpu["times"]["sys"]
                            + cpu["times"]["idle"]
                        )
                        current_user += cpu["times"]["user"]
                        current_sys += cpu["times"]["sys"]

                    prev_total = node["times"]["prev_total"]
                    prev_user = node["times"]["prev_user"]
                    prev_sys = node["times"]["prev_sys"]

                    # test
                    print(f"df total : {current_total - prev_total}")
                    print(
                        f"df su    : {((current_sys - prev_sys) + (current_user - prev_user))}"
                    )
                    print(f"df sys   : {current_sys - prev_sys}")
                    print(f"df user  : {current_user - prev_user}")
                    # cpus data
                    diff_t = current_total - prev_total
                    diff_su = (current_sys - prev_sys) + (current_user - prev_user)
                    userRate = diff_su / diff_t

                    if current_total > prev_total:
                        cpu_percent = min(userRate / cpu_limit, cpu_limit)
                    else:
                        cpu_percent = node["cpu_usage"]

                    monitor_log.info(
                        f"{log_time}:{node['name']}:{cpu_percent*100:.4f}%"
                    )

                    if cpu_percent >= 0:
                        node["cpu_usage"] = cpu_percent
                        node["times"]["prev_total"] = current_total
                        node["times"]["prev_user"] = current_user
                        node["times"]["prev_sys"] = current_sys
                        print(f"{cpu_percent * 100:.4f}%")
                    else:
                        print(node["times"]["prev_total"])
                    response = {
                        "data": {
                            # 'cpuUsage': cpuUsage,
                            "mem": mem
                        },
                        "server": node["address"],
                    }

                    # HS when cpu usages of cpus over 80% of cpu limit in 3 seconds
        log_time += 1

        for node in route_table:
            if node["state"] == "ready" and node["availability"] == "active":
                if node["cpu_usage"] > 0.8 * cpu_limit:
                    hs_up_time_count += 1
                    hs_down_time_count -= 1

                if node["cpu_usage"] < 0.2 * cpu_limit:
                    hs_down_time_count += 1
                    hs_up_time_count -= 1

        # hs up
        if hs_up_time_count > 3 * enable_hs_down and enable_hs_up > 0:
            hs_up_time_count = 0
            hs(route_table, "up")
            enable_hs_up -= 1
            enable_hs_down += 1

        # hs down
        if hs_down_time_count > 3 * enable_hs_up and enable_hs_down > 0:
            hs_down_time_count = 0
            hs(route_table, "down")
            enable_hs_up += 1
            enable_hs_down -= 1

        # get cpu usage interval
        await asyncio.sleep(1)


# For changing by cpu usage, first time is random, next is to cpuUsage min
async def handle_request(request: aiohttp.ClientRequest):
    global route_table
    global req_count

    # temp_rt: list = route_table
    server_url = None
    cpu_limit = 0.5

    # if syncQueue.qsize() < 1:
    # return web.json_response({"Error": "Queue Empty"})

    # rt = await syncQueue.get()
    # if len(route_table) < 1:
    # return web.json_response({"Error": "Route Table Empty"})
    min_usage = 2
    for stats in route_table:
        # print(f"{stats['address']} : {stats['cpu_usage']}")
        if stats["state"] == "ready" and stats["availability"] == "active":
            if float(stats["cpu_usage"]) <= min_usage:
                server_url = stats["address"]
                min_usage = stats["cpu_usage"]

    # await syncQueue.put(route_table)

    request_data = await request.json()

    tasks = []

    # rt = await syncQueue.get()
    # send request to first server
    async with aiohttp.ClientSession() as session:
        for stats in route_table:
            if stats["state"] == "ready" and stats["availability"] == "active":
                if server_url == stats["address"]:
                    tasks.append(
                        asyncio.create_task(
                            req_post_task(
                                session,
                                f"http://{stats['address']}:{stats['port']}",
                                "POST",
                                request,
                                request_data,
                                cpu_limit,
                            )
                        )
                    )
                # else:
                # tasks.append(asyncio.create_task(req_task(session, f"http://{stats['address']}:{stats['port']}", "HEAD", request, request_data, cpu_limit)))

        responses = await asyncio.gather(*tasks)

    # Here update route_table
    # await syncQueue.put(rt)
    return web.json_response(responses)


if __name__ == "__main__":
    req_count = 0
    cpu_limit = 0.5
    try:
        route_table = init_route_table()
        main_loop = asyncio.new_event_loop()

        task = main_loop.create_task(send_head_request())
        asyncio.gather(task)

        app = web.Application()
        app.router.add_post("/", handle_request)
        # app['send_head_request'] = asyncio.ensure_future(send_head_request())

        web.run_app(app=app, host="192.168.56.107", port=8080, loop=main_loop)

        # monitor_process = multiprocessing.Process(target=monitor_main)
        # monitor_process.start()

        # monitor_threading = threading.Thread(target=monitor_main)
        # monitor_threading.start()

    except asyncio.CancelledError:
        pass
    finally:
        # monitor_process.join()
        # monitor_threading.join()
        # app.shutdown()
        pass
