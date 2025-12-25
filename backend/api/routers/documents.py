"""
Document management endpoints for upload, deletion, and RAG ingestion.
"""
import logging
import os
import shutil
import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks

from database import supabase
from config import MAX_FILE_DELETE_RETRIES, FILE_DELETE_RETRY_DELAY
from ingest_service import process_and_store_document, rag_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Form(...),
    category: str = Form(...),
    status: str = Form(...),
    tags: str = Form(None)
):
    """
    Handle document upload:
    1. Fetch project path from Supabase.
    2. Save file to category subfolder.
    3. Log entry to project_documents table.
    4. Trigger RAG Ingestion (Async).
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # 1. Fetch Project Path
        response = supabase.table("projects").select("sharepoint_folder_path").eq("id", project_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        base_path = response.data.get("sharepoint_folder_path")
        if not base_path:
            raise HTTPException(status_code=400, detail="Project has no configured local folder path")

        # 2. Determine Save Path
        # Map category names to folder names if they differ slightly, or use direct match
        # Assuming category matches folder definitions in create_folders_endpoint
        folder_name = category
        target_dir = os.path.join(base_path, folder_name)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True) # Create if missing

        file_path = os.path.join(target_dir, file.filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)

        # 3. Log to Supabase
        # Parse tags (comma separated string) -> list
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        doc_entry = {
            "project_id": project_id,
            "user_id": user_id,
            "filename": file.filename,
            "file_path": file_path,
            "category": category,
            "status": status,
            "tags": tag_list,
            "file_size": file_size,
            "content_type": file.content_type
        }

        db_response = supabase.table("project_documents").insert(doc_entry).execute()
        new_doc = db_response.data[0] if db_response.data else {}

        # 4. Trigger Ingestion (Background)
        if new_doc and new_doc.get("id"):
            background_tasks.add_task(
                process_and_store_document, 
                document_id=new_doc.get("id"), 
                file_path=file_path,
                metadata={"category": category}
            )

        return {
            "message": "File uploaded and logged successfully. RAG ingestion started.", 
            "data": new_doc,
            "saved_path": file_path
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document:
    1. Fetch file path from Supabase
    2. Delete local file
    3. Delete database record
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # 1. Fetch document details to get the path
        response = supabase.table("project_documents").select("*").eq("id", document_id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc = response.data
        file_path = doc.get("file_path")

        # 2. Delete local file with Retry Logic
        if file_path and os.path.exists(file_path):
            try:
                # Check for structured data cleanup before deletion
                ext = os.path.splitext(file_path)[1].lower()
                filename = os.path.basename(file_path)
                
                if ext in [".xlsx", ".xls", ".csv"]:
                    # Same sanitization logic as ingest_service.py
                    table_name = os.path.splitext(filename)[0]
                    table_name = "".join([c if c.isalnum() else "_" for c in table_name])
                    logger.info(f"Attempting to drop table {table_name} for deleted file {filename}")
                    rag_manager.drop_table(table_name)
                    
            except Exception as e:
                logger.error(f"Error during structured data cleanup: {e}")

            for attempt in range(MAX_FILE_DELETE_RETRIES):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted local file: {file_path}")
                    break  # Success
                except PermissionError:
                    if attempt < MAX_FILE_DELETE_RETRIES - 1:
                        logger.warning(f"File locked, retrying delete ({attempt+1}/{MAX_FILE_DELETE_RETRIES}): {file_path}")
                        await asyncio.sleep(FILE_DELETE_RETRY_DELAY)
                    else:
                        logger.error(f"Failed to delete file after retries (locked): {file_path}")
                        # Proceed to delete from DB anyway
                except Exception as e:
                    logger.error(f"Failed to delete local file {file_path}: {e}")
                    break
        else:
            logger.warning(f"File not found locally: {file_path}")

        # 3. Delete from Supabase
        supabase.table("project_documents").delete().eq("id", document_id).execute()
        
        return {"status": "success", "message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
