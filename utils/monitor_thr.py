import docker
import time
import asyncio
import multiprocessing
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

def get_cpu_usage(cpu_usage_stats, lock, ip, node):
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

            print(f"Node {node.id} Container {container['Names']} CPU Percent is {cpu_percent: .2f} %")
            # print(f"Node {node.id} Container {container['Names']} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")

            with lock:
                # Update cpu usage for special node
                for stats in cpu_usage_stats:
                    if stats['node_id'] == node.id:
                        stats['cpu_usage'] = cpu_percent
                    stats['cm'] += 1
        

        # horizontal scaling scheduler   
        hs_scheduler(cpu_usage_stats, lock)
    
    except Exception as e:
        print("Error")
        print(e)
    

def hs(cpu_usage_stats, _class, lock):
    # for getting node id
    print("HS RUNNING...")
    password = '123321'
    if _class == 'up':
        for s in cpu_usage_stats:
            if s['availability'] == 'drain' and s['state'] == 'ready':
                print("HS UP")
                hs_active_command = f"echo '{password}' | sudo -S docker node update --availability active {s['node_id']}"
                with lock:
                    s['availability'] = 'active'
                
                # scaling
                subprocess.Popen(hs_active_command, shell=True)
        

    elif _class == 'down':
        for s in cpu_usage_stats:
            if s['availability'] == 'drain' and s['state'] == 'ready':
                print("HS DOWN")
                hs_drain_command = f"echo '{password}' | sudo -S docker node update --availability drain {s['node_id']}"

                with lock:
                    s['availability'] = 'drain'
                
                # scaling
                subprocess.Popen(hs_drain_command, shell=True)
        
    else:
        exit(1)        



def hs_scheduler(cpu_usage_stats, lock):
    temp_stats = cpu_usage_stats
    print(cpu_usage_stats)
    if hs_up_check(temp_stats, 40):
        print("Up")
        hs(cpu_usage_stats, "up", lock)
    elif hs_down_check(temp_stats, 20):
        print("Down")
        hs(cpu_usage_stats, "down", lock)
    else:
        print("No")
        pass

def hs_down_check(cpu_usage_stats: list, hs_under_limit_cpu_usage: float):
    flag = 1
    for stats in cpu_usage_stats:
        if stats['cpu_usage'] < hs_under_limit_cpu_usage and stats['availability'] == 'active' and stats['state'] == 'ready':
            flag &= 1
        else:
            flag &= 0

    return flag

def hs_up_check(cpu_usage_stats: list, hs_over_limit_cpu_usage: float):
    flag = 1
    for stats in cpu_usage_stats:
        if stats['cpu_usage'] >= hs_over_limit_cpu_usage and stats['availability'] == 'active' and stats['state'] == 'ready':
            flag &= 1
        else:
            flag &= 0

    return flag


def main():
    port = 2375
    manager_ip = '192.168.56.107'
    swarm_client = docker.DockerClient(base_url=f'tcp://{manager_ip}:{port}')
    swarm_nodes = swarm_client.nodes.list()
    with ThreadPoolExecutor(max_workers = len(swarm_nodes) + 1) as pool:
        
        # declare
        cpu_usage_stats = list()
        lock = threading.Lock()
        arguments = list()

        # initialize lists
        for node in swarm_nodes:
            if node.attrs['Spec']['Role'] == 'worker':
                cpu_usage_stats.append({
                    "node_id": node.id,
                    "cpu_usage": 0,
                    "availability": node.attrs['Spec']['Availability'],      # get availability for choosing drain node to HS
                    "state": node.attrs['Status']['State'],
                    "cm": 0
                })
                arguments.append(lock, node.attrs['Status']['Addr'], node)

        # run thread pool
        try:
            while True:
                futures = list()
                for node in swarm_nodes:
                    f = pool.submit(get_cpu_usage(cpu_usage_stats, lock, node.attrs['Status']['Addr'], node))
                    futures.append(f)
                concurrent.futures.wait(futures)

                f = pool.submit(hs_scheduler())
                concurrent.futures.wait(f)

        except KeyboardInterrupt:
            pool.terminate()


if __name__ == "__main__":
    main()