import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.suppliers import SuppliersService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/suppliers", tags=["suppliers"])


# ---------- Pydantic Schemas ----------
class SuppliersData(BaseModel):
    """Entity data schema (for create/update)"""
    name: str = None
    phone: str = None
    company: str = None
    category: str = None
    city: str = None
    observations: str = None
    status: str = None


class SuppliersUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None


class SuppliersResponse(BaseModel):
    """Entity response schema"""
    id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    observations: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SuppliersListResponse(BaseModel):
    """List response schema"""
    items: List[SuppliersResponse]
    total: int
    skip: int
    limit: int


class SuppliersBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[SuppliersData]


class SuppliersBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: SuppliersUpdateData


class SuppliersBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[SuppliersBatchUpdateItem]


class SuppliersBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=SuppliersListResponse)
async def query_supplierss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query supplierss with filtering, sorting, and pagination"""
    logger.debug(f"Querying supplierss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = SuppliersService(db)
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
        logger.debug(f"Found {result['total']} supplierss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid suppliers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying supplierss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=SuppliersListResponse)
async def query_supplierss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query supplierss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying supplierss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = SuppliersService(db)
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
        logger.debug(f"Found {result['total']} supplierss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid suppliers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying supplierss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=SuppliersResponse)
async def get_suppliers(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single suppliers by ID"""
    logger.debug(f"Fetching suppliers with id: {id}, fields={fields}")
    
    service = SuppliersService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Suppliers with id {id} not found")
            raise HTTPException(status_code=404, detail="Suppliers not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching suppliers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=SuppliersResponse, status_code=201)
async def create_suppliers(
    data: SuppliersData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new suppliers"""
    logger.debug(f"Creating new suppliers with data: {data}")
    
    service = SuppliersService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create suppliers")
        
        logger.info(f"Suppliers created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating suppliers: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating suppliers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[SuppliersResponse], status_code=201)
async def create_supplierss_batch(
    request: SuppliersBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple supplierss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} supplierss")
    
    service = SuppliersService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} supplierss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[SuppliersResponse])
async def update_supplierss_batch(
    request: SuppliersBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple supplierss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} supplierss")
    
    service = SuppliersService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} supplierss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=SuppliersResponse)
async def update_suppliers(
    id: int,
    data: SuppliersUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing suppliers"""
    logger.debug(f"Updating suppliers {id} with data: {data}")

    service = SuppliersService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Suppliers with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Suppliers not found")
        
        logger.info(f"Suppliers {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating suppliers {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating suppliers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_supplierss_batch(
    request: SuppliersBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple supplierss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} supplierss")
    
    service = SuppliersService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} supplierss successfully")
        return {"message": f"Successfully deleted {deleted_count} supplierss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_suppliers(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single suppliers by ID"""
    logger.debug(f"Deleting suppliers with id: {id}")
    
    service = SuppliersService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Suppliers with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Suppliers not found")
        
        logger.info(f"Suppliers {id} deleted successfully")
        return {"message": "Suppliers deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting suppliers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")