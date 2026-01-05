#!/bin/bash

# Update package list
sudo apt-get update

# Install PostgreSQL and its dependencies
sudo apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql

# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE cohortkuku;"
sudo -u postgres psql -c "CREATE USER kuku WITH PASSWORD '123@kuku';"
sudo -u postgres psql -c "ALTER ROLE kuku SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE kuku SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE kuku SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cohortkuku TO kuku;"

echo "PostgreSQL has been set up successfully!"
echo "Database: cohortkuku"
echo "Username: kuku"
echo "Password: 123@kuku"
