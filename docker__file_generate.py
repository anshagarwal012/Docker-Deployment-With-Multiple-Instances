import yaml

# List of domains with associated DB service name, DB name and DB password
domains = [
    {"domain": "147.93.104.239",  "db_service": "mysql1",  "db_name": "db_site1",  "db_password": "pass1"},
    {"domain": "testing.lookhype.com",  "db_service": "mysql1",  "db_name": "db_site1",  "db_password": "pass1"},
    {"domain": "site1.com",  "db_service": "mysql1",  "db_name": "db_site1",  "db_password": "pass1"},
    {"domain": "site2.com",  "db_service": "mysql2",  "db_name": "db_site2",  "db_password": "pass2"},
    {"domain": "site3.com",  "db_service": "mysql3",  "db_name": "db_site3",  "db_password": "pass3"},
    {"domain": "site4.com",  "db_service": "mysql4",  "db_name": "db_site4",  "db_password": "pass4"},
    {"domain": "site5.com",  "db_service": "mysql5",  "db_name": "db_site5",  "db_password": "pass5"},
    {"domain": "site6.com",  "db_service": "mysql6",  "db_name": "db_site6",  "db_password": "pass6"},
    {"domain": "site7.com",  "db_service": "mysql7",  "db_name": "db_site7",  "db_password": "pass7"},
    {"domain": "site8.com",  "db_service": "mysql8",  "db_name": "db_site8",  "db_password": "pass8"},
    {"domain": "site9.com",  "db_service": "mysql9",  "db_name": "db_site9",  "db_password": "pass9"},
    {"domain": "site10.com", "db_service": "mysql10", "db_name": "db_site10", "db_password": "pass10"},
    {"domain": "site11.com", "db_service": "mysql11", "db_name": "db_site11", "db_password": "pass11"},
    {"domain": "site12.com", "db_service": "mysql12", "db_name": "db_site12", "db_password": "pass12"},
    {"domain": "site13.com", "db_service": "mysql13", "db_name": "db_site13", "db_password": "pass13"},
    {"domain": "site14.com", "db_service": "mysql14", "db_name": "db_site14", "db_password": "pass14"},
    {"domain": "site15.com", "db_service": "mysql15", "db_name": "db_site15", "db_password": "pass15"},
    {"domain": "site16.com", "db_service": "mysql16", "db_name": "db_site16", "db_password": "pass16"},
    {"domain": "site17.com", "db_service": "mysql17", "db_name": "db_site17", "db_password": "pass17"},
    {"domain": "site18.com", "db_service": "mysql18", "db_name": "db_site18", "db_password": "pass18"},
]

# Define your servers (nodes) mapping.
# Update this dictionary if you add more nodes. For example, if you add a fifth node:
# servers = {1: "server1", 2: "server2", 3: "server3", 4: "server4", 5: "server5"}
servers = {1: "server1", 2: "server2", 3: "server3", 4: "server4"}

# Base structure for the docker stack YAML
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

# 1. Nginx Load Balancer Service
stack['services']['nginx'] = {
    'image': 'nginx:latest',
    'ports': ['80:80'],
    # Using Docker configs is recommended for swarm deployments instead of bind mounts
    # 'volumes': ['./nginx.conf:/etc/nginx/nginx.conf:ro'],
    'networks': ['internal_net'],
    'deploy': {
        'placement': {
            'constraints': ['node.role == manager']
        }
    }
}

# 2. Laravel Application Service (handles all 20 domains)
# Create a DB_MAPPING JSON string from the domains list.
db_mapping = {
    item["domain"]: {
        "host": "proxysql",
        "port": 6033,
        "database": item["db_name"],
        "username": f"user{index}",
        "password": item["db_password"]
    }
    for index, item in enumerate(domains, start=1)
}

stack['services']['app'] = {
    'image': 'masteransh/laravel-ecommerce-prateek:latest',
    'networks': ['internal_net'],
    'deploy': {
        'replicas': 4,  # Scale with: docker service scale mystack_app=<replica_count>
        'update_config': {
            'parallelism': 2,
            'delay': '10s'
        }
    },
    'environment': [
        f'DB_MAPPING={db_mapping}',
        'APP_ENV=production'
    ]
}

# 3. MySQL Instances for Each Domain
for idx, item in enumerate(domains, start=1):
    service_name = item["db_service"]
    # Distribute databases evenly: 5 per node.
    server_num = (idx - 1) // 5 + 1  
    # The constraint below will place the service on a node with the appropriate label.
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
    # Create a Docker volume for each MySQL instance.
    stack['volumes'][f'{service_name}_data'] = None

# 4. ProxySQL Service
stack['services']['proxysql'] = {
    'image': 'proxysql/proxysql:latest',
    'ports': [
        "6032:6032",  # Admin interface
        "6034:6033"   # Map host port 6034 to container port 6033 (for external access)
    ],
    'networks': ['internal_net'],
    # Use Docker configs here if possible instead of bind mounts:
    'volumes': ['./proxysql.cnf:/etc/proxysql.cnf:ro'],
    'deploy': {
        'replicas': 1
    }
}

# 5. Backup Service (runs a daily backup using a custom backup image)
stack['services']['backup'] = {
    'image': 'masteransh/backup:latest',
    'networks': ['internal_net'],
    'volumes': ['backup_data:/backups'],
    'deploy': {
        'replicas': 1
    }
}
stack['volumes']['backup_data'] = None

# Write the generated Docker stack YAML file
with open('docker-stack.yml', 'w') as f:
    yaml.dump(stack, f, default_flow_style=False)

print("docker-stack.yml generated successfully!")

# --------------------------------------------------------------------
# Generate the ProxySQL configuration file dynamically.
proxysql_lines = []
proxysql_lines.append('datadir="/var/lib/proxysql"')
proxysql_lines.append('admin_variables=\n{')
proxysql_lines.append('    admin_credentials="admin:admin"')
proxysql_lines.append('    mysql_ifaces="0.0.0.0:6032"')
proxysql_lines.append('}')
proxysql_lines.append('mysql_variables=\n{')
proxysql_lines.append('    threads=4')
proxysql_lines.append('}')
proxysql_lines.append('mysql_servers =\n(')
# Build mysql_servers section with each MySQL service from domains.
for item in domains:
    # Each entry uses the service name as the address; port 3306 is assumed.
    line = f'    {{ address="{item["db_service"]}", port=3306, hostgroup=0, max_connections=100 }},'
    proxysql_lines.append(line)
proxysql_lines.append(')')
proxysql_lines.append('mysql_users:\n(')
proxysql_lines.append('    { username="user", password="pass", default_hostgroup=0, transaction_persistent=false }')
proxysql_lines.append(')')

# Write proxysql.cnf file
with open('proxysql.cnf', 'w') as f:
    f.write("\n".join(proxysql_lines))

print("proxysql.cnf generated successfully!")

# --------------------------------------------------------------------
# NOTE:
# To add new nodes in the future, update the 'servers' dictionary above with new mappings,
# e.g., servers = {1: "server1", 2: "server2", 3: "server3", 4: "server4", 5: "server5"}.
#
# Also, ensure that each Docker Swarm node is labeled appropriately:
# For example:
#   docker node update --label-add db=server1 <node-id-for-server1>
#   docker node update --label-add db=server2 <node-id-for-server2>
#   docker node update --label-add db=server3 <node-id-for-server3>
#   docker node update --label-add db=server4 <node-id-for-server4>
#
# Then, redeploy your stack after updating the configuration.
#
# Increasing the replica count for the app or ProxySQL service using:
#   docker service scale mystack_app=6
# is a good practice to handle increased traffic.
