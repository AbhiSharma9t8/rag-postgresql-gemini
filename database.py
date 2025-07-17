#database 
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME="my_llm_db"
DB_USER="postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST="localhost"
DB_PORT="5432"

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_table_schema(cursor, table_name):
    query = f"""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = '{table_name}';
    """
    cursor.execute(query)
    columns = cursor.fetchall()
    schema_str = f"Table: {table_name}\nColumns: "
    schema_str += ", ".join([f"{col[0]} ({col[1]})" for col in columns])
    return schema_str

def get_all_table_schemas(conn):
    """Retrieves schemas for all tables in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    tables = cursor.fetchall()
    all_schemas = []
    for table in tables:
        all_schemas.append(get_table_schema(cursor, table[0]))
    cursor.close()
    return "\n\n".join(all_schemas)

def execute_sql_query(conn, sql_query):
    """Executes an SQL query and returns the results."""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        # If it's a SELECT query, fetch results
        if sql_query.strip().upper().startswith('SELECT'):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            return columns, rows
        else: # For INSERT, UPDATE, DELETE
            conn.commit()
            cursor.close()
            return None, "Command executed successfully."
    except psycopg2.Error as e:
        print(f"Error executing SQL query: {e}")
        return None, f"SQL Error: {e}"
    
