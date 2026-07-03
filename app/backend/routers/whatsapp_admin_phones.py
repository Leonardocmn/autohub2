import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.whatsapp_admin_phones import Whatsapp_admin_phonesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/whatsapp_admin_phones", tags=["whatsapp_admin_phones"])


# ---------- Pydantic Schemas ----------
class Whatsapp_admin_phonesData(BaseModel):
    """Entity data schema (for create/update)"""
    phone: str
    name: str = None
    active: bool = None


class Whatsapp_admin_phonesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    phone: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None


class Whatsapp_admin_phonesResponse(BaseModel):
    """Entity response schema"""
    id: int
    phone: str
    name: Optional[str] = None
    active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Whatsapp_admin_phonesListResponse(BaseModel):
    """List response schema"""
    items: List[Whatsapp_admin_phonesResponse]
    total: int
    skip: int
    limit: int


class Whatsapp_admin_phonesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Whatsapp_admin_phonesData]


class Whatsapp_admin_phonesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Whatsapp_admin_phonesUpdateData


class Whatsapp_admin_phonesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Whatsapp_admin_phonesBatchUpdateItem]


class Whatsapp_admin_phonesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Whatsapp_admin_phonesListResponse)
async def query_whatsapp_admin_phoness(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query whatsapp_admin_phoness with filtering, sorting, and pagination"""
    logger.debug(f"Querying whatsapp_admin_phoness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Whatsapp_admin_phonesService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")
        
        result = await service.get_list(
            skip=skip, 
            limit=limit,
            query_dict=query_dict,
            sort=sort,
        )
        logger.debug(f"Found {result['total']} whatsapp_admin_phoness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_admin_phoness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Whatsapp_admin_phonesListResponse)
async def query_whatsapp_admin_phoness_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query whatsapp_admin_phoness with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying whatsapp_admin_phoness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Whatsapp_admin_phonesService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort
        )
        logger.debug(f"Found {result['total']} whatsapp_admin_phoness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_admin_phoness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Whatsapp_admin_phonesResponse)
async def get_whatsapp_admin_phones(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single whatsapp_admin_phones by ID"""
    logger.debug(f"Fetching whatsapp_admin_phones with id: {id}, fields={fields}")
    
    service = Whatsapp_admin_phonesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Whatsapp_admin_phones with id {id} not found")
            raise HTTPException(status_code=404, detail="Whatsapp_admin_phones not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching whatsapp_admin_phones {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Whatsapp_admin_phonesResponse, status_code=201)
async def create_whatsapp_admin_phones(
    data: Whatsapp_admin_phonesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new whatsapp_admin_phones"""
    logger.debug(f"Creating new whatsapp_admin_phones with data: {data}")
    
    service = Whatsapp_admin_phonesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create whatsapp_admin_phones")
        
        logger.info(f"Whatsapp_admin_phones created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating whatsapp_admin_phones: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating whatsapp_admin_phones: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Whatsapp_admin_phonesResponse], status_code=201)
async def create_whatsapp_admin_phoness_batch(
    request: Whatsapp_admin_phonesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple whatsapp_admin_phoness in a single request"""
    logger.debug(f"Batch creating {len(request.items)} whatsapp_admin_phoness")
    
    service = Whatsapp_admin_phonesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} whatsapp_admin_phoness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Whatsapp_admin_phonesResponse])
async def update_whatsapp_admin_phoness_batch(
    request: Whatsapp_admin_phonesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple whatsapp_admin_phoness in a single request"""
    logger.debug(f"Batch updating {len(request.items)} whatsapp_admin_phoness")
    
    service = Whatsapp_admin_phonesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} whatsapp_admin_phoness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Whatsapp_admin_phonesResponse)
async def update_whatsapp_admin_phones(
    id: int,
    data: Whatsapp_admin_phonesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing whatsapp_admin_phones"""
    logger.debug(f"Updating whatsapp_admin_phones {id} with data: {data}")

    service = Whatsapp_admin_phonesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Whatsapp_admin_phones with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Whatsapp_admin_phones not found")
        
        logger.info(f"Whatsapp_admin_phones {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating whatsapp_admin_phones {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating whatsapp_admin_phones {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_whatsapp_admin_phoness_batch(
    request: Whatsapp_admin_phonesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple whatsapp_admin_phoness by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} whatsapp_admin_phoness")
    
    service = Whatsapp_admin_phonesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} whatsapp_admin_phoness successfully")
        return {"message": f"Successfully deleted {deleted_count} whatsapp_admin_phoness", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_whatsapp_admin_phones(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single whatsapp_admin_phones by ID"""
    logger.debug(f"Deleting whatsapp_admin_phones with id: {id}")
    
    service = Whatsapp_admin_phonesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Whatsapp_admin_phones with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Whatsapp_admin_phones not found")
        
        logger.info(f"Whatsapp_admin_phones {id} deleted successfully")
        return {"message": "Whatsapp_admin_phones deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting whatsapp_admin_phones {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")