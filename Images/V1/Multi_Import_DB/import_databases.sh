#!/bin/bash
# import_all_domains.sh
# This script imports gzipped SQL files for each domain.
# It expects files to be named as <domain>.sql.gz (e.g., allairx.com.sql.gz) in the /sql/ directory.

# Default MySQL connection details (common for all domains)
MYSQL_HOST="${MYSQL_HOST:-proxysql}"
MYSQL_PORT="${MYSQL_PORT:-6033}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-rootpass}"

# The base directory where SQL files are stored.
SQL_BASE_DIR="${SQL_DIR:-/sql}"

# Define a list of domains and their DB details in a pipe-delimited format:
# Format: domain|db_name|db_password
domains=(
    "allairx.com|allairx|WireTrip0908@allairx"
    "site1.com|db_site1|pass1"
    "site2.com|db_site2|pass2"
    "site3.com|db_site3|pass3"
    "site4.com|db_site4|pass4"
    "site5.com|db_site5|pass5"
    "site6.com|db_site6|pass6"
    "site7.com|db_site7|pass7"
    "site8.com|db_site8|pass8"
    "site9.com|db_site9|pass9"
    "site10.com|db_site10|pass10"
    "site11.com|db_site11|pass11"
    "site12.com|db_site12|pass12"
    "site13.com|db_site13|pass13"
    "site14.com|db_site14|pass14"
    "site15.com|db_site15|pass15"
    "site16.com|db_site16|pass16"
    "site17.com|db_site17|pass17"
    "site18.com|db_site18|pass18"
)

echo "Starting SQL import process at $(date)"

for entry in "${domains[@]}"; do
    # Split the entry by the delimiter "|"
    IFS="|" read -r domain db_name db_password <<< "$entry"
    # Construct the file name as <domain>.sql.gz, e.g. "allairx.com.sql.gz"
    sql_file="${SQL_BASE_DIR}/${domain}.sql.gz"
    if [ -f "$sql_file" ]; then
        echo "Importing $sql_file for domain $domain into database $db_name..."
        # Uncompress the SQL file and pipe its content to mysql command
        gunzip -c "$sql_file" | mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$db_password" "$db_name"
        if [ $? -eq 0 ]; then
            echo "Successfully imported $sql_file for $domain"
        else
            echo "Error importing $sql_file for $domain" >&2
        fi
    else
        echo "SQL file not found for $domain: $sql_file"
    fi
done

echo "SQL import process completed at $(date)"
