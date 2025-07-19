# main.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Union
from fastapi.middleware.cors import CORSMiddleware

import database
import llm_service

app = FastAPI(
    title="PostgreSQL RAG API with Gemini",
    description="API to query a PostgreSQL database using natural language via Gemini LLM."
)

# --- CORS Configuration ---
origins = [
    "http://localhost:5173", # Your React app's default address
    "http://127.0.0.1:5173",
    # Add any other origins where your frontend might be hosted
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

# Global variable to store DB schema to avoid fetching on every request
DB_SCHEMA = None

@app.on_event("startup")
async def startup_event():
    """
    Connects to the database and fetches the schema on application startup.
    This ensures the schema is available for all requests without re-fetching.
    """
    global DB_SCHEMA
    conn = database.get_db_connection()
    if conn:
        DB_SCHEMA = database.get_all_table_schemas(conn)
        conn.close()
        print("\n--- Database Schema Loaded on Startup ---")
        print(DB_SCHEMA)
        print("--------------------------------------\n")
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to the database on startup."
        )

# Pydantic model for the request body
class QueryRequest(BaseModel):
    question: str

# Pydantic model for the response body
class QueryResponse(BaseModel):
    query: str
    sql_query_generated: str
    llm_answer: str
    raw_db_results: Union[List[Dict[str, Any]], str, None] = None # For select/dml results

@app.post("/query", response_model=QueryResponse, summary="Query database with natural language")
async def natural_language_query(request: QueryRequest):
    """
    Accepts a natural language question, converts it to SQL using Gemini,
    executes the SQL on PostgreSQL, and returns the interpreted answer.
    """
    if not DB_SCHEMA:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database schema not loaded. Please try again later."
        )

    conn = None
    try:
        conn = database.get_db_connection()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to the database."
            )

        # 1. Generate SQL Query using LLM
        sql_query = llm_service.generate_sql_query(request.question, DB_SCHEMA)
        print(f"Generated SQL: {sql_query}") # For logging

        # 2. Execute SQL Query
        columns, results = database.execute_sql_query(conn, sql_query)

        # Prepare raw DB results for API response
        raw_db_results_formatted = None
        if isinstance(results, list): # It's a SELECT query result
            if columns:
                raw_db_results_formatted = [
                    {col: row[i] for i, col in enumerate(columns)}
                    for row in results
                ]
            else:
                raw_db_results_formatted = []
        elif isinstance(results, str): # It's a DML operation message
            raw_db_results_formatted = results

        # 3. Interpret and Present Results using LLM
        llm_answer = llm_service.interpret_and_present_results(
            request.question, sql_query, columns, results
        )

        return QueryResponse(
            query=request.question,
            sql_query_generated=sql_query,
            llm_answer=llm_answer,
            raw_db_results=raw_db_results_formatted
        )

    except HTTPException as he:
        raise he # Re-raise FastAPI HTTP exceptions
    except Exception as e:
        print(f"An error occurred: {e}") # Log the error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

@app.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Basic health check to ensure the API is running and can connect to the database.
    """
    conn = None
    try:
        conn = database.get_db_connection()
        if conn:
            # Try to fetch schema to ensure DB is fully responsive
            test_schema = database.get_all_table_schemas(conn)
            if test_schema:
                return {"status": "ok", "message": "API and database connection are healthy."}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database connected but could not retrieve schema."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to the database."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
    finally:
        if conn:
            conn.close()