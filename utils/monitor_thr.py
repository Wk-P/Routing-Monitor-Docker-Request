import docker
import time
import asyncio
import multiprocessing
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import queue
import logging

logging.basicConfig(filename='logs/hs-log.log', level=logging.INFO)

def get_cpu_usage(q: asyncio.Queue, ip, node):
    try:
        if node.attrs['Status']['State'] != 'ready':
            return None
            
        client = docker.api.APIClient(base_url=f"tcp://{ip}:2375")
        for container in client.containers():
            stats = client.stats(container['Id'], stream=False)

            pre_cpu_stats = stats['precpu_stats']
            cpu_stats = stats['cpu_stats']

            cpu_usage = cpu_stats['cpu_usage']
            # print(cpu_usage)
            pre_cpu_usage = pre_cpu_stats['cpu_usage']

            system_cpu_usage = cpu_stats['system_cpu_usage']
            online_cpus = cpu_stats['online_cpus']

            # calculate
            cpu_delta = cpu_usage['total_usage'] - pre_cpu_usage['total_usage']
            system_delta = system_cpu_usage - pre_cpu_stats['system_cpu_usage']

            cpu_percent = 0.0
            # if system_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * online_cpus * 100


            # memory stats
            memory_stats = stats['memory_stats']
            memory_usage = memory_stats['usage'] / 1024 / 1024
            memory_limit = memory_stats['limit'] / 1024 / 1024 / 1024

            print(f"Hostname {node.attrs['Description']['Hostname']} Node {node.id} Container {container['Names']} CPU Percent is {cpu_percent: .2f} %")
            # print(f"Node {node.id} Container {container['Names']} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")

            cpu_usage_stats: list = q.get()
            # Update cpu usage for special node
            for stats in cpu_usage_stats:
                if stats['node_id'] == node.id:
                    stats['cpu_usage'] = cpu_percent
            q.put(cpu_usage_stats)
        
        # horizontal scaling scheduler
        # hs_scheduler(cpu_usage_stats)
    
    except Exception as e:
        print("Error")
        print(e)
    

def hs(q: asyncio.Queue, _class):
    # for getting node id
    print("HS RUNNING...")
    password = '123321'


    cpu_usage_stats = q.get()
    if _class == 'up':
        for s in cpu_usage_stats:
            if s['availability'] == 'drain' and s['state'] == 'ready':
                hs_active_command = f"echo '{password}' | sudo -S docker node update --availability active {s['node_id']}"
                s['availability'] = 'active'
                
                # scaling
                process = subprocess.Popen(hs_active_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()


    elif _class == 'down':
        active_num = 1
        get_node_num_cmd = f"echo '{password}' | sudo -S docker node ls | wc -l"
        n_process = subprocess.Popen(get_node_num_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, err = n_process.communicate()

        # print(worker_sum)
        if n_process.returncode == 0:
            worker_sum = int(output.strip())
            if active_num >= worker_sum:
                return

        for s in cpu_usage_stats:
            if s['availability'] == 'active' and s['state'] == 'ready':
                hs_drain_command = f"echo '{password}' | sudo -S docker node update --availability drain {s['node_id']}"
                s['availability'] = 'drain'
                
                # scaling
                process = subprocess.Popen(hs_drain_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                time.sleep(0.5)
                return

    else:
        exit(1)        
    q.put(cpu_usage_stats)


def hs_scheduler(q: asyncio.Queue):
    if hs_up_check(q, 40):
        logging.info(f"HS : Up")
        hs(q, "up")
    elif hs_down_check(q, 20):
        logging.info(f"HS : Down")
        hs(q, "down")
    else:
        logging.info(f"HS : no")
        pass

def hs_down_check(q: asyncio.Queue, hs_under_limit_cpu_usage: float):
    flag = 0
    cm = 0 
    cpu_usage_stats = q.get()

    for stats in cpu_usage_stats:
        if stats['availability'] == 'active' and stats['state'] == 'ready':
            cm += 1
    
    if cm <= 1:
        return flag

    for stats in cpu_usage_stats:
        if stats['availability'] == 'active' and stats['state'] == 'ready':
            if stats['cpu_usage'] <= hs_under_limit_cpu_usage:
                flag += 1
            else:
                flag = 0

    q.put(cpu_usage_stats)
    return flag

def hs_up_check(q: asyncio.Queue, hs_over_limit_cpu_usage: float):
    flag = 0
    cpu_usage_stats = q.get()
    for stats in cpu_usage_stats:
        if stats['availability'] == 'active' and stats['state'] == 'ready':
            if stats['cpu_usage'] > hs_over_limit_cpu_usage:
                flag += 1
            else:
                flag = 0
    q.put(cpu_usage_stats)
    return flag


def main(q: asyncio.Queue):
    port = 2375
    manager_ip = '192.168.56.107'
    swarm_client = docker.DockerClient(base_url=f'tcp://{manager_ip}:{port}')
    swarm_nodes = swarm_client.nodes.list()
    with ThreadPoolExecutor(max_workers = len(swarm_nodes) + 1) as pool:
        
        # declare
        route_table: list = q.get()

        # initialize lists
        for node in swarm_nodes:
            if node.attrs['Spec']['Role'] == 'worker':
                route_table.append({
                    "node_id": node.id,
                    'name': node.attrs['Description']['Hostname'],
                    "cpu_usage": 0,
                    "availability": node.attrs['Spec']['Availability'],      # get availability for choosing drain node to HS
                    "state": node.attrs['Status']['State'],
                    "address": node.attrs['Status']['Addr'],
                    'cpuUsage': 0,
                })

        q.put(route_table)
        # run thread pool
        try:
            while True:
                futures = list()
                # get route_table from queue
                for node in swarm_nodes:
                    
                    f = pool.submit(get_cpu_usage(q, node.attrs['Status']['Addr'], node))
                    futures.append(f)
                    

                concurrent.futures.wait(futures)
                
                # put into for router using


                # get for monitor

                f = pool.submit(hs_scheduler(q))
                concurrent.futures.wait([f])
                

        except KeyboardInterrupt:
            pool.terminate()


if __name__ == "__main__":
    pass