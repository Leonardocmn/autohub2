import json
from typing import Optional

from core.database import get_db
from dependencies.auth import get_admin_user, get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from schemas.auth import UserResponse
from services.plate_lookup import lookup_plate
from services.vehicle_dossiers import VehicleDossierService, normalize_plate
from sqlalchemy.ext.asyncio import AsyncSession
from models.vehicle_dossier_files import Vehicle_dossier_files

_vehicle_dossier_router = APIRouter(prefix="/api/v1/vehicle-dossiers", tags=["vehicle-dossiers"])
buyer_router = APIRouter(prefix="/api/v1/buyer/vehicle-dossiers", tags=["buyer-vehicle-dossiers"])


class PlateLookupRequest(BaseModel):
    plate: str
    offer_id: Optional[int] = None
    dossier_id: Optional[int] = None


class RegisterSaleRequest(BaseModel):
    offer_id: int
    buyer_id: int
    notes: str = ""


class CreateDossierRequest(BaseModel):
    plate: str
    offer_id: Optional[int] = None


class AddFileRequest(BaseModel):
    file_name: str
    file_type: str = "document"
    mime_type: str = ""
    file_size: Optional[int] = None
    is_released_to_buyer: bool = False


class UpdateFileRequest(BaseModel):
    is_released_to_buyer: bool
    file_type: Optional[str] = None


def _dt(value):
    return value.isoformat() if hasattr(value, "isoformat") else (value or "")


def _model_dict(obj, fields: list[str]) -> Optional[dict]:
    if not obj:
        return None
    data = {}
    for field in fields:
        value = getattr(obj, field, None)
        data[field] = _dt(value) if field.endswith("_at") or field in ("created_at", "updated_at") else value
    return data


def _consultation_dict(item) -> dict:
    parsed = None
    if item.result_json:
        try:
            parsed = json.loads(item.result_json)
        except json.JSONDecodeError:
            parsed = {"raw": item.result_json}
    return {
        "id": item.id,
        "plate": item.plate,
        "offer_id": item.offer_id,
        "dossier_id": item.dossier_id,
        "requested_by_user_id": item.requested_by_user_id,
        "requested_by_role": item.requested_by_role,
        "source": item.source,
        "success": item.success,
        "result": parsed,
        "error_message": item.error_message,
        "created_at": _dt(item.created_at),
    }


def _file_dict(item) -> dict:
    return {
        "id": item.id,
        "dossier_id": item.dossier_id,
        "offer_id": item.offer_id,
        "plate": item.plate,
        "file_type": item.file_type,
        "file_name": item.file_name,
        "storage_bucket": item.storage_bucket,
        "storage_key": item.storage_key,
        "public_url": item.public_url,
        "mime_type": item.mime_type,
        "file_size": item.file_size,
        "is_admin_only": item.is_admin_only,
        "is_released_to_buyer": item.is_released_to_buyer,
        "created_at": _dt(item.created_at),
    }


def _history_dict(item) -> dict:
    return {
        "id": item.id,
        "offer_id": item.offer_id,
        "admin_name": item.admin_name,
        "previous_status": item.previous_status,
        "new_status": item.new_status,
        "buyer_id": item.buyer_id,
        "observations": item.observations,
        "created_at": _dt(item.created_at),
    }


def _detail_response(detail: dict) -> dict:
    dossier = detail["dossier"]
    offer = detail.get("offer")
    buyer = detail.get("buyer")
    return {
        "dossier": _model_dict(
            dossier,
            ["id", "plate", "offer_id", "sold_buyer_id", "status", "created_at", "updated_at"],
        ),
        "offer": _model_dict(
            offer,
            [
                "id",
                "code",
                "title",
                "brand",
                "model",
                "year",
                "color",
                "mileage",
                "price",
                "description",
                "status",
                "negotiation_status",
                "negotiation_substatus",
                "negotiation_buyer_id",
                "sold_buyer_id",
                "sold_at",
                "sale_notes",
                "finalized_at",
                "plate",
                "images",
                "selected_images",
                "processed_images",
                "original_images",
                "created_at",
            ],
        ),
        "buyer": _model_dict(buyer, ["id", "name", "phone", "email", "user_id", "status"]),
        "consultations": [_consultation_dict(item) for item in detail.get("consultations", [])],
        "files": [_file_dict(item) for item in detail.get("files", [])],
        "negotiation_history": [_history_dict(item) for item in detail.get("negotiation_history", [])],
    }


@_vehicle_dossier_router.get("")
async def list_dossiers(
    plate: str = Query("", description="Optional plate search"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    dossiers = await service.search_by_plate(plate) if plate else await service.list_admin_dossiers(limit, offset)
    return {
        "items": [
            _model_dict(item, ["id", "plate", "offer_id", "sold_buyer_id", "status", "created_at", "updated_at"])
            for item in dossiers
        ],
        "total": len(dossiers),
    }


@_vehicle_dossier_router.post("")
async def create_dossier(
    data: CreateDossierRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        dossier = await service.get_or_create_dossier(data.plate, offer_id=data.offer_id)
        return _model_dict(dossier, ["id", "plate", "offer_id", "sold_buyer_id", "status", "created_at", "updated_at"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@_vehicle_dossier_router.get("/{dossier_id}")
async def get_dossier(
    dossier_id: int,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        dossier = await service.get_dossier(dossier_id)
        return _detail_response(await service.assemble_detail(dossier))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@_vehicle_dossier_router.post("/plate-lookup")
async def lookup_plate_and_record(
    data: PlateLookupRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await lookup_plate(data.plate)
    service = VehicleDossierService(db)
    try:
        consultation = await service.record_plate_consultation(
            data.plate,
            result,
            user=current_user,
            offer_id=data.offer_id,
            dossier_id=data.dossier_id,
        )
        return {
            **result,
            "plate": normalize_plate(result.get("plate") or data.plate),
            "consultation_id": consultation.id,
            "dossier_id": consultation.dossier_id,
        }
    except ValueError as exc:
        if result.get("success"):
            raise HTTPException(status_code=400, detail=str(exc))
        return result


@_vehicle_dossier_router.post("/register-sale")
async def register_sale(
    data: RegisterSaleRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        dossier = await service.register_sale(data.offer_id, data.buyer_id, data.notes)
        return {
            "success": True,
            "dossier": _model_dict(
                dossier,
                ["id", "plate", "offer_id", "sold_buyer_id", "status", "created_at", "updated_at"],
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@_vehicle_dossier_router.post("/{dossier_id}/files")
async def add_file(
    dossier_id: int,
    data: AddFileRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        result = await service.add_file(
            dossier_id,
            file_name=data.file_name,
            file_type=data.file_type,
            mime_type=data.mime_type,
            file_size=data.file_size,
            is_released_to_buyer=data.is_released_to_buyer,
            user=current_user,
        )
        return {
            "file": _file_dict(result["file"]),
            "upload_url": result["upload_url"],
            "expires_at": result["expires_at"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@_vehicle_dossier_router.put("/files/{file_id}")
async def update_file(
    file_id: int,
    data: UpdateFileRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        item = await service.update_file_permissions(file_id, data.is_released_to_buyer, data.file_type)
        return _file_dict(item)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@_vehicle_dossier_router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        await service.delete_file(file_id)
        return {"success": True}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@_vehicle_dossier_router.post("/files/{file_id}/download-url")
async def admin_download_file(
    file_id: int,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    file_row = await db.get(Vehicle_dossier_files, file_id)
    if not file_row:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    return {"download_url": await service.create_download_url(file_row)}


@buyer_router.get("")
async def list_buyer_dossiers(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    dossiers = await service.list_buyer_dossiers(current_user)
    return {
        "items": [
            _model_dict(item, ["id", "plate", "offer_id", "sold_buyer_id", "status", "created_at", "updated_at"])
            for item in dossiers
        ],
        "total": len(dossiers),
    }


@buyer_router.get("/{dossier_id}")
async def get_buyer_dossier(
    dossier_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    try:
        dossier = await service.assert_buyer_can_access(dossier_id, current_user)
        return _detail_response(await service.assemble_detail(dossier, buyer_view=True))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@buyer_router.post("/files/{file_id}/download-url")
async def buyer_download_file(
    file_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = VehicleDossierService(db)
    file_row = await db.get(Vehicle_dossier_files, file_id)
    if not file_row or not file_row.is_released_to_buyer:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    try:
        await service.assert_buyer_can_access(file_row.dossier_id, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return {"download_url": await service.create_download_url(file_row)}


router = [_vehicle_dossier_router, buyer_router]

