import psycopg2
from psycopg2 import OperationalError

def check_postgres_connection():
    try:
        conn = psycopg2.connect(
            dbname='cohortkuku',
            user='kuku',
            password='123@kuku',
            host='localhost',
            port='5432'
        )
        print("Successfully connected to PostgreSQL database")
        
        # Check if the connection is working
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        print(f"PostgreSQL database version: {db_version[0]}")
        
        # List all databases
        cursor.execute("SELECT datname FROM pg_database;")
        print("\nAvailable databases:")
        for db in cursor.fetchall():
            print(f"- {db[0]}")
            
        cursor.close()
        conn.close()
        
    except OperationalError as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure PostgreSQL is running: 'sudo systemctl status postgresql'")
        print("2. Check if the database exists: 'sudo -u postgres psql -c \"SELECT datname FROM pg_database;\"'")
        print("3. Verify user permissions: 'sudo -u postgres psql -c \"\du\"'")
        print("4. Check PostgreSQL logs: 'sudo tail -n 50 /var/log/postgresql/postgresql-*-main.log'")

if __name__ == "__main__":
    check_postgres_connection()
