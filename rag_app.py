import os
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("key not found")

DB_NAME = "my_llm_db"
DB_USER = "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-2.0-flash')

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except pyscopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_table_schema(cursor, table_name):
    """Retrieves the schema (column names and types) for a given table."""
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

def generate_sql_query(user_question, db_schema):
    """Uses Gemini to generate an SQL query based on the user's question and DB schema."""
    prompt = f"""
    You are an expert in PostgreSQL and can convert natural language questions into SQL queries.
    Here is the database schema:

    {db_schema}

    Based on the schema, generate a PostgreSQL SQL query to answer the following question:
    Question: "{user_question}"

    Provide only the SQL query as your answer, no additional text or explanations.
    """
    response = model.generate_content(prompt)
    sql_query = response.text.strip()
    # Simple post-processing to clean up potential markdown
    if sql_query.startswith("```sql") and sql_query.endswith("```"):
        sql_query = sql_query[7:-3].strip()
    elif sql_query.startswith("```") and sql_query.endswith("```"):
         sql_query = sql_query[3:-3].strip()
    return sql_query

def interpret_and_present_results(user_question, sql_query, columns, rows):
    """Uses Gemini to interpret SQL results and present them in a user-friendly way."""
    if rows is None: # For DML operations
        return f"Operation successful based on your query: '{sql_query}'"

    # Prepare results for LLM
    results_str = f"SQL Query Executed: {sql_query}\n\n"
    if columns:
        results_str += "Columns: " + ", ".join(columns) + "\n"
    if rows:
        results_str += "Results:\n"
        for row in rows:
            results_str += str(row) + "\n"
    else:
        results_str += "No results found for this query."

    prompt = f"""
    The user asked: "{user_question}"
    I executed the following SQL query:
    {sql_query}
    And got these results from the database:
    {results_str}

    Based on the user's question and the SQL results, provide a concise and clear natural language answer.
    If there are specific data points, highlight them. If no results, state that clearly.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

# def main():
#     conn = get_db_connection()
#     if not conn:
#         print("Could not connect to the database. Exiting.")
#         return

#     # Get the schema of all tables once
#     db_schema = get_all_table_schemas(conn)
#     print("\n--- Database Schema Loaded ---")
#     print(db_schema)
#     print("----------------------------\n")

#     while True:
#         user_question = input("Ask a question about your database (or type 'exit' to quit): \n")
#         if user_question.lower() == 'exit':
#             break

#         print("\nThinking...")
#         try:
#             # 1. Generate SQL Query
#             sql_query = generate_sql_query(user_question, db_schema)
#             print(f"\nGenerated SQL: {sql_query}")

#             # 2. Execute SQL Query
#             columns, results = execute_sql_query(conn, sql_query)

#             # 3. Interpret and Present Results
#             final_answer = interpret_and_present_results(user_question, sql_query, columns, results)
#             print(f"\nAI Answer: {final_answer}\n")

#         except Exception as e:
#             print(f"An error occurred: {e}")
#             print("Please try rephrasing your question or check the API key/database connection.")

#     conn.close()
#     print("Exiting application. Goodbye!")

# if __name__ == "__main__":
#     main()