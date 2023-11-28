import docker
import time
import asyncio
import multiprocessing
import subprocess
import threading

def get_cpu_usage(cpu_usage_stats, lock, ip, node):
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
        print(f"Node {node.id} Container {container['Names']} MEM Usage is {memory_usage: .2f} MiB / {memory_limit: .2f} GiB")

        print(cpu_usage_stats)

        with lock:
            # Update cpu usage for special node
            for stats in cpu_usage_stats:
                stats['cm'] += 1
                if stats['node_id'] == node.id:
                    stats['cpu_usage'] = cpu_percent

    if hs_up_check(cpu_usage_stats, 0.4):
        pass

    if hs_down_check(cpu_usage_stats, 0.2):
        pass



def hs_up(cpu_usage_stats):
    # for getting node id
    for s in cpu_usage_stats:
        hs_command = f"sudo docker node update --availability active {s['node']}"



def hs_down_check(cpu_usage_stats: list, hs_under_limit_cpu_usage: float):
    pass

def hs_up_check(cpu_usage_stats: list, hs_over_limit_cpu_usage: float):
    flag = 1
    for stats in cpu_usage_stats:
        if stats['cpu_usage'] >= hs_over_limit_cpu_usage:
            flag &= 1
        else:
            flag &= 0

    return flag


def main():
    port = 2375
    swarm_client = docker.DockerClient(base_url=f'tcp://192.168.56.107:{port}')
    swarm_nodes = swarm_client.nodes.list()
    with multiprocessing.Pool(processes=len(swarm_nodes)-1) as pool, multiprocessing.Manager() as manager:
        cpu_usage_stats = manager.list()
        lock = manager.Lock()
        for node in swarm_nodes:
            if node.attrs['Spec']['Role'] == 'worker':
                cpu_usage_stats.append({
                    "node_id": node.id,
                    "cpu_usage": 0,
                    "availability": node.attrs['Spec']['Availability'],      # get availability for choosing drain node to HS
                    "cm": 0     # fot test
                })
        
        try:
            while True:
                for node in swarm_nodes:
                    if node.attrs['Spec']['Role'] == 'worker':
                        pool.apply_async(get_cpu_usage, (cpu_usage_stats, lock, node.attrs['Status']['Addr'], node))
        except KeyboardInterrupt:
            pool.terminate()


if __name__ == "__main__":
    main()