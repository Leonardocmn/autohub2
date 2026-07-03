import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.negotiation_history import Negotiation_historyService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/negotiation_history", tags=["negotiation_history"])


# ---------- Pydantic Schemas ----------
class Negotiation_historyData(BaseModel):
    """Entity data schema (for create/update)"""
    offer_id: int
    admin_name: str = None
    previous_status: str = None
    new_status: str
    buyer_id: int = None
    observations: str = None


class Negotiation_historyUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    offer_id: Optional[int] = None
    admin_name: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    buyer_id: Optional[int] = None
    observations: Optional[str] = None


class Negotiation_historyResponse(BaseModel):
    """Entity response schema"""
    id: int
    offer_id: int
    admin_name: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: str
    buyer_id: Optional[int] = None
    observations: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Negotiation_historyListResponse(BaseModel):
    """List response schema"""
    items: List[Negotiation_historyResponse]
    total: int
    skip: int
    limit: int


class Negotiation_historyBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Negotiation_historyData]


class Negotiation_historyBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Negotiation_historyUpdateData


class Negotiation_historyBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Negotiation_historyBatchUpdateItem]


class Negotiation_historyBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Negotiation_historyListResponse)
async def query_negotiation_historys(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query negotiation_historys with filtering, sorting, and pagination"""
    logger.debug(f"Querying negotiation_historys: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Negotiation_historyService(db)
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
        logger.debug(f"Found {result['total']} negotiation_historys")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying negotiation_historys: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Negotiation_historyListResponse)
async def query_negotiation_historys_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query negotiation_historys with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying negotiation_historys: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Negotiation_historyService(db)
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
        logger.debug(f"Found {result['total']} negotiation_historys")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying negotiation_historys: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Negotiation_historyResponse)
async def get_negotiation_history(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single negotiation_history by ID"""
    logger.debug(f"Fetching negotiation_history with id: {id}, fields={fields}")
    
    service = Negotiation_historyService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Negotiation_history with id {id} not found")
            raise HTTPException(status_code=404, detail="Negotiation_history not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching negotiation_history {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Negotiation_historyResponse, status_code=201)
async def create_negotiation_history(
    data: Negotiation_historyData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new negotiation_history"""
    logger.debug(f"Creating new negotiation_history with data: {data}")
    
    service = Negotiation_historyService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create negotiation_history")
        
        logger.info(f"Negotiation_history created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating negotiation_history: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating negotiation_history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Negotiation_historyResponse], status_code=201)
async def create_negotiation_historys_batch(
    request: Negotiation_historyBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple negotiation_historys in a single request"""
    logger.debug(f"Batch creating {len(request.items)} negotiation_historys")
    
    service = Negotiation_historyService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} negotiation_historys successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Negotiation_historyResponse])
async def update_negotiation_historys_batch(
    request: Negotiation_historyBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple negotiation_historys in a single request"""
    logger.debug(f"Batch updating {len(request.items)} negotiation_historys")
    
    service = Negotiation_historyService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} negotiation_historys successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Negotiation_historyResponse)
async def update_negotiation_history(
    id: int,
    data: Negotiation_historyUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing negotiation_history"""
    logger.debug(f"Updating negotiation_history {id} with data: {data}")

    service = Negotiation_historyService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Negotiation_history with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Negotiation_history not found")
        
        logger.info(f"Negotiation_history {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating negotiation_history {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating negotiation_history {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_negotiation_historys_batch(
    request: Negotiation_historyBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple negotiation_historys by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} negotiation_historys")
    
    service = Negotiation_historyService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} negotiation_historys successfully")
        return {"message": f"Successfully deleted {deleted_count} negotiation_historys", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_negotiation_history(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single negotiation_history by ID"""
    logger.debug(f"Deleting negotiation_history with id: {id}")
    
    service = Negotiation_historyService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Negotiation_history with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Negotiation_history not found")
        
        logger.info(f"Negotiation_history {id} deleted successfully")
        return {"message": "Negotiation_history deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting negotiation_history {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")