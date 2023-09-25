import docker, time, json

# get address
def get_all_worker_node_address(nodes):
    nodes_info_pool = []
    for node in nodes:
        if node.attrs['Spec']['Role'] == "worker":
            # test
            print(f"{node.attrs['Description']['Hostname']}: {node.attrs['Status']['Addr']}")

            ip = node.attrs['Status']['Addr']
            port = 2375

            node_info = {
                "name": node.attrs['Description']['Hostname'],
                "address": f'{ip}:{port}'
            }

            nodes_info_pool.append(node_info)

    return nodes_info_pool



# get client
def get_all_nodes_client(nodes_info):

    for node in nodes_info:
        node["client"] = docker.DockerClient(base_url=f"tcp://{node['address']}")

    return nodes_info


# find container by node_name and service name
def get_container_of_service(nodes_info, service_name):
    for node in nodes_info:
        node['containers'] = list()
        containers = node['client'].containers.list()

        # get the container we want
        
        for c in containers:
            container_name = c.name
            if container_name.split('.')[0] == service_name:
                try:
                    # add container object in nodes_info
                    node['containers'].append(c)
                except:
                    print(c)
                    exit(1)
    return None




# def update_data(client, container, manager_client, service_name, scaled):
def monitor_node(nodes_info):
    resources = []
    cpu_percent_limit = 5
    for node in nodes_info:
        client = node['client']

        for container in node['containers']:
            # get CPU stats data
            stats_data = client.containers.get(container.id).stats(stream=False)

            pre_cpu_stats = stats_data['precpu_stats']
            cpu_stats = stats_data['cpu_stats']

            cpu_usage = cpu_stats['cpu_usage']
            pre_cpu_usage = pre_cpu_stats['cpu_usage']

            system_cpu_usage = cpu_stats['system_cpu_usage']
            online_cpus = cpu_stats['online_cpus']

            # calculate
            cpu_delta = cpu_usage['total_usage'] - pre_cpu_usage['total_usage']
            system_delta = system_cpu_usage - pre_cpu_stats['system_cpu_usage']

            cpu_percent = 0.0
            if system_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100

            print(f"Node {node['name']} Container {container.name.split('.')[0]} CPU Percent is {cpu_percent: .2f} %")
            
            # scale
            if cpu_percent >= cpu_percent_limit:
                # route_table change
                resources.append({'node': node['name'], 'status': 'running', 'request': 'HS'})

    return resources  

def create_monitor():
    default_client = docker.from_env()
    service_name = "node-service"
    nodes = default_client.nodes.list()

    # get node requests url and port (json list : NAME, ADDRESS)
    nodes_info = get_all_worker_node_address(nodes)

    # get client for every node (json list: NAME, ADDRESS, CLIENT)
    nodes_info = get_all_nodes_client(nodes_info)

    get_container_of_service(nodes_info=nodes_info, service_name=service_name)

    return nodes_info

def start_monitor(nodes_info):
   
    while True:
        # print nodes CPU percent
        # get router table change request
        # ret == node name
        yield monitor_node(nodes_info=nodes_info)

if __name__ == "__main__":
    pass