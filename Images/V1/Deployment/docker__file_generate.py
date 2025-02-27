import os, subprocess, yaml, json

# ---------------------------
# Step 0: Define Domains and Servers
# ---------------------------
domains = [
    {"domain": "147.93.104.239", "db_service": "mysql19", "db_name": "allairx", "db_password": "WireTrip0908@allairx"},
    {"domain": "allairx.com", "db_service": "mysql20", "db_name": "allairx", "db_password": "WireTrip0908@allairx"},
    # {"domain": "site1.com", "db_service": "mysql1", "db_name": "db_site1", "db_password": "pass1"},
    # {"domain": "site2.com", "db_service": "mysql2", "db_name": "db_site2", "db_password": "pass2"},
    # {"domain": "site3.com", "db_service": "mysql3", "db_name": "db_site3", "db_password": "pass3"},
    # {"domain": "site4.com", "db_service": "mysql4", "db_name": "db_site4", "db_password": "pass4"},
    # {"domain": "site5.com", "db_service": "mysql5", "db_name": "db_site5", "db_password": "pass5"},
    # {"domain": "site6.com", "db_service": "mysql6", "db_name": "db_site6", "db_password": "pass6"},
    # {"domain": "site7.com", "db_service": "mysql7", "db_name": "db_site7", "db_password": "pass7"},
    # {"domain": "site8.com", "db_service": "mysql8", "db_name": "db_site8", "db_password": "pass8"},
    # {"domain": "site9.com", "db_service": "mysql9", "db_name": "db_site9", "db_password": "pass9"},
    # {"domain": "site10.com", "db_service": "mysql10", "db_name": "db_site10", "db_password": "pass10"},
    # {"domain": "site11.com", "db_service": "mysql11", "db_name": "db_site11", "db_password": "pass11"},
    # {"domain": "site12.com", "db_service": "mysql12", "db_name": "db_site12", "db_password": "pass12"},
    # {"domain": "site13.com", "db_service": "mysql13", "db_name": "db_site13", "db_password": "pass13"},
    # {"domain": "site14.com", "db_service": "mysql14", "db_name": "db_site14", "db_password": "pass14"},
    # {"domain": "site15.com", "db_service": "mysql15", "db_name": "db_site15", "db_password": "pass15"},
    # {"domain": "site16.com", "db_service": "mysql16", "db_name": "db_site16", "db_password": "pass16"},
    # {"domain": "site17.com", "db_service": "mysql17", "db_name": "db_site17", "db_password": "pass17"},
    # {"domain": "site18.com", "db_service": "mysql18", "db_name": "db_site18", "db_password": "pass18"}
]

# Define master and replicas for ProxySQL (adjust these names to match your Docker service names)
master = {"address": "mysql_master", "port": 3306, "hostgroup_id": 0, "max_connections": 100}
replicas = [
    {"address": "mysql_replica1", "port": 3306, "hostgroup_id": 1, "max_connections": 100},
    {"address": "mysql_replica2", "port": 3306, "hostgroup_id": 1, "max_connections": 100},
    {"address": "mysql_replica3", "port": 3306, "hostgroup_id": 1, "max_connections": 100},
]

# Mapping of server numbers to node labels for placement constraints
servers = {1: "server1", 2: "server2", 3: "server3", 4: "server4"}

# ---------------------------
# Step 1: Auto-generate Self-Signed SSL Certificates
# ---------------------------
ssl_dir = "./ssl"
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)

def is_ip(domain):
    try:
        parts = domain.split('.')
        return all(part.isdigit() for part in parts)
    except Exception:
        return False

for item in domains:
    domain = item["domain"]
    # Only generate certificates for hostnames (not IP addresses)
    if not is_ip(domain):
        cert_file = os.path.join(ssl_dir, f"{domain}.crt")
        key_file = os.path.join(ssl_dir, f"{domain}.key")
        if not (os.path.exists(cert_file) and os.path.exists(key_file)):
            print(f"Generating self-signed certificate for {domain}...")
            cmd = (
                f"openssl req -x509 -nodes -days 365 -newkey rsa:2048 "
                f"-subj '/CN={domain}' "
                f"-keyout {key_file} -out {cert_file}"
            )
            subprocess.run(cmd, shell=True, check=True)
        else:
            print(f"Certificate for {domain} already exists.")

# ---------------------------
# Step 2: Generate Docker Swarm Stack File (docker-stack.yml)
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

# Nginx Service with SSL mount and config
stack['services']['nginx'] = {
    'image': 'nginx:latest',
    'ports': ['80:80', '443:443'],
    'depends_on': ['app'],
    'configs': ['nginx_conf'],
    'networks': {
        'internal_net': {
            'aliases': ['app']
        }
    },
    'deploy': {
        'mode': 'replicated',
        'replicas': 1,
        'placement': {
            'constraints': ['node.role == manager']
        }
    },
    'volumes': [
        './nginx.conf:/etc/nginx/nginx.conf:ro',
        './ssl:/etc/nginx/ssl:ro',
        '/home/logs/nginx:/var/log/nginx'
    ]
}

stack['configs'] = {
    'nginx_conf': {
        'file': './nginx.conf'
    }
}

# Laravel Application Service (common for all domains)
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
        'APP_DEBUG=true',
        'REDIS_HOST=redis',
        'REDIS_PORT=6379'
    ],
    'expose': ['9000'],
    'volumes': ['laravel_code:/var/www/html']
}

