import docker

client = docker.APIClient(base_url=f"tcp://10.0.2.7:2375")

df = client.df()

# services = client.services.get('node-service')

for key in df.keys():
    print(df['LayersSize'] / (5 * pow(2, 30)))

# service = client.services.get('node-service')

# tasks = services.tasks()


# for task in tasks:
#     if task['DesiredState'] == "running":
#         container_id = task['Status']['ContainerStatus']['ContainerID']
#         node_id = task["NodeID"]
#         print(node_id)
#         break

# for node in client.nodes.list():
#     if node.id == node_id:
#         node_ip = node.attrs["Status"]['Addr']
#         node_client = docker.DockerClient(f"http://{node_ip}:2375")
#         stats = node_client.containers.get(container_id).stats(stream=False)
#         for key in stats.keys():
#             print(f"{key} => {stats[key]}")
        # print(stats['storage']['read'])
        # print(stats['storage']['total'])
        # print( node.client.containers.get(container_id) )