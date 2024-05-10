# test demo

import docker
import concurrent.futures

import logging


if __name__ == "__main__":
    manager_client = docker.APIClient(base_url="unix://var/run/docker.sock")
    nodes = manager_client.nodes(filters={"role": "worker"})

    logger = logging.getLogger('cpu log')
    logger.setLevel(level=logging.INFO)
    loggerHandler = logging.FileHandler('./logs/cpu_usage.log')
    logger.addHandler(loggerHandler)

    for node in nodes:
        node_ip = node['Status']['Addr']
        node_client = docker.APIClient(base_url=f'tcp://{node_ip}:2375')
        containers = node_client.containers()
        containers_stats_list = list()
        for container in containers:
            containers_stats_list.append(node_client.stats(container, stream=True, decode=True))
        
        for stats_obj in containers_stats_list:
            for stats in stats_obj:
                precpustats = stats['precpu_stats']
                cpustats = stats['cpu_stats']
                if 'system_cpu_usage' in precpustats and 'system_cpu_usage' in cpustats:
                    usage = (cpustats['cpu_usage']['usage_in_usermode'] - precpustats['cpu_usage']['usage_in_usermode']) / (cpustats['system_cpu_usage'] - precpustats['system_cpu_usage'])
                    
                    logger.info(round(usage * 100, 2))
                    
                else:
                    logger.info("---")