import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    # Connect to the default 'postgres' database
    conn = psycopg2.connect(user="postgres", password="postgres", host="localhost", database="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create our new database
    cursor.execute("CREATE DATABASE agriflux")
    print("Database 'agriflux' created successfully!")
    
    cursor.close()
    conn.close()
except psycopg2.errors.DuplicateDatabase:
    print("Database 'agriflux' already exists! Good to go.")
except Exception as e:
    print(f"Error: {e}")
