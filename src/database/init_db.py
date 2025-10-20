import psycopg2
from config.config import config

def init_database():
    """Initialize the PostgreSQL database."""
    # Connect to default postgres database
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database="postgres"
    )
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            # Create database if it doesn't exist
            cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{config.DB_NAME}'")
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {config.DB_NAME}")
                print(f"Created database: {config.DB_NAME}")
            else:
                print(f"Database already exists: {config.DB_NAME}")
                
    finally:
        conn.close()

if __name__ == '__main__':
    init_database() 