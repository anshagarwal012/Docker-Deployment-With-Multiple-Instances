docker stack rm ecommerce_stack
sleep 5
python3 docker__file_generate.py
docker stack deploy -c docker-stack.yml ecommerce_stack