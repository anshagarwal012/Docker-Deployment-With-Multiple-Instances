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

# Generate an init SQL file for each MySQL instance (to create multiple databases)
for group, items in mysql_groups.items():
    filename = f"init-mysql{group}.sql"
    sql_content = ""
    for item in items:
        # Create the database; assume db_name is unique per domain
        db_name = item["db_name"]
        sql_content += f"CREATE DATABASE IF NOT EXISTS {db_name};\n"
    with open(filename, "w") as f:
        f.write(sql_content)
    print(f"{filename} generated successfully.")

# ---------------------------
# Step 3: Generate Docker Swarm Stack File (docker-stack.yml)
# ---------------------------
stack = {
    'version': '3.8',
    'networks': {
        'internal_net': {
            'driver': 'overlay',
            'internal': True
        }
    },
    'services': {},
    'volumes': {}
}

# Nginx Service (config file in root)
stack['services']['nginx'] = {
    'image': 'nginx:latest',
    'ports': ['80:80', '443:443'],
    'configs': ['nginx_conf'],
    'networks': ['internal_net'],
    'deploy': {
        'placement': {
            'constraints': ['node.role == manager']
        }
    },
    'volumes': [
        './nginx.conf:/etc/nginx/nginx.conf:ro',
        './ssl:/etc/nginx/ssl:ro'
    ]
}
stack['configs'] = {
    'nginx_conf': {
        'file': './nginx.conf'
    }
}

# Laravel Application Service
stack['services']['app'] = {
    'image': 'masteransh/laravel-ecommerce-prateek:3',
    'networks': ['internal_net'],
    'deploy': {
        'replicas': 4,
        'update_config': {
            'parallelism': 2,
            'delay': '10s'
        },
        'restart_policy': {
            'condition': 'any'
        }
    },
    'environment': [
        'APP_ENV=production',
        'APP_DEBUG=false',
        'REDIS_HOST=redis',
        'REDIS_PORT=6379'
    ],
    'expose': ['9000'],
    'volumes': ['laravel_code:/var/www/html']
}

# Create 4 MySQL Services (one per server), mounting the corresponding init SQL file
for i in range(1, 5):
    service_name = f"mysql{i}"
    stack['services'][service_name] = {
        'image': 'mysql:8.0',
        'environment': {
            'MYSQL_ROOT_PASSWORD': mysql_root_password
        },
        'volumes': [
            f'{service_name}_data:/var/lib/mysql',
            f'./init-mysql{i}.sql:/docker-entrypoint-initdb.d/init.sql:ro'
        ],
        'networks': ['internal_net'],
        'deploy': {
            'placement': {
                'constraints': [f'node.labels.db == {servers[i]}']
            }
        }
    }
    stack['volumes'][f'{service_name}_data'] = None

