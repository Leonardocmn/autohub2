import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.whatsapp_conversations import Whatsapp_conversationsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/whatsapp_conversations", tags=["whatsapp_conversations"])


# ---------- Pydantic Schemas ----------
class Whatsapp_conversationsData(BaseModel):
    """Entity data schema (for create/update)"""
    supplier_phone: str
    supplier_name: str = None
    status: str = None
    offer_draft_id: int = None
    last_message_at: str = None
    message_count: int = None
    ai_analysis: str = None
    window_closed: bool = None


class Whatsapp_conversationsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    supplier_phone: Optional[str] = None
    supplier_name: Optional[str] = None
    status: Optional[str] = None
    offer_draft_id: Optional[int] = None
    last_message_at: Optional[str] = None
    message_count: Optional[int] = None
    ai_analysis: Optional[str] = None
    window_closed: Optional[bool] = None


class Whatsapp_conversationsResponse(BaseModel):
    """Entity response schema"""
    id: int
    supplier_phone: str
    supplier_name: Optional[str] = None
    status: Optional[str] = None
    offer_draft_id: Optional[int] = None
    last_message_at: Optional[str] = None
    message_count: Optional[int] = None
    ai_analysis: Optional[str] = None
    window_closed: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Whatsapp_conversationsListResponse(BaseModel):
    """List response schema"""
    items: List[Whatsapp_conversationsResponse]
    total: int
    skip: int
    limit: int


class Whatsapp_conversationsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Whatsapp_conversationsData]


class Whatsapp_conversationsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Whatsapp_conversationsUpdateData


class Whatsapp_conversationsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Whatsapp_conversationsBatchUpdateItem]


class Whatsapp_conversationsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Whatsapp_conversationsListResponse)
async def query_whatsapp_conversationss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query whatsapp_conversationss with filtering, sorting, and pagination"""
    logger.debug(f"Querying whatsapp_conversationss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Whatsapp_conversationsService(db)
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
        logger.debug(f"Found {result['total']} whatsapp_conversationss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_conversationss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Whatsapp_conversationsListResponse)
async def query_whatsapp_conversationss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query whatsapp_conversationss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying whatsapp_conversationss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Whatsapp_conversationsService(db)
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
        logger.debug(f"Found {result['total']} whatsapp_conversationss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_conversationss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Whatsapp_conversationsResponse)
async def get_whatsapp_conversations(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single whatsapp_conversations by ID"""
    logger.debug(f"Fetching whatsapp_conversations with id: {id}, fields={fields}")
    
    service = Whatsapp_conversationsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Whatsapp_conversations with id {id} not found")
            raise HTTPException(status_code=404, detail="Whatsapp_conversations not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching whatsapp_conversations {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Whatsapp_conversationsResponse, status_code=201)
async def create_whatsapp_conversations(
    data: Whatsapp_conversationsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new whatsapp_conversations"""
    logger.debug(f"Creating new whatsapp_conversations with data: {data}")
    
    service = Whatsapp_conversationsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create whatsapp_conversations")
        
        logger.info(f"Whatsapp_conversations created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating whatsapp_conversations: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating whatsapp_conversations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Whatsapp_conversationsResponse], status_code=201)
async def create_whatsapp_conversationss_batch(
    request: Whatsapp_conversationsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple whatsapp_conversationss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} whatsapp_conversationss")
    
    service = Whatsapp_conversationsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} whatsapp_conversationss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Whatsapp_conversationsResponse])
async def update_whatsapp_conversationss_batch(
    request: Whatsapp_conversationsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple whatsapp_conversationss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} whatsapp_conversationss")
    
    service = Whatsapp_conversationsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} whatsapp_conversationss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Whatsapp_conversationsResponse)
async def update_whatsapp_conversations(
    id: int,
    data: Whatsapp_conversationsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing whatsapp_conversations"""
    logger.debug(f"Updating whatsapp_conversations {id} with data: {data}")

    service = Whatsapp_conversationsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Whatsapp_conversations with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Whatsapp_conversations not found")
        
        logger.info(f"Whatsapp_conversations {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating whatsapp_conversations {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating whatsapp_conversations {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_whatsapp_conversationss_batch(
    request: Whatsapp_conversationsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple whatsapp_conversationss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} whatsapp_conversationss")
    
    service = Whatsapp_conversationsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} whatsapp_conversationss successfully")
        return {"message": f"Successfully deleted {deleted_count} whatsapp_conversationss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_whatsapp_conversations(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single whatsapp_conversations by ID"""
    logger.debug(f"Deleting whatsapp_conversations with id: {id}")
    
    service = Whatsapp_conversationsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Whatsapp_conversations with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Whatsapp_conversations not found")
        
        logger.info(f"Whatsapp_conversations {id} deleted successfully")
        return {"message": "Whatsapp_conversations deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting whatsapp_conversations {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")