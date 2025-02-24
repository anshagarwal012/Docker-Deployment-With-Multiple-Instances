#!/bin/bash

NETWORK_NAME="my_custom_network"
SUBNET="192.168.100.0/24"
UBUNTU_IMAGE="ubuntu:20.04"

declare -A CONTAINERS
CONTAINERS=(
    ["ubuntu2"]="192.168.100.2"
    ["ubuntu3"]="192.168.100.3"
    ["ubuntu4"]="192.168.100.4"
    ["ubuntu5"]="192.168.100.5"
)

if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
    echo "Creating Docker network..."
    docker network create --subnet=$SUBNET $NETWORK_NAME
else
    echo "Docker network '$NETWORK_NAME' already exists. Skipping creation."
fi

create_container() {
    local NAME=$1
    local IP=$2
    echo "Creating container $NAME with IP $IP..."

    docker run -dit --privileged --name $NAME --network $NETWORK_NAME --ip $IP \
        $UBUNTU_IMAGE bash

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create container $NAME. Skipping..."
    else
        echo "✅ Successfully created $NAME!"
    fi
}

for NAME in "${!CONTAINERS[@]}"; do
    create_container "$NAME" "${CONTAINERS[$NAME]}"
done

echo "✅ All Ubuntu containers created!"

install_docker_inside_container() {
    local NAME=$1
    echo "Installing Docker inside $NAME..."

    docker exec -it $NAME bash -c "
    export DEBIAN_FRONTEND=noninteractive &&
    apt-get update &&
    apt-get install -y ca-certificates curl gnupg lsb-release iputils-ping net-tools &&
    mkdir -p /etc/apt/keyrings &&
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc &&
    chmod a+r /etc/apt/keyrings/docker.asc &&
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&
    apt-get update &&
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin &&
    service docker start
    "

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Docker inside $NAME. Skipping..."
    else
        echo "✅ Docker installed inside $NAME!"
    fi
}

for NAME in "${!CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^$NAME\$"; then
        install_docker_inside_container "$NAME"
    else
        echo "⚠️ Container $NAME does not exist. Skipping Docker installation."
    fi
done

echo "✅ Docker installation process completed!"
docker ps
