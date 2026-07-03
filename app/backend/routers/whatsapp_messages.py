import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.whatsapp_messages import Whatsapp_messagesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/whatsapp_messages", tags=["whatsapp_messages"])


# ---------- Pydantic Schemas ----------
class Whatsapp_messagesData(BaseModel):
    """Entity data schema (for create/update)"""
    phone: str
    contact_name: str = None
    direction: str
    message_type: str = None
    content: str = None
    media_url: str = None
    message_id: str = None
    conversation_id: int = None
    processed: bool = None
    is_supplier: bool = None
    is_buyer: bool = None
    timestamp: str = None


class Whatsapp_messagesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    direction: Optional[str] = None
    message_type: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    message_id: Optional[str] = None
    conversation_id: Optional[int] = None
    processed: Optional[bool] = None
    is_supplier: Optional[bool] = None
    is_buyer: Optional[bool] = None
    timestamp: Optional[str] = None


class Whatsapp_messagesResponse(BaseModel):
    """Entity response schema"""
    id: int
    phone: str
    contact_name: Optional[str] = None
    direction: str
    message_type: Optional[str] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    message_id: Optional[str] = None
    conversation_id: Optional[int] = None
    processed: Optional[bool] = None
    is_supplier: Optional[bool] = None
    is_buyer: Optional[bool] = None
    timestamp: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Whatsapp_messagesListResponse(BaseModel):
    """List response schema"""
    items: List[Whatsapp_messagesResponse]
    total: int
    skip: int
    limit: int


class Whatsapp_messagesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Whatsapp_messagesData]


class Whatsapp_messagesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Whatsapp_messagesUpdateData


class Whatsapp_messagesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Whatsapp_messagesBatchUpdateItem]


class Whatsapp_messagesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Whatsapp_messagesListResponse)
async def query_whatsapp_messagess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query whatsapp_messagess with filtering, sorting, and pagination"""
    logger.debug(f"Querying whatsapp_messagess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Whatsapp_messagesService(db)
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
        logger.debug(f"Found {result['total']} whatsapp_messagess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_messagess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Whatsapp_messagesListResponse)
async def query_whatsapp_messagess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query whatsapp_messagess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying whatsapp_messagess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Whatsapp_messagesService(db)
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
        logger.debug(f"Found {result['total']} whatsapp_messagess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_messagess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Whatsapp_messagesResponse)
async def get_whatsapp_messages(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single whatsapp_messages by ID"""
    logger.debug(f"Fetching whatsapp_messages with id: {id}, fields={fields}")
    
    service = Whatsapp_messagesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Whatsapp_messages with id {id} not found")
            raise HTTPException(status_code=404, detail="Whatsapp_messages not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching whatsapp_messages {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Whatsapp_messagesResponse, status_code=201)
async def create_whatsapp_messages(
    data: Whatsapp_messagesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new whatsapp_messages"""
    logger.debug(f"Creating new whatsapp_messages with data: {data}")
    
    service = Whatsapp_messagesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create whatsapp_messages")
        
        logger.info(f"Whatsapp_messages created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating whatsapp_messages: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating whatsapp_messages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Whatsapp_messagesResponse], status_code=201)
async def create_whatsapp_messagess_batch(
    request: Whatsapp_messagesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple whatsapp_messagess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} whatsapp_messagess")
    
    service = Whatsapp_messagesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} whatsapp_messagess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Whatsapp_messagesResponse])
async def update_whatsapp_messagess_batch(
    request: Whatsapp_messagesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple whatsapp_messagess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} whatsapp_messagess")
    
    service = Whatsapp_messagesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} whatsapp_messagess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Whatsapp_messagesResponse)
async def update_whatsapp_messages(
    id: int,
    data: Whatsapp_messagesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing whatsapp_messages"""
    logger.debug(f"Updating whatsapp_messages {id} with data: {data}")

    service = Whatsapp_messagesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Whatsapp_messages with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Whatsapp_messages not found")
        
        logger.info(f"Whatsapp_messages {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating whatsapp_messages {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating whatsapp_messages {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_whatsapp_messagess_batch(
    request: Whatsapp_messagesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple whatsapp_messagess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} whatsapp_messagess")
    
    service = Whatsapp_messagesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} whatsapp_messagess successfully")
        return {"message": f"Successfully deleted {deleted_count} whatsapp_messagess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_whatsapp_messages(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single whatsapp_messages by ID"""
    logger.debug(f"Deleting whatsapp_messages with id: {id}")
    
    service = Whatsapp_messagesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Whatsapp_messages with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Whatsapp_messages not found")
        
        logger.info(f"Whatsapp_messages {id} deleted successfully")
        return {"message": "Whatsapp_messages deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting whatsapp_messages {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")