# ProxySQL Service: list the 4 MySQL services as backends
proxysql_config = (
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
    proxysql_config += f'    {{ address="mysql{i}", port=3306, hostgroup_id=0, max_connections=100 }},\n'
proxysql_config += ')\n\n'
proxysql_config += 'mysql_users =\n(\n'
proxysql_config += '    { username="user", password="pass", default_hostgroup=0, transaction_persistent=false }\n'
proxysql_config += ')\n\n'
proxysql_config += 'mysql_query_rules =\n(\n'
proxysql_config += '    { rule_id=1, active=1, match_pattern="^SELECT", destination_hostgroup=1, apply=1 },\n'
proxysql_config += '    { rule_id=2, active=1, match_pattern=".*", destination_hostgroup=0, apply=1 }\n'
proxysql_config += ')\n'

with open('proxysql.cnf', 'w') as f:
    f.write(proxysql_config)
print("proxysql.cnf generated successfully.")

stack['services']['proxysql'] = {
    'image': 'proxysql/proxysql:latest',
    'ports': [
        "6032:6032",  # Admin interface
        "6034:6033"   # Map host port 6034 to container port 6033
    ],
    'networks': ['internal_net'],
    'depends_on': [],
    'volumes': ['./proxysql.cnf:/etc/proxysql.cnf:ro'],
    'deploy': {
        'replicas': 1
    }
}

# Redis Service
stack['services']['redis'] = {
    'image': 'redis:alpine',
    'container_name': 'redis',
    'restart': 'always',
    'networks': ['internal_net'],
    'ports': ['6379:6379']
}

# phpMyAdmin Service: using ProxySQL for connectivity
stack['services']['phpmyadmin'] = {
    'image': 'phpmyadmin/phpmyadmin:latest',
    'container_name': 'phpmyadmin',
    'restart': 'always',
    'depends_on': ['proxysql'],
    'networks': ['internal_net'],
    'environment': {
        'PMA_HOST': 'proxysql',
        'PMA_PORT': '6033',
        'MYSQL_ROOT_PASSWORD': mysql_root_password
    },
    'ports': ['8080:80']
}

# Persistent volume for Laravel code
stack['volumes']['laravel_code'] = None

with open('docker-stack.yml', 'w') as f:
    yaml.dump(stack, f, default_flow_style=False)
print("docker-stack.yml generated successfully!")

# ---------------------------
# Step 4: Generate Nginx Configuration (nginx.conf)
# ---------------------------
nginx_conf_lines = []
nginx_conf_lines.append("worker_processes auto;")
nginx_conf_lines.append("")
nginx_conf_lines.append("events {")
nginx_conf_lines.append("    worker_connections 1024;")
nginx_conf_lines.append("}")
nginx_conf_lines.append("")
nginx_conf_lines.append("http {")
nginx_conf_lines.append("    include       /etc/nginx/mime.types;")
nginx_conf_lines.append("    default_type  application/octet-stream;")
# nginx_conf_lines.append("")
# nginx_conf_lines.append("    resolver 127.0.0.11 valid=30s;")
# nginx_conf_lines.append("    resolver_timeout 5s;")
nginx_conf_lines.append("")
nginx_conf_lines.append("    sendfile        on;")
nginx_conf_lines.append("    keepalive_timeout 65;")
nginx_conf_lines.append("    access_log /var/log/nginx/access.log;")
nginx_conf_lines.append("    error_log  /var/log/nginx/error.log;")
nginx_conf_lines.append("")
nginx_conf_lines.append("    upstream app_servers {")
nginx_conf_lines.append("        server app:9000;")
nginx_conf_lines.append("    }")
nginx_conf_lines.append("")
for item in domains:
    d = item["domain"]
    if any(part.isalpha() for part in d.split('.')):  # Hostnames get SSL and redirection
        # HTTP block: redirect to HTTPS
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 80;")
        nginx_conf_lines.append(f"        server_name {d} www.{d};")
        nginx_conf_lines.append("        return 301 https://$host$request_uri;")
        nginx_conf_lines.append("    }")
        nginx_conf_lines.append("")
        # HTTPS block with SSL
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 443 ssl;")
        nginx_conf_lines.append(f"        server_name {d} www.{d};")
        nginx_conf_lines.append("")
        nginx_conf_lines.append(f"        ssl_certificate /etc/nginx/ssl/{d}.crt;")
        nginx_conf_lines.append(f"        ssl_certificate_key /etc/nginx/ssl/{d}.key;")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        root /var/www/html/public;")
        nginx_conf_lines.append("        index index.php index.html;")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location / {")
        nginx_conf_lines.append("            try_files $uri $uri/ /index.php?$query_string;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {")
        nginx_conf_lines.append("            try_files $uri =404;")
        nginx_conf_lines.append("            expires max;")
        nginx_conf_lines.append("            log_not_found off;")
        nginx_conf_lines.append("            access_log off;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location ~ \\.php$ {")
        nginx_conf_lines.append("            include fastcgi_params;")
        nginx_conf_lines.append("            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;")
        nginx_conf_lines.append("            fastcgi_pass app_servers;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        error_page 404 /index.php;")
        nginx_conf_lines.append("    }")
        nginx_conf_lines.append("")
    else:
        # For IP addresses, only HTTP block (no SSL)
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 80;")
        nginx_conf_lines.append(f"        server_name {d};")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        root /var/www/html/public;")
        nginx_conf_lines.append("        index index.php index.html;")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location / {")
        nginx_conf_lines.append("            try_files $uri $uri/ /index.php?$query_string;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {")
        nginx_conf_lines.append("            try_files $uri =404;")
        nginx_conf_lines.append("            expires max;")
        nginx_conf_lines.append("            log_not_found off;")
        nginx_conf_lines.append("            access_log off;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        location ~ \\.php$ {")
        nginx_conf_lines.append("            include fastcgi_params;")
        nginx_conf_lines.append("            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;")
        nginx_conf_lines.append("            fastcgi_pass app_servers;")
        nginx_conf_lines.append("        }")
        nginx_conf_lines.append("")
        nginx_conf_lines.append("        error_page 404 /index.php;")
        nginx_conf_lines.append("    }")
        nginx_conf_lines.append("")
nginx_conf_lines.append("}")
with open('nginx.conf', 'w') as f:
    f.write("\n".join(nginx_conf_lines))
print("nginx.conf generated successfully!")
