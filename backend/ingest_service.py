import os
import logging
from typing import List, Dict, Any
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from database import supabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Embeddings
embeddings_model = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# Initialize Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)

async def process_and_store_document(document_id: str, file_path: str, metadata: Dict[str, Any] = None):
    """
    Reads a file, chunks it, embeds it, and stores it in Supabase `document_chunks`.
    """
    logger.info(f"Starting ingestion for document {document_id} at {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
        
    try:
        # 1. Extract Text
        content = ""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                content += page.extract_text() + "\n"
        elif ext in [".txt", ".md", ".csv", ".json"]:
             with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            logger.warning(f"Unsupported file type for RAG: {ext}. Skipping content extraction.")
            return False

        if not content.strip():
            logger.warning("Document content is empty.")
            return False

        # 2. Split Text
        chunks = text_splitter.split_text(content)
        logger.info(f"Generated {len(chunks)} chunks from document.")

        # 3. Embed and Prepare Records
        records = []
        
        # Batch embedding for efficiency? 
        # langchain-ollama handles list inputs but let's do it explicitly if needed.
        # embeddings = embeddings_model.embed_documents(chunks) 
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            vector = embeddings_model.embed_query(chunk)
            
            records.append({
                "project_document_id": document_id,
                "content": chunk,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "chunk_index": i,
                    **(metadata or {})
                },
                "embedding": vector
            })
            
        # 4. Store in Supabase
        # Insert in batches of 50 to avoid payload limits
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