# MySQL Instances for Each Domain
# Each domain gets its own MySQL container; distribute evenly across servers (assume 5 per server)
for idx, item in enumerate(domains, start=1):
    service_name = item["db_service"]
    # server_num = (idx - 1) // 5 + 1  # Distribute 5 per server
    server_num = (idx - 1) % len(servers) + 1
    stack['services'][service_name] = {
        'image': 'mysql:8.0',
        'environment': {
            'MYSQL_ROOT_PASSWORD': 'rootpass',
            'MYSQL_DATABASE': item["db_name"],
            'MYSQL_USER': 'user',
            'MYSQL_PASSWORD': item["db_password"]
        },
        'volumes': [f'{service_name}_data:/var/lib/mysql'],
        'networks': ['internal_net'],
        'deploy': {
            'placement': {
                'constraints': [f'node.labels.db == {servers[server_num]}']
            }
        }
    }
    stack['volumes'][f'{service_name}_data'] = None

# ProxySQL Service – Note: For proper master/replica routing, we’ll generate a separate config later.
stack['services']['proxysql'] = {
    'image': 'proxysql/proxysql:latest',
    'ports': [
        "6032:6032",  # Admin interface
        "6034:6033"   # Map host port 6034 to container port 6033 for MySQL connections
    ],
    'networks': ['internal_net'],
    'depends_on': [],  # (No explicit dependency here; adjust if you have a designated master)
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

# phpMyAdmin Service (pointing to the first MySQL instance, assume it's mysql19)
stack['services']['phpmyadmin'] = {
    'image': 'phpmyadmin/phpmyadmin:latest',
    'container_name': 'phpmyadmin',
    'restart': 'always',
    'depends_on': ['mysql19'],
    'networks': ['internal_net'],
    'environment': {
        'PMA_HOST': 'mysql19',
        'PMA_PORT': '3306',
        'MYSQL_ROOT_PASSWORD': 'rootpass'
    },
    'ports': ['8080:80']
}

# Define persistent volume for Laravel code
stack['volumes']['laravel_code'] = None

with open('docker-stack.yml', 'w') as f:
    yaml.dump(stack, f, default_flow_style=False)
print("docker-stack.yml generated successfully!")

# ---------------------------
# Step 3: Generate ProxySQL Configuration (proxysql.cnf)
# ---------------------------
proxysql_lines = []
proxysql_lines.append('datadir="/var/lib/proxysql"')
proxysql_lines.append("")
proxysql_lines.append("admin_variables =")
proxysql_lines.append("{")
proxysql_lines.append('    admin_credentials="admin:admin"')
proxysql_lines.append('    mysql_ifaces="0.0.0.0:6032"')
proxysql_lines.append("}")
proxysql_lines.append("")
proxysql_lines.append("mysql_variables =")
proxysql_lines.append("{")
proxysql_lines.append("    threads=4")
proxysql_lines.append("}")
proxysql_lines.append("")
proxysql_lines.append("mysql_servers =")
proxysql_lines.append("(")
# Add master server entry
proxysql_lines.append(f'    {{ address="{master["address"]}", port={master["port"]}, hostgroup_id={master["hostgroup_id"]}, max_connections={master["max_connections"]} }},')
# Add replica server entries
for replica in replicas:
    proxysql_lines.append(f'    {{ address="{replica["address"]}", port={replica["port"]}, hostgroup_id={replica["hostgroup_id"]}, max_connections={replica["max_connections"]} }},')
proxysql_lines.append(")")
proxysql_lines.append("")
proxysql_lines.append("mysql_users =")
proxysql_lines.append("(")
proxysql_lines.append('    { username="user", password="pass", default_hostgroup=0, transaction_persistent=false }')
proxysql_lines.append(")")
proxysql_lines.append("")
proxysql_lines.append("mysql_query_rules =")
proxysql_lines.append("(")
proxysql_lines.append('    { rule_id=1, active=1, match_pattern="^SELECT", destination_hostgroup=1, apply=1 },')
proxysql_lines.append('    { rule_id=2, active=1, match_pattern=".*", destination_hostgroup=0, apply=1 }')
proxysql_lines.append(")")

with open('proxysql.cnf', 'w') as f:
    f.write("\n".join(proxysql_lines))
print("proxysql.cnf generated successfully!")

# ---------------------------
# Step 4: Generate Nginx Configuration (nginx.conf) with Separate Server Blocks and SSL
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
nginx_conf_lines.append("")
nginx_conf_lines.append("    resolver 127.0.0.11 valid=30s;")
nginx_conf_lines.append("    resolver_timeout 5s;")
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
# For each domain, generate server blocks
for item in domains:
    domain = item["domain"]
    if any(part.isalpha() for part in domain.split('.')):  # Hostnames, not IPs
        # HTTP block: redirect to HTTPS
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 80;")
        nginx_conf_lines.append(f"        server_name {domain} www.{domain};")
        nginx_conf_lines.append("        return 301 https://$host$request_uri;")
        nginx_conf_lines.append("    }")
        nginx_conf_lines.append("")
        # HTTPS block with SSL
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 443 ssl;")
        nginx_conf_lines.append(f"        server_name {domain} www.{domain};")
        nginx_conf_lines.append("")
        nginx_conf_lines.append(f"        ssl_certificate /etc/nginx/ssl/{domain}.crt;")
        nginx_conf_lines.append(f"        ssl_certificate_key /etc/nginx/ssl/{domain}.key;")
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
        # For IP addresses, only HTTP server block (no SSL)
        nginx_conf_lines.append("    server {")
        nginx_conf_lines.append("        listen 80;")
        nginx_conf_lines.append(f"        server_name {domain};")
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

nginx_conf_lines.append("}")  # Close the http block

with open('nginx.conf', 'w') as f:
    f.write("\n".join(nginx_conf_lines))
print("nginx.conf generated successfully!")
