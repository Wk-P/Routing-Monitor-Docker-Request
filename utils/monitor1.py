import docker
import time
import asyncio
import multiprocessing

def get_cpu_usage(ip, node):
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

        print(time.strftime("%X"))

def main():
    port = 2375
    swarm_client = docker.DockerClient(base_url=f'tcp://192.168.56.104:{port}')
    swarm_nodes = swarm_client.nodes.list()
    print(time.strftime("%X"))
    with multiprocessing.Pool(processes=len(swarm_nodes)) as pool:
        try:
            while True:
                for node in swarm_nodes:
                    if node.attrs['Spec']['Role'] == 'worker':
                        pool.apply_async(get_cpu_usage, (node.attrs['Status']['Addr'], node))
        except KeyboardInterrupt:\
            pool.terminate()


if __name__ == "__main__":
    main()