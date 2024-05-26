#! /bin/bash

SERVICE_NAME="node-service"
IMAGE="soar009/node-service-image"
TAG="v3"
REPLICAS=$(sudo docker node ls --filter "role=worker" | grep -c "Ready")
CPU_LIMIT=2
MODE="global"

sudo docker service create --name $SERVICE_NAME --publish 8080:8080 --replicas $REPLICAS --limit-cpu $CPU_LIMIT --replicas-max-per-node 1 --constraint "node.role==worker" $IMAGE:$TAG
# sudo docker service create --name "$SERVICE_NAME" -p 8080:8080 --limit-cpu "$CPU_LIMIT" --mode "$MODE" --constraint "node.role==worker" "$IMAGE"

# sudo docker node ls --filter "role=worker" -q | sudo wc -l




