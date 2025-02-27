import os
import subprocess

# Your provided configuration
domains = [
    "allairx.com", "example2.com", "example3.com", "example4.com",
    "example5.com", "example6.com", "example7.com", "example8.com",
    "example9.com", "example10.com", "example11.com", "example12.com",
    "example13.com", "example14.com", "example15.com", "example16.com",
    "example17.com", "example18.com", "example19.com", "example20.com"
]

servers = ["147.93.104.239", "82.29.164.50", "82.29.164.51", "82.29.164.52"]
laravel_image = "masteransh/laravel-ecommerce-prateek:3"

def is_ip(domain):
    return all(part.isdigit() for part in domain.split('.'))

def generate_ssl():
    ssl_dir = "ssl"
    os.makedirs(ssl_dir, exist_ok=True)
    
    for domain in domains:
        if not is_ip(domain):
            cert_file = os.path.join(ssl_dir, f"{domain}.crt")
            key_file = os.path.join(ssl_dir, f"{domain}.key")
            if not os.path.exists(cert_file):
                print(f"Generating SSL certificate for {domain}...")
                cmd = (f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
                       f"-subj '/CN={domain}' -keyout {key_file} -out {cert_file}")
                subprocess.run(cmd, shell=True, check=True)
            else:
                print(f"SSL certificate for {domain} already exists.")

def generate_nginx_conf():
    nginx_dir = "nginx"
    os.makedirs(nginx_dir, exist_ok=True)
    config_path = os.path.join(nginx_dir, "nginx.conf")
    
    nginx_config = """
worker_processes auto;
events { worker_connections 1024; }
http {
    include mime.types;
    sendfile on;
    keepalive_timeout 65;
"""
    # Create a server block for each domain
    for domain in domains:
        nginx_config += f"""
    server {{
        listen 80;
        listen 443 ssl;
        server_name {domain};
        
        ssl_certificate /etc/nginx/certs/{domain}.crt;
        ssl_certificate_key /etc/nginx/certs/{domain}.key;
        
        location / {{
            proxy_pass http://laravel_app:9000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}
"""
    nginx_config += "\n}"
    with open(config_path, "w") as file:
        file.write(nginx_config)
    print("nginx.conf created successfully.")

def generate_docker_stack():
    # Use your provided laravel_image variable in the service definition
    stack_config = f"""
version: '3.8'

services:
  laravel_app:
    image: {laravel_image}
    deploy:
      replicas: 20
      placement:
        constraints: [node.role == worker]
    environment:
      APP_ENV: production
      DB_CONNECTION: mysql
      DB_HOST: proxysql
      DB_PORT: 6033
      DB_USERNAME: laravel
      DB_PASSWORD: your_password
    networks:
      - laravel_network
    volumes:
      - /var/www/html

  proxysql:
    image: proxysql/proxysql:latest
    networks:
      - laravel_network
    ports:
      - "6032:6032"
      - "6033:6033"
    volumes:
      - ./proxysql/proxysql.cnf:/etc/proxysql.cnf

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    networks:
      - laravel_network
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/certs
    depends_on:
      - laravel_app

  redis:
    image: redis:latest
    networks:
      - laravel_network

  phpmyadmin:
    image: phpmyadmin/phpmyadmin:latest
    environment:
      PMA_HOST: proxysql
      PMA_PORT: 6033
    ports:
      - "8080:80"
    networks:
      - laravel_network
    depends_on:
      - proxysql

networks:
  laravel_network:
    driver: overlay
"""
    with open("docker-stack.yml", "w") as file:
        file.write(stack_config)
    print("docker-stack.yml created successfully.")

def generate_proxysql_config():
    proxysql_dir = "proxysql"
    os.makedirs(proxysql_dir, exist_ok=True)
    config_path = os.path.join(proxysql_dir, "proxysql.cnf")
    
    # Use your servers list to generate mysql_servers entries
    proxysql_config = "[mysql_servers]\n"
    for server in servers:
        proxysql_config += f"{{ address=\"{server}\", port=3306, hostgroup_id=0, max_connections=100 }}\n"
    proxysql_config += "\n[mysql_users]\n"
    proxysql_config += "user = \"laravel\"\n"
    proxysql_config += "password = \"your_password\"\n"
    proxysql_config += "\ndefault_hostgroup = 0\n"
    
    with open(config_path, "w") as file:
        file.write(proxysql_config)
    print("proxysql.cnf created successfully.")

def main():
    generate_ssl()
    generate_nginx_conf()
    generate_docker_stack()
    generate_proxysql_config()
    print("All configuration files created successfully.")

if __name__ == "__main__":
    main()
