"""FIPE lookup router — plate/code lookups and consultation logs."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.fipe_lookup import lookup_fipe_by_code, lookup_fipe_by_plate, get_consultation_logs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fipe", tags=["fipe"])


# ---------- Pydantic Schemas ----------

class FipePlateLookupRequest(BaseModel):
    plate: str


class FipeCodeLookupRequest(BaseModel):
    fipe_code: str


# ---------- Routes ----------

@router.post("/lookup-by-plate")
async def fipe_lookup_by_plate(
    body: FipePlateLookupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Look up FIPE price by license plate."""
    result = await lookup_fipe_by_plate(
        plate=body.plate,
        db=db,
        source="admin",
    )
    return result


@router.post("/lookup-by-code")
async def fipe_lookup_by_code(
    body: FipeCodeLookupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Look up FIPE price by FIPE code."""
    result = await lookup_fipe_by_code(
        fipe_code=body.fipe_code,
        db=db,
        source="admin",
    )
    return result


@router.get("/consultation-logs")
async def fipe_consultation_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    phone: str = Query("", description="Filter by phone"),
    plate: str = Query("", description="Filter by plate"),
    fipe_code: str = Query("", description="Filter by FIPE code"),
    source: str = Query("", description="Filter by source"),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated FIPE consultation logs with optional filters."""
    result = await get_consultation_logs(
        db=db,
        skip=skip,
        limit=limit,
        phone=phone,
        plate=plate,
        fipe_code=fipe_code,
        source=source,
    )
    return result