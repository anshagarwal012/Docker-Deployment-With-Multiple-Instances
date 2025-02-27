import os, subprocess, yaml

# ---------------------------
# Step 0: Define Domains and Servers
# ---------------------------
domains = [
    {"domain": "147.93.104.239", "db_service": "mysql19", "db_name": "allairx", "db_password": "WireTrip0908@allairx"},
    {"domain": "allairx.com",   "db_service": "mysql20", "db_name": "allairx", "db_password": "WireTrip0908@allairx"},
    # {"domain": "site1.com",     "db_service": "mysql1",  "db_name": "db_site1", "db_password": "pass1"},
    # {"domain": "site2.com",     "db_service": "mysql2",  "db_name": "db_site2", "db_password": "pass2"},
    # {"domain": "site3.com",     "db_service": "mysql3",  "db_name": "db_site3", "db_password": "pass3"},
    # {"domain": "site4.com",     "db_service": "mysql4",  "db_name": "db_site4", "db_password": "pass4"},
    # {"domain": "site5.com",     "db_service": "mysql5",  "db_name": "db_site5", "db_password": "pass5"},
    # {"domain": "site6.com",     "db_service": "mysql6",  "db_name": "db_site6", "db_password": "pass6"},
    # {"domain": "site7.com",     "db_service": "mysql7",  "db_name": "db_site7", "db_password": "pass7"},
    # {"domain": "site8.com",     "db_service": "mysql8",  "db_name": "db_site8", "db_password": "pass8"},
    # {"domain": "site9.com",     "db_service": "mysql9",  "db_name": "db_site9", "db_password": "pass9"},
    # {"domain": "site10.com",    "db_service": "mysql10", "db_name": "db_site10", "db_password": "pass10"},
    # {"domain": "site11.com",    "db_service": "mysql11", "db_name": "db_site11", "db_password": "pass11"},
    # {"domain": "site12.com",    "db_service": "mysql12", "db_name": "db_site12", "db_password": "pass12"},
    # {"domain": "site13.com",    "db_service": "mysql13", "db_name": "db_site13", "db_password": "pass13"},
    # {"domain": "site14.com",    "db_service": "mysql14", "db_name": "db_site14", "db_password": "pass14"},
    # {"domain": "site15.com",    "db_service": "mysql15", "db_name": "db_site15", "db_password": "pass15"},
    # {"domain": "site16.com",    "db_service": "mysql16", "db_name": "db_site16", "db_password": "pass16"},
    # {"domain": "site17.com",    "db_service": "mysql17", "db_name": "db_site17", "db_password": "pass17"},
    # {"domain": "site18.com",    "db_service": "mysql18", "db_name": "db_site18", "db_password": "pass18"}
]
# Mapping of server numbers to node labels for placement constraints
servers = {1: "server1", 2: "server2", 3: "server3", 4: "server4"}
mysql_root_password = "Devilansh@123"

# ---------------------------
# Step 1: Generate SSL Certificates
# ---------------------------
def is_ip(domain):
    try:
        parts = domain.split('.')
        return all(part.isdigit() for part in parts)
    except Exception:
        return False

ssl_dir = "./ssl"
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)

for item in domains:
    d = item["domain"]
    if not is_ip(d):
        cert_file = os.path.join(ssl_dir, f"{d}.crt")
        key_file = os.path.join(ssl_dir, f"{d}.key")
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            print(f"Generating SSL certificate for {d}...")
            cmd = f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj '/CN={d}' -keyout {key_file} -out {cert_file}"
            subprocess.run(cmd, shell=True, check=True)
        else:
            print(f"Certificate for {d} already exists.")

# ---------------------------
# Step 2: Group Domains for MySQL (4 instances)
# ---------------------------
mysql_groups = {1: [], 2: [], 3: [], 4: []}
for idx, item in enumerate(domains, start=1):
    group = ((idx - 1) % 4) + 1
    mysql_groups[group].append(item)

# Generate an init SQL file for each MySQL instance
for group, items in mysql_groups.items():
    filename = f"init-mysql{group}.sql"
    sql_content = ""
    for item in items:
        # Create the database using the db_name (assumed unique)
        db_name = item["db_name"]
        sql_content += f"CREATE DATABASE IF NOT EXISTS {db_name};\n"
    with open(filename, "w") as f:
        f.write(sql_content)
    print(f"{filename} generated successfully.")

# ---------------------------
# Step 3: Generate Docker Stack File (docker-stack.yml) with Docker Configs
# ---------------------------
stack = {
    "version": "3.8",
    "networks": {
        "internal_net": {
            "driver": "overlay"
        }
    },
    "services": {},
    "volumes": {},
    "configs": {}
}

# Generate content for proxysql.cnf
# Generate proxysql_config_content with dynamic mysql_users
proxysql_config_content = (
    'datadir="/var/lib/proxysql"\n\n'
    'admin_variables =\n'
    '{\n'
    '    admin_credentials="admin:admin"\n'
    '    mysql_ifaces="0.0.0.0:6032"\n'
    '}\n\n'
    'mysql_variables =\n'
    '{\n'
    '    threads=4\n'
    '}\n\n'
    'mysql_servers =\n'
    '(\n'
)
for i in range(1, 5):
    proxysql_config_content += f'    {{ address="mysql{i}", port=3306, hostgroup_id=0, max_connections=100 }},\n'
proxysql_config_content += ')\n\n'

# Dynamically generate mysql_users section based on unique (db_name, db_password) pairs
user_dict = {}
for item in domains:
    uname = item["db_name"]
    upass = item["db_password"]
    user_dict[uname] = upass  # this ensures uniqueness

proxysql_config_content += 'mysql_users =\n(\n'
for uname, upass in user_dict.items():
    proxysql_config_content += f'    {{ username="{uname}", password="{upass}", default_hostgroup=0, transaction_persistent=false }},\n'
# Remove the trailing comma and newline, then close the block
proxysql_config_content = proxysql_config_content.rstrip(",\n") + "\n)\n\n"

proxysql_config_content += 'mysql_query_rules =\n(\n'
proxysql_config_content += '    { rule_id=1, active=1, match_pattern="^SELECT", destination_hostgroup=1, apply=1 },\n'
proxysql_config_content += '    { rule_id=2, active=1, match_pattern=".*", destination_hostgroup=0, apply=1 }\n'
proxysql_config_content += ')\n'


# Generate content for nginx.conf
nginx_config_content = (
    "worker_processes auto;\n"
    "events { worker_connections 1024; }\n"
    "http {\n"
    "    include /etc/nginx/mime.types;\n"
    "    sendfile on;\n"
    "    keepalive_timeout 65;\n"
    "\n"
    "    upstream app_servers {\n"
    "        server app:9000;\n"
    "    }\n"
)
for item in domains:
    d = item["domain"]
    if any(part.isalpha() for part in d.split('.')):
        nginx_config_content += (
            f"    server {{\n"
            f"        listen 80;\n"
            f"        server_name {d} www.{d};\n"
            f"        return 301 https://$host$request_uri;\n"
            f"    }}\n"
            f"    server {{\n"
            f"        listen 443 ssl;\n"
            f"        server_name {d} www.{d};\n"
            f"        ssl_certificate /etc/nginx/ssl/{d}.crt;\n"
            f"        ssl_certificate_key /etc/nginx/ssl/{d}.key;\n"
            f"        root /var/www/html/public;\n"
            f"        index index.php index.html;\n"
            f"        location / {{\n"
            f"            try_files $uri $uri/ /index.php?$query_string;\n"
            f"        }}\n"
            f"        location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{\n"
            f"            try_files $uri =404;\n"
            f"            expires max;\n"
            f"            log_not_found off;\n"
            f"            access_log off;\n"
            f"        }}\n"
            f"        location ~ \\.php$ {{\n"
            f"            include fastcgi_params;\n"
            f"            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n"
            f"            fastcgi_pass app_servers;\n"
            f"        }}\n"
            f"        error_page 404 /index.php;\n"
            f"    }}\n"
        )
    else:
        nginx_config_content += (
            f"    server {{\n"
            f"        listen 80;\n"
            f"        server_name {d};\n"
            f"        root /var/www/html/public;\n"
            f"        index index.php index.html;\n"
            f"        location / {{\n"
            f"            try_files $uri $uri/ /index.php?$query_string;\n"
            f"        }}\n"
            f"        location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{\n"
            f"            try_files $uri =404;\n"
            f"            expires max;\n"
            f"            log_not_found off;\n"
            f"            access_log off;\n"
            f"        }}\n"
            f"        location ~ \\.php$ {{\n"
            f"            include fastcgi_params;\n"
            f"            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n"
            f"            fastcgi_pass app_servers;\n"
            f"        }}\n"
            f"        error_page 404 /index.php;\n"
            f"    }}\n"
        )
