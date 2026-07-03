import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_admin_user
from services.whatsapp_settings import Whatsapp_settingsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/entities/whatsapp_settings",
    tags=["whatsapp_settings"],
    dependencies=[Depends(get_admin_user)],
)

SENSITIVE_SETTING_KEYS = {"EVOLUTION_API_KEY", "OPENAI_API_KEY", "APP_AI_KEY"}


def _mask_sensitive_setting(item):
    if item and getattr(item, "setting_key", "") in SENSITIVE_SETTING_KEYS:
        item.setting_value = "****"
    return item


def _reject_sensitive_setting_key(setting_key: Optional[str]) -> None:
    if setting_key in SENSITIVE_SETTING_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Use the secure integration settings endpoint for API keys.",
        )


# ---------- Pydantic Schemas ----------
class Whatsapp_settingsData(BaseModel):
    """Entity data schema (for create/update)"""
    setting_key: str
    setting_value: str = None


class Whatsapp_settingsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    setting_key: Optional[str] = None
    setting_value: Optional[str] = None


class Whatsapp_settingsResponse(BaseModel):
    """Entity response schema"""
    id: int
    setting_key: str
    setting_value: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Whatsapp_settingsListResponse(BaseModel):
    """List response schema"""
    items: List[Whatsapp_settingsResponse]
    total: int
    skip: int
    limit: int


class Whatsapp_settingsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Whatsapp_settingsData]


class Whatsapp_settingsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Whatsapp_settingsUpdateData


class Whatsapp_settingsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Whatsapp_settingsBatchUpdateItem]


class Whatsapp_settingsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Whatsapp_settingsListResponse)
async def query_whatsapp_settingss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query whatsapp_settingss with filtering, sorting, and pagination"""
    logger.debug(f"Querying whatsapp_settingss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Whatsapp_settingsService(db)
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
        result["items"] = [_mask_sensitive_setting(item) for item in result["items"]]
        logger.debug(f"Found {result['total']} whatsapp_settingss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_settingss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Whatsapp_settingsListResponse)
async def query_whatsapp_settingss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query whatsapp_settingss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying whatsapp_settingss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Whatsapp_settingsService(db)
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
        result["items"] = [_mask_sensitive_setting(item) for item in result["items"]]
        logger.debug(f"Found {result['total']} whatsapp_settingss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying whatsapp_settingss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Whatsapp_settingsResponse)
async def get_whatsapp_settings(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single whatsapp_settings by ID"""
    logger.debug(f"Fetching whatsapp_settings with id: {id}, fields={fields}")
    
    service = Whatsapp_settingsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Whatsapp_settings with id {id} not found")
            raise HTTPException(status_code=404, detail="Whatsapp_settings not found")
        
        return _mask_sensitive_setting(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching whatsapp_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Whatsapp_settingsResponse, status_code=201)
async def create_whatsapp_settings(
    data: Whatsapp_settingsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new whatsapp_settings"""
    logger.debug(f"Creating new whatsapp_settings with data: {data}")
    _reject_sensitive_setting_key(data.setting_key)
    
    service = Whatsapp_settingsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create whatsapp_settings")
        
        logger.info(f"Whatsapp_settings created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating whatsapp_settings: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating whatsapp_settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Whatsapp_settingsResponse], status_code=201)
async def create_whatsapp_settingss_batch(
    request: Whatsapp_settingsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple whatsapp_settingss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} whatsapp_settingss")
    
    service = Whatsapp_settingsService(db)
    results = []
    
    try:
        for item_data in request.items:
            _reject_sensitive_setting_key(item_data.setting_key)
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} whatsapp_settingss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Whatsapp_settingsResponse])
async def update_whatsapp_settingss_batch(
    request: Whatsapp_settingsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple whatsapp_settingss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} whatsapp_settingss")
    
    service = Whatsapp_settingsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            _reject_sensitive_setting_key(update_dict.get("setting_key"))
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} whatsapp_settingss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Whatsapp_settingsResponse)
async def update_whatsapp_settings(
    id: int,
    data: Whatsapp_settingsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing whatsapp_settings"""
    logger.debug(f"Updating whatsapp_settings {id} with data: {data}")
    _reject_sensitive_setting_key(data.setting_key)

    service = Whatsapp_settingsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Whatsapp_settings with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Whatsapp_settings not found")
        
        logger.info(f"Whatsapp_settings {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating whatsapp_settings {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating whatsapp_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_whatsapp_settingss_batch(
    request: Whatsapp_settingsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple whatsapp_settingss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} whatsapp_settingss")
    
    service = Whatsapp_settingsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} whatsapp_settingss successfully")
        return {"message": f"Successfully deleted {deleted_count} whatsapp_settingss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_whatsapp_settings(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single whatsapp_settings by ID"""
    logger.debug(f"Deleting whatsapp_settings with id: {id}")
    
    service = Whatsapp_settingsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Whatsapp_settings with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Whatsapp_settings not found")
        
        logger.info(f"Whatsapp_settings {id} deleted successfully")
        return {"message": "Whatsapp_settings deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting whatsapp_settings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
