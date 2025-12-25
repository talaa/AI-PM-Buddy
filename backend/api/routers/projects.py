"""
Project and folder management endpoints.
"""
import logging
import os
from fastapi import APIRouter, HTTPException

from schemas import FolderCreationRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["projects"])


@router.post("/folders/create")
async def create_folders_endpoint(request: FolderCreationRequest):
    """Create standard project subfolders locally"""
    if not request.path:
        raise HTTPException(status_code=400, detail="Path is required")
    
    base_path = request.path

    subfolders = [
        "Contracts",
        "Financials",
        "Technical Specs",
        "Correspondance",
        "Safety & Compliance"
    ]
    
    results = []
    errors = []

    try:
        # Create base folder (if it doesn't exist)
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
            results.append(f"Created base folder: {base_path}")

        for folder in subfolders:
            folder_path = os.path.join(base_path, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                results.append(f"Created: {folder}")
            except Exception as e:
                errors.append(f"Failed to create {folder}: {str(e)}")
                logger.error(f"Error creating folder {folder_path}: {e}")

        if errors:
            return {"status": "partial_success", "created": results, "errors": errors}
        
        return {"status": "success", "created": results}

    except Exception as e:
        logger.error(f"Error in folder creation: {e}")
        raise HTTPException(status_code=500, detail=f"System error: {str(e)}")
