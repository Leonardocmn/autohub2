import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.buyers import BuyersService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/buyers", tags=["buyers"])


# ---------- Pydantic Schemas ----------
class BuyersData(BaseModel):
    """Entity data schema (for create/update)"""
    name: str = None
    phone: str = None
    email: str = None
    company: str = None
    city: str = None
    observations: str = None
    status: str = None


class BuyersUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None


class BuyersResponse(BaseModel):
    """Entity response schema"""
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BuyersListResponse(BaseModel):
    """List response schema"""
    items: List[BuyersResponse]
    total: int
    skip: int
    limit: int


class BuyersBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[BuyersData]


class BuyersBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: BuyersUpdateData


class BuyersBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[BuyersBatchUpdateItem]


class BuyersBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=BuyersListResponse)
async def query_buyerss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query buyerss with filtering, sorting, and pagination"""
    logger.debug(f"Querying buyerss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = BuyersService(db)
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
        logger.debug(f"Found {result['total']} buyerss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid buyers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying buyerss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=BuyersListResponse)
async def query_buyerss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query buyerss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying buyerss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = BuyersService(db)
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
        logger.debug(f"Found {result['total']} buyerss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid buyers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying buyerss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=BuyersResponse)
async def get_buyers(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single buyers by ID"""
    logger.debug(f"Fetching buyers with id: {id}, fields={fields}")
    
    service = BuyersService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Buyers with id {id} not found")
            raise HTTPException(status_code=404, detail="Buyers not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching buyers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=BuyersResponse, status_code=201)
async def create_buyers(
    data: BuyersData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new buyers"""
    logger.debug(f"Creating new buyers with data: {data}")
    
    service = BuyersService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create buyers")
        
        logger.info(f"Buyers created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating buyers: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating buyers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[BuyersResponse], status_code=201)
async def create_buyerss_batch(
    request: BuyersBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple buyerss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} buyerss")
    
    service = BuyersService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} buyerss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[BuyersResponse])
async def update_buyerss_batch(
    request: BuyersBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple buyerss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} buyerss")
    
    service = BuyersService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} buyerss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=BuyersResponse)
async def update_buyers(
    id: int,
    data: BuyersUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing buyers"""
    logger.debug(f"Updating buyers {id} with data: {data}")

    service = BuyersService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Buyers with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Buyers not found")
        
        logger.info(f"Buyers {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating buyers {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating buyers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_buyerss_batch(
    request: BuyersBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple buyerss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} buyerss")
    
    service = BuyersService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} buyerss successfully")
        return {"message": f"Successfully deleted {deleted_count} buyerss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_buyers(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single buyers by ID"""
    logger.debug(f"Deleting buyers with id: {id}")
    
    service = BuyersService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Buyers with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Buyers not found")
        
        logger.info(f"Buyers {id} deleted successfully")
        return {"message": "Buyers deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting buyers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")