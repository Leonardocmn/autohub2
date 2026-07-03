import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.fipe_consultation_logs import Fipe_consultation_logsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/fipe_consultation_logs", tags=["fipe_consultation_logs"])


# ---------- Pydantic Schemas ----------
class Fipe_consultation_logsData(BaseModel):
    """Entity data schema (for create/update)"""
    phone: str
    plate: str = None
    fipe_code: str = None
    vehicle_description: str = None
    price_returned: str = None
    source: str
    result_json: str = None


class Fipe_consultation_logsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    phone: Optional[str] = None
    plate: Optional[str] = None
    fipe_code: Optional[str] = None
    vehicle_description: Optional[str] = None
    price_returned: Optional[str] = None
    source: Optional[str] = None
    result_json: Optional[str] = None


class Fipe_consultation_logsResponse(BaseModel):
    """Entity response schema"""
    id: int
    phone: str
    plate: Optional[str] = None
    fipe_code: Optional[str] = None
    vehicle_description: Optional[str] = None
    price_returned: Optional[str] = None
    source: str
    result_json: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Fipe_consultation_logsListResponse(BaseModel):
    """List response schema"""
    items: List[Fipe_consultation_logsResponse]
    total: int
    skip: int
    limit: int


class Fipe_consultation_logsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Fipe_consultation_logsData]


class Fipe_consultation_logsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Fipe_consultation_logsUpdateData


class Fipe_consultation_logsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Fipe_consultation_logsBatchUpdateItem]


class Fipe_consultation_logsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Fipe_consultation_logsListResponse)
async def query_fipe_consultation_logss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query fipe_consultation_logss with filtering, sorting, and pagination"""
    logger.debug(f"Querying fipe_consultation_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Fipe_consultation_logsService(db)
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
        logger.debug(f"Found {result['total']} fipe_consultation_logss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying fipe_consultation_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Fipe_consultation_logsListResponse)
async def query_fipe_consultation_logss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query fipe_consultation_logss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying fipe_consultation_logss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Fipe_consultation_logsService(db)
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
        logger.debug(f"Found {result['total']} fipe_consultation_logss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying fipe_consultation_logss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Fipe_consultation_logsResponse)
async def get_fipe_consultation_logs(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single fipe_consultation_logs by ID"""
    logger.debug(f"Fetching fipe_consultation_logs with id: {id}, fields={fields}")
    
    service = Fipe_consultation_logsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Fipe_consultation_logs with id {id} not found")
            raise HTTPException(status_code=404, detail="Fipe_consultation_logs not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fipe_consultation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Fipe_consultation_logsResponse, status_code=201)
async def create_fipe_consultation_logs(
    data: Fipe_consultation_logsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new fipe_consultation_logs"""
    logger.debug(f"Creating new fipe_consultation_logs with data: {data}")
    
    service = Fipe_consultation_logsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create fipe_consultation_logs")
        
        logger.info(f"Fipe_consultation_logs created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating fipe_consultation_logs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating fipe_consultation_logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Fipe_consultation_logsResponse], status_code=201)
async def create_fipe_consultation_logss_batch(
    request: Fipe_consultation_logsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple fipe_consultation_logss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} fipe_consultation_logss")
    
    service = Fipe_consultation_logsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} fipe_consultation_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Fipe_consultation_logsResponse])
async def update_fipe_consultation_logss_batch(
    request: Fipe_consultation_logsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple fipe_consultation_logss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} fipe_consultation_logss")
    
    service = Fipe_consultation_logsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} fipe_consultation_logss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Fipe_consultation_logsResponse)
async def update_fipe_consultation_logs(
    id: int,
    data: Fipe_consultation_logsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing fipe_consultation_logs"""
    logger.debug(f"Updating fipe_consultation_logs {id} with data: {data}")

    service = Fipe_consultation_logsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Fipe_consultation_logs with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Fipe_consultation_logs not found")
        
        logger.info(f"Fipe_consultation_logs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating fipe_consultation_logs {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating fipe_consultation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_fipe_consultation_logss_batch(
    request: Fipe_consultation_logsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple fipe_consultation_logss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} fipe_consultation_logss")
    
    service = Fipe_consultation_logsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} fipe_consultation_logss successfully")
        return {"message": f"Successfully deleted {deleted_count} fipe_consultation_logss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_fipe_consultation_logs(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single fipe_consultation_logs by ID"""
    logger.debug(f"Deleting fipe_consultation_logs with id: {id}")
    
    service = Fipe_consultation_logsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Fipe_consultation_logs with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Fipe_consultation_logs not found")
        
        logger.info(f"Fipe_consultation_logs {id} deleted successfully")
        return {"message": "Fipe_consultation_logs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting fipe_consultation_logs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")