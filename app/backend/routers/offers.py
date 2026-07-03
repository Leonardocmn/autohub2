import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.offers import OffersService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/offers", tags=["offers"])


# ---------- Pydantic Schemas ----------
class OffersData(BaseModel):
    """Entity data schema (for create/update)"""
    code: str = None
    supplier_id: int = None
    title: str = None
    brand: str = None
    model: str = None
    version: str = None
    year: str = None
    color: str = None
    mileage: str = None
    price: float = None
    supplier_price: float = None
    description: str = None
    status: str = None
    negotiation_status: str = None
    negotiation_substatus: str = None
    negotiation_buyer_id: int = None
    doc_status: str = None
    vehicle_status: str = None
    negotiation_deadline_hours: int = None
    distributed_at: str = None
    finalized_at: str = None
    images: str = None
    selected_images: str = None
    fipe: str = None
    plate: str = None
    fuel: str = None
    transmission: str = None
    suggested_category: str = None
    has_manual: bool = None
    has_spare_key: bool = None
    is_auction: bool = None
    target_categories: str = None
    processed_images: str = None
    original_images: str = None
    sold_buyer_id: int = None
    sale_notes: str = None
    vehicle_dossier_id: int = None


class OffersUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    code: Optional[str] = None
    supplier_id: Optional[int] = None
    title: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    year: Optional[str] = None
    color: Optional[str] = None
    mileage: Optional[str] = None
    price: Optional[float] = None
    supplier_price: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None
    negotiation_status: Optional[str] = None
    negotiation_substatus: Optional[str] = None
    negotiation_buyer_id: Optional[int] = None
    doc_status: Optional[str] = None
    vehicle_status: Optional[str] = None
    negotiation_deadline_hours: Optional[int] = None
    distributed_at: Optional[str] = None
    finalized_at: Optional[str] = None
    images: Optional[str] = None
    selected_images: Optional[str] = None
    fipe: Optional[str] = None
    plate: Optional[str] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    suggested_category: Optional[str] = None
    has_manual: Optional[bool] = None
    has_spare_key: Optional[bool] = None
    is_auction: Optional[bool] = None
    target_categories: Optional[str] = None
    processed_images: Optional[str] = None
    original_images: Optional[str] = None
    sold_buyer_id: Optional[int] = None
    sale_notes: Optional[str] = None
    vehicle_dossier_id: Optional[int] = None


class OffersResponse(BaseModel):
    """Entity response schema"""
    id: int
    code: Optional[str] = None
    supplier_id: Optional[int] = None
    title: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    year: Optional[str] = None
    color: Optional[str] = None
    mileage: Optional[str] = None
    price: Optional[float] = None
    supplier_price: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None
    negotiation_status: Optional[str] = None
    negotiation_substatus: Optional[str] = None
    negotiation_buyer_id: Optional[int] = None
    doc_status: Optional[str] = None
    vehicle_status: Optional[str] = None
    negotiation_deadline_hours: Optional[int] = None
    distributed_at: Optional[str] = None
    finalized_at: Optional[str] = None
    images: Optional[str] = None
    selected_images: Optional[str] = None
    fipe: Optional[str] = None
    plate: Optional[str] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    suggested_category: Optional[str] = None
    has_manual: Optional[bool] = None
    has_spare_key: Optional[bool] = None
    is_auction: Optional[bool] = None
    target_categories: Optional[str] = None
    processed_images: Optional[str] = None
    original_images: Optional[str] = None
    sold_buyer_id: Optional[int] = None
    sale_notes: Optional[str] = None
    vehicle_dossier_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OffersListResponse(BaseModel):
    """List response schema"""
    items: List[OffersResponse]
    total: int
    skip: int
    limit: int


class OffersBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[OffersData]


class OffersBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: OffersUpdateData


class OffersBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[OffersBatchUpdateItem]


class OffersBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=OffersListResponse)
async def query_offerss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query offerss with filtering, sorting, and pagination"""
    logger.debug(f"Querying offerss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = OffersService(db)
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
        logger.debug(f"Found {result['total']} offerss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid offers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying offerss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=OffersListResponse)
async def query_offerss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query offerss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying offerss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = OffersService(db)
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
        logger.debug(f"Found {result['total']} offerss")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid offers query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying offerss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=OffersResponse)
async def get_offers(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single offers by ID"""
    logger.debug(f"Fetching offers with id: {id}, fields={fields}")
    
    service = OffersService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Offers with id {id} not found")
            raise HTTPException(status_code=404, detail="Offers not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching offers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=OffersResponse, status_code=201)
async def create_offers(
    data: OffersData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new offers"""
    logger.debug(f"Creating new offers with data: {data}")
    
    service = OffersService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create offers")
        
        logger.info(f"Offers created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating offers: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating offers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[OffersResponse], status_code=201)
async def create_offerss_batch(
    request: OffersBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple offerss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} offerss")
    
    service = OffersService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} offerss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[OffersResponse])
async def update_offerss_batch(
    request: OffersBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple offerss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} offerss")
    
    service = OffersService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} offerss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=OffersResponse)
async def update_offers(
    id: int,
    data: OffersUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing offers"""
    logger.debug(f"Updating offers {id} with data: {data}")

    service = OffersService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Offers with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Offers not found")
        
        logger.info(f"Offers {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating offers {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating offers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_offerss_batch(
    request: OffersBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple offerss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} offerss")
    
    service = OffersService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} offerss successfully")
        return {"message": f"Successfully deleted {deleted_count} offerss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_offers(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single offers by ID"""
    logger.debug(f"Deleting offers with id: {id}")
    
    service = OffersService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Offers with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Offers not found")
        
        logger.info(f"Offers {id} deleted successfully")
        return {"message": "Offers deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting offers {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")