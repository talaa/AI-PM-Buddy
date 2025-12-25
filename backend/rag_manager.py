import os
from typing import Optional
import logging
import json
# import pandas as pd
from sqlalchemy import create_engine, text, inspect
from langchain_ollama import OllamaEmbeddings
from database import supabase

logger = logging.getLogger(__name__)

# Directory to store local SQLite databases
DB_DIR = os.path.join(os.path.dirname(__file__), "project_data")
os.makedirs(DB_DIR, exist_ok=True)

class RAGDocumentManager:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://localhost:11434"
        )
        # We will dynamically connect to the correct SQLite DB based on context?
        # For MVP, let's assume a single global DB or passed in context.
        # But the User Request implies "project specific".
        # Let's use a default one for now or handling dynamic connection.
        self.db_path = os.path.join(DB_DIR, "global_project_data.db") 
        self.engine = create_engine(f"sqlite:///{self.db_path}")

    @property
    def processor(self):
        # Helper to expose embeddings for the tools
        return self

    def search_documents(self, query_embedding: list, match_count: int = 5, target_document_id: Optional[str] = None, target_filename: Optional[str] = None):
        """
        Search Supabase vector store
        """
        try:
            # If filtering by document, we fetch more results globally then filter in Python
            # This is a workaround because we cannot add a new RPC with the current permissions.
            actual_match_count = match_count * 10 if (target_document_id or target_filename) else match_count
            
            response = supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.3, # Lower threshold when filtering to be safer
                    "match_count": actual_match_count
                }
            ).execute()
            
            results = response.data or []
            
            if target_document_id or target_filename:
                # Filter results by the specific project_document_id in metadata OR by filename
                results = [
                    r for r in results 
                    if (target_document_id and r.get("metadata", {}).get("project_document_id") == target_document_id)
                    or (target_filename and r.get("metadata", {}).get("source") == target_filename)
                ]
                # Return only the requested number of matches
                results = results[:match_count]
                
            return results
        except Exception as e:
            logger.error(f"Supabase search error: {e}")
            return []

    def query_structured_data(self, sql_query: str):
        """
        Execute read-only SQL query on SQLite
        """
        # Security check: rudimentary read-only check
        if not sql_query.strip().lower().startswith("select"):
            return None, False, "Only SELECT queries are allowed."

        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                # Convert to list of dicts
                rows = [dict(row._mapping) for row in result]
                return rows, True, None
        except Exception as e:
            return None, False, str(e)

    def get_data_context(self) -> str:
        """
        Get schema string for all tables
        """
        try:
            inspector = inspect(self.engine)
            table_names = inspector.get_table_names()
            
            schema_info = []
            for table in table_names:
                columns = inspector.get_columns(table)
                col_str = ", ".join([f"{c['name']} ({c['type']})" for c in columns])
                
                # Get row count
                with self.engine.connect() as conn:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM '{table}'")).scalar()
                    
                schema_info.append(f"Table: {table} ({count} rows)\nColumns: {col_str}")
                
            return "\n\n".join(schema_info)
        except Exception as e:
            logger.error(f"Schema introspection error: {e}")
            return str(e)

    def ingest_excel(self, file_path: str, table_name: str):
        """
        Load Excel/CSV into SQLite
        """
        try:
            import pandas as pd
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Sanitize column names
            df.columns = [c.strip().replace(" ", "_").lower() for c in df.columns]
            
            # Write to SQLite
            df.to_sql(table_name, self.engine, if_exists='replace', index=False)
            logger.info(f"Ingested table {table_name} into SQLite")
            return True
        except Exception as e:
            logger.error(f"Excel ingestion error: {e}")
            raise e

    def drop_table(self, table_name: str):
        """
        Drop a table from SQLite if it exists
        """
        try:
            # Drop table
            with self.engine.connect() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                conn.commit() # Ensure commit for DDL
            logger.info(f"Dropped table {table_name} from SQLite")
            return True
        except Exception as e:
            logger.error(f"Error dropping table {table_name}: {e}")
            return False
