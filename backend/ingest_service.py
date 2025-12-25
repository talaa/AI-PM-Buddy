import os
import logging
from typing import List, Dict, Any
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from database import supabase
from rag_manager import RAGDocumentManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize RAG Manager Lazily
rag_manager = None

def get_rag_manager():
    global rag_manager
    if rag_manager is None:
        rag_manager = RAGDocumentManager()
    return rag_manager

# Initialize Embeddings Lazily
embeddings_model = None

def get_embeddings_model():
    global embeddings_model
    if embeddings_model is None:
        embeddings_model = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url="http://localhost:11434"
        )
    return embeddings_model

# Initialize Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

async def process_and_store_document(document_id: str, file_path: str, metadata: Dict[str, Any] = None):
    """
    Reads a file:
    - If Excel/CSV: Ingests into SQLite.
    - If PDF/Text: Chunks, embeds, and stores in Supabase `document_chunks`.
    """
    logger.info(f"Starting ingestion for document {document_id} at {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
        
    try:
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        
        # --- PATH A: Structured Data (SQLite) ---
        if ext in [".xlsx", ".xls", ".csv"]:
            # Sanitize table name: filename without extension, alphanumeric only
            table_name = os.path.splitext(filename)[0]
            table_name = "".join([c if c.isalnum() else "_" for c in table_name])
            
            logger.info(f"Ingesting structured data into table: {table_name}")
            logger.info(f"Ingesting structured data into table: {table_name}")
            get_rag_manager().ingest_excel(file_path, table_name)
            return True

        # --- PATH B: Unstructured Data (Vector Store) ---
        content = ""
        
        if ext == ".pdf":
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() + "\n"
        elif ext in [".docx", ".doc"]:
            # Lazy import to avoid dependency issues if not installed yet
            import docx 
            # Open file stream to ensure it's closed
            with open(file_path, "rb") as f:
                doc = docx.Document(f)
                content = "\n".join([para.text for para in doc.paragraphs])
        elif ext in [".txt", ".md", ".json"]:
             with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            logger.warning(f"Unsupported file type for RAG: {ext}. Skipping content extraction.")
            return False

        if not content.strip():
            logger.warning("Document content is empty.")
            return False

        # Split Text
        chunks = text_splitter.split_text(content)
        logger.info(f"Generated {len(chunks)} chunks from document.")

        # Embed and Prepare Records
        records = []
        for i, chunk in enumerate(chunks):
            vector = get_embeddings_model().embed_query(chunk)
            records.append({
                "project_document_id": document_id,
                "content": chunk,
                "metadata": {
                    "source": filename,
                    "project_document_id": document_id,
                    "chunk_index": i,
                    **(metadata or {})
                },
                "embedding": vector
            })
            
        # Store in Supabase
        batch_size = 50
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            response = supabase.table("document_chunks").insert(batch).execute()
            logger.info(f"Stored batch {i // batch_size + 1}: {len(response.data) if response.data else 0} chunks.")
            
        logger.info(f"Successfully ingrained document {document_id}")
        return True

    except Exception as e:
        logger.error(f"Error ingesting document: {str(e)}", exc_info=True)
        return False
