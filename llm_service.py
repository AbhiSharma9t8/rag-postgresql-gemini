# llm_service.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file. Please add it.")

genai.configure(api_key=GEMINI_API_KEY)
# Using gemini-pro for text tasks, you can change this to gemini-1.5-flash or gemini-1.5-pro if needed
model = genai.GenerativeModel('models/gemini-2.0-flash')

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
        # Convert rows to a more readable string format for the LLM
        for i, row in enumerate(rows):
            row_dict = {columns[j]: row[j] for j in range(len(columns))}
            results_str += f"- {row_dict}\n"
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