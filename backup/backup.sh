#!/bin/bash
# List of MySQL services (adjust if needed)
services=(mysql1 mysql2 mysql3 mysql4 mysql5 mysql6 mysql7 mysql8 mysql9 mysql10 mysql11 mysql12 mysql13 mysql14 mysql15 mysql16 mysql17 mysql18 mysql19 mysql20)

for service in "${services[@]}"; do
    TIMESTAMP=$(date +%F_%H-%M-%S)
    BACKUP_FILE="/backups/${service}_${TIMESTAMP}.sql"
    echo "Backing up $service to $BACKUP_FILE"
    # Use the service name as host (the internal Docker network will resolve it)
    mysqldump -h "$service" -u user -ppass --all-databases > "$BACKUP_FILE"
done