nginx_config_content += "}\n"

# Add Docker configs to the stack
stack["configs"]["proxysql_config"] = {
    "file": "./proxysql.cnf"
}
stack["configs"]["nginx_conf"] = {
    "file": "./nginx.conf"
}

# Define the Laravel application service with network alias "app"
stack["services"]["app"] = {
    "image": "masteransh/laravel-ecommerce-prateek:3",
    "networks": {
        "internal_net": {
            "aliases": ["app"]
        }
    },
    "deploy": {
        "replicas": 4,
        "update_config": {
            "parallelism": 2,
            "delay": "10s"
        },
        "restart_policy": {
            "condition": "any"
        }
    },
    "environment": [
        "APP_ENV=production",
        "APP_DEBUG=false",
        "REDIS_HOST=redis",
        "REDIS_PORT=6379"
    ],
    "expose": ["9000"],
    "volumes": ["laravel_code:/var/www/html"]
}

# Create 4 MySQL services (one per group) with init SQL file mounts
for i in range(1, 5):
    service_name = f"mysql{i}"
    stack["services"][service_name] = {
        "image": "mysql:8.0",
        "environment": {
            "MYSQL_ROOT_PASSWORD": mysql_root_password
        },
        "volumes": [
            f"{service_name}_data:/var/lib/mysql",
            # f"./init-mysql{i}.sql:/docker-entrypoint-initdb.d/init.sql:ro"
        ],
        "networks": ["internal_net"],
        "deploy": {
            "placement": {
                "constraints": [f"node.labels.db == {servers[i]}"]
            }
        }
    }
    stack["volumes"][f"{service_name}_data"] = None

# ProxySQL service using Docker config for proxysql.cnf
stack["services"]["proxysql"] = {
    "image": "proxysql/proxysql:latest",
    "ports": [
        "6032:6032",  # Admin interface
        "6034:6033"   # MySQL connections
    ],
    "networks": ["internal_net"],
    "depends_on": [],
    "configs": [
        {
            "source": "proxysql_config",
            "target": "/etc/proxysql.cnf",
            "mode": 292
        }
    ],
    "deploy": {
        "replicas": 1
    }
}

# Redis service
stack["services"]["redis"] = {
    "image": "redis:alpine",
    "container_name": "redis",
    "restart": "always",
    "networks": ["internal_net"],
    "ports": ["6379:6379"]
}

# phpMyAdmin service (using ProxySQL for connectivity)
stack["services"]["phpmyadmin"] = {
    "image": "phpmyadmin/phpmyadmin:latest",
    "container_name": "phpmyadmin",
    "restart": "always",
    "depends_on": ["proxysql"],
    "networks": ["internal_net"],
    "environment": {
        "PMA_HOST": "proxysql",
        "PMA_PORT": "6033",
        "MYSQL_ROOT_PASSWORD": mysql_root_password
    },
    "ports": ["8080:80"]
}

stack["volumes"]["laravel_code"] = None

with open("docker-stack.yml", "w") as f:
    yaml.dump(stack, f, default_flow_style=False)
print("docker-stack.yml generated successfully!")

# Also write proxysql.cnf and nginx.conf locally for reference (they are provided as Docker configs)
with open("proxysql.cnf", "w") as f:
    f.write(proxysql_config_content)
print("proxysql.cnf generated successfully!")

with open("nginx.conf", "w") as f:
    f.write(nginx_config_content)
print("nginx.conf generated successfully!")
