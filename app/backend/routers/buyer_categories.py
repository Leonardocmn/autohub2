import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.buyer_categories import Buyer_categoriesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/buyer_categories", tags=["buyer_categories"])


# ---------- Pydantic Schemas ----------
class Buyer_categoriesData(BaseModel):
    """Entity data schema (for create/update)"""
    buyer_id: int
    category_id: int


class Buyer_categoriesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    buyer_id: Optional[int] = None
    category_id: Optional[int] = None


class Buyer_categoriesResponse(BaseModel):
    """Entity response schema"""
    id: int
    buyer_id: int
    category_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Buyer_categoriesListResponse(BaseModel):
    """List response schema"""
    items: List[Buyer_categoriesResponse]
    total: int
    skip: int
    limit: int


class Buyer_categoriesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Buyer_categoriesData]


class Buyer_categoriesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Buyer_categoriesUpdateData


class Buyer_categoriesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Buyer_categoriesBatchUpdateItem]


class Buyer_categoriesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Buyer_categoriesListResponse)
async def query_buyer_categoriess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query buyer_categoriess with filtering, sorting, and pagination"""
    logger.debug(f"Querying buyer_categoriess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Buyer_categoriesService(db)
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
        logger.debug(f"Found {result['total']} buyer_categoriess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying buyer_categoriess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Buyer_categoriesListResponse)
async def query_buyer_categoriess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query buyer_categoriess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying buyer_categoriess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Buyer_categoriesService(db)
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
        logger.debug(f"Found {result['total']} buyer_categoriess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying buyer_categoriess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Buyer_categoriesResponse)
async def get_buyer_categories(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single buyer_categories by ID"""
    logger.debug(f"Fetching buyer_categories with id: {id}, fields={fields}")
    
    service = Buyer_categoriesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Buyer_categories with id {id} not found")
            raise HTTPException(status_code=404, detail="Buyer_categories not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching buyer_categories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Buyer_categoriesResponse, status_code=201)
async def create_buyer_categories(
    data: Buyer_categoriesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new buyer_categories"""
    logger.debug(f"Creating new buyer_categories with data: {data}")
    
    service = Buyer_categoriesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create buyer_categories")
        
        logger.info(f"Buyer_categories created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating buyer_categories: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating buyer_categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Buyer_categoriesResponse], status_code=201)
async def create_buyer_categoriess_batch(
    request: Buyer_categoriesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple buyer_categoriess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} buyer_categoriess")
    
    service = Buyer_categoriesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} buyer_categoriess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Buyer_categoriesResponse])
async def update_buyer_categoriess_batch(
    request: Buyer_categoriesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple buyer_categoriess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} buyer_categoriess")
    
    service = Buyer_categoriesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} buyer_categoriess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Buyer_categoriesResponse)
async def update_buyer_categories(
    id: int,
    data: Buyer_categoriesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing buyer_categories"""
    logger.debug(f"Updating buyer_categories {id} with data: {data}")

    service = Buyer_categoriesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Buyer_categories with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Buyer_categories not found")
        
        logger.info(f"Buyer_categories {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating buyer_categories {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating buyer_categories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_buyer_categoriess_batch(
    request: Buyer_categoriesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple buyer_categoriess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} buyer_categoriess")
    
    service = Buyer_categoriesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} buyer_categoriess successfully")
        return {"message": f"Successfully deleted {deleted_count} buyer_categoriess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_buyer_categories(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single buyer_categories by ID"""
    logger.debug(f"Deleting buyer_categories with id: {id}")
    
    service = Buyer_categoriesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Buyer_categories with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Buyer_categories not found")
        
        logger.info(f"Buyer_categories {id} deleted successfully")
        return {"message": "Buyer_categories deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting buyer_categories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")