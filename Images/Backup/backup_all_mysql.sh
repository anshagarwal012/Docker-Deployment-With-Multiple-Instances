#!/bin/bash
# backup_all_mysql.sh
# This script backs up each MySQL instance's database by running mysqldump
# inside each MySQL container and compressing the output.
# It assumes the SQL files are stored in a host backup directory.

# Set the directory to store backups (modify as needed)
BACKUP_DIR="/backup/mysql"
mkdir -p "$BACKUP_DIR"

# Get the current date for backup filenames
DATE=$(date +"%F")

echo "Starting MySQL backup process at $(date)"

# Define MySQL instances with container name, database name, and root password.
# Format: container_name|database|root_password
mysql_instances=(
    "mysql19|allairx|rootpass"
    "mysql20|allairx|rootpass"
    "mysql1|db_site1|rootpass"
    "mysql2|db_site2|rootpass"
    "mysql3|db_site3|rootpass"
    "mysql4|db_site4|rootpass"
    "mysql5|db_site5|rootpass"
    "mysql6|db_site6|rootpass"
    "mysql7|db_site7|rootpass"
    "mysql8|db_site8|rootpass"
    "mysql9|db_site9|rootpass"
    "mysql10|db_site10|rootpass"
    "mysql11|db_site11|rootpass"
    "mysql12|db_site12|rootpass"
    "mysql13|db_site13|rootpass"
    "mysql14|db_site14|rootpass"
    "mysql15|db_site15|rootpass"
    "mysql16|db_site16|rootpass"
    "mysql17|db_site17|rootpass"
    "mysql18|db_site18|rootpass"
)

# Loop over each instance and perform the backup.
for entry in "${mysql_instances[@]}"; do
    IFS="|" read -r container db_name rootpass <<< "$entry"
    backup_file="${BACKUP_DIR}/${container}_${db_name}_${DATE}.sql.gz"
    echo "Backing up database '$db_name' from container '$container'..."
    # Execute mysqldump inside the container and compress the output.
    docker exec "$container" mysqldump -uroot -p"$rootpass" "$db_name" | gzip > "$backup_file"
    if [ $? -eq 0 ]; then
        echo "Backup successful for $container ($db_name) -> $backup_file"
    else
        echo "Backup failed for $container ($db_name)" >&2
    fi
done

echo "MySQL backup process completed at $(date)"
