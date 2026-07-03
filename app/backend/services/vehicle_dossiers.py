import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from models.buyers import Buyers
from models.negotiation_history import Negotiation_history
from models.offers import Offers
from models.vehicle_dossier_access import Vehicle_dossier_access
from models.vehicle_dossier_files import Vehicle_dossier_files
from models.vehicle_dossiers import Vehicle_dossiers
from models.vehicle_plate_consultations import Vehicle_plate_consultations
from schemas.auth import UserResponse
from schemas.storage import FileUpDownRequest
from services.storage import StorageService
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


DOSSIER_BUCKET = os.environ.get("VEHICLE_DOSSIER_BUCKET", "vehicle-images")


def normalize_plate(plate: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (plate or "").upper())


class VehicleDossierService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_buyer_for_user(self, user: UserResponse) -> Optional[Buyers]:
        conditions = []
        if user.id:
            conditions.append(Buyers.user_id == user.id)
        if user.email:
            conditions.append(Buyers.email == user.email)
        if not conditions:
            return None

        result = await self.db.execute(select(Buyers).where(or_(*conditions)))
        return result.scalar_one_or_none()

    async def get_or_create_dossier(
        self,
        plate: str,
        offer_id: Optional[int] = None,
        sold_buyer_id: Optional[int] = None,
        status: str = "active",
    ) -> Vehicle_dossiers:
        clean_plate = normalize_plate(plate)
        if not clean_plate:
            raise ValueError("Placa obrigatoria para criar dossie")

        dossier = None
        if offer_id:
            result = await self.db.execute(select(Vehicle_dossiers).where(Vehicle_dossiers.offer_id == offer_id))
            dossier = result.scalar_one_or_none()

        if not dossier:
            result = await self.db.execute(
                select(Vehicle_dossiers)
                .where(Vehicle_dossiers.plate == clean_plate)
                .order_by(Vehicle_dossiers.id.desc())
            )
            dossier = result.scalars().first()

        if dossier:
            changed = False
            if offer_id and not dossier.offer_id:
                dossier.offer_id = offer_id
                changed = True
            if sold_buyer_id and dossier.sold_buyer_id != sold_buyer_id:
                dossier.sold_buyer_id = sold_buyer_id
                changed = True
            if status and dossier.status != status:
                dossier.status = status
                changed = True
            if changed:
                await self.db.commit()
                await self.db.refresh(dossier)
            return dossier

        dossier = Vehicle_dossiers(
            plate=clean_plate,
            offer_id=offer_id,
            sold_buyer_id=sold_buyer_id,
            status=status,
        )
        self.db.add(dossier)
        await self.db.commit()
        await self.db.refresh(dossier)
        return dossier

    async def record_plate_consultation(
        self,
        plate: str,
        result_data: dict[str, Any],
        user: Optional[UserResponse] = None,
        offer_id: Optional[int] = None,
        dossier_id: Optional[int] = None,
    ) -> Vehicle_plate_consultations:
        clean_plate = normalize_plate(plate or result_data.get("plate", ""))
        if not clean_plate:
            raise ValueError("Placa obrigatoria para registrar consulta")

        dossier = None
        if dossier_id:
            dossier = await self.get_dossier(dossier_id)
        elif offer_id:
            offer = await self.get_offer(offer_id)
            dossier = await self.get_or_create_dossier(offer.plate or clean_plate, offer_id=offer.id)
        else:
            dossier = await self.get_or_create_dossier(clean_plate)

        consultation = Vehicle_plate_consultations(
            plate=clean_plate,
            offer_id=offer_id,
            dossier_id=dossier.id if dossier else dossier_id,
            requested_by_user_id=user.id if user else None,
            requested_by_role=user.role if user else "system",
            source=result_data.get("source", ""),
            success=bool(result_data.get("success")),
            result_json=json.dumps(result_data, ensure_ascii=False),
            error_message="" if result_data.get("success") else result_data.get("error", ""),
        )
        self.db.add(consultation)
        await self.db.commit()
        await self.db.refresh(consultation)
        return consultation

    async def get_offer(self, offer_id: int) -> Offers:
        result = await self.db.execute(select(Offers).where(Offers.id == offer_id))
        offer = result.scalar_one_or_none()
        if not offer:
            raise ValueError("Oferta nao encontrada")
        return offer

    async def get_dossier(self, dossier_id: int) -> Vehicle_dossiers:
        result = await self.db.execute(select(Vehicle_dossiers).where(Vehicle_dossiers.id == dossier_id))
        dossier = result.scalar_one_or_none()
        if not dossier:
            raise ValueError("Dossie nao encontrado")
        return dossier

    async def search_by_plate(self, plate: str) -> list[Vehicle_dossiers]:
        clean_plate = normalize_plate(plate)
        if not clean_plate:
            return []
        result = await self.db.execute(
            select(Vehicle_dossiers)
            .where(Vehicle_dossiers.plate.like(f"%{clean_plate}%"))
            .order_by(Vehicle_dossiers.updated_at.desc(), Vehicle_dossiers.id.desc())
        )
        return list(result.scalars().all())

    async def list_admin_dossiers(self, limit: int = 100, offset: int = 0) -> list[Vehicle_dossiers]:
        result = await self.db.execute(
            select(Vehicle_dossiers)
            .order_by(Vehicle_dossiers.updated_at.desc(), Vehicle_dossiers.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def register_sale(
        self,
        offer_id: int,
        buyer_id: int,
        notes: str = "",
    ) -> Vehicle_dossiers:
        offer = await self.get_offer(offer_id)
        if not offer.plate:
            raise ValueError("A oferta precisa ter placa para registrar venda no dossie")

        buyer = await self.db.get(Buyers, buyer_id)
        if not buyer:
            raise ValueError("Comprador nao encontrado")

        sold_at = datetime.now(timezone.utc)
        offer.status = "sold"
        offer.sold_buyer_id = buyer_id
        offer.negotiation_buyer_id = buyer_id
        offer.sold_at = sold_at
        offer.finalized_at = sold_at.isoformat()
        offer.sale_notes = notes

        dossier = await self.get_or_create_dossier(
            offer.plate,
            offer_id=offer.id,
            sold_buyer_id=buyer_id,
            status="sold",
        )
        offer.vehicle_dossier_id = dossier.id

        access_result = await self.db.execute(
            select(Vehicle_dossier_access).where(
                Vehicle_dossier_access.dossier_id == dossier.id,
                Vehicle_dossier_access.buyer_id == buyer_id,
            )
        )
        access = access_result.scalar_one_or_none()
        if not access:
            access = Vehicle_dossier_access(
                dossier_id=dossier.id,
                buyer_id=buyer_id,
                user_id=buyer.user_id,
                can_view_consultations=True,
                can_view_files=True,
            )
            self.db.add(access)
        else:
            access.user_id = buyer.user_id or access.user_id
            access.can_view_consultations = True
            access.can_view_files = True

        history = Negotiation_history(
            offer_id=offer.id,
            admin_name="Administrador",
            previous_status=offer.negotiation_status,
            new_status="sold",
            buyer_id=buyer_id,
            observations=notes or "Venda registrada no dossie do veiculo",
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(dossier)
        return dossier

    async def add_file(
        self,
        dossier_id: int,
        file_name: str,
        file_type: str,
        mime_type: str = "",
        file_size: Optional[int] = None,
        is_released_to_buyer: bool = False,
        user: Optional[UserResponse] = None,
    ) -> dict[str, Any]:
        dossier = await self.get_dossier(dossier_id)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "-", file_name or "arquivo")
        object_key = f"dossier-{dossier.id}-{uuid.uuid4().hex[:12]}-{safe_name}"

        storage = StorageService()
        upload = await storage.create_upload_url(FileUpDownRequest(bucket_name=DOSSIER_BUCKET, object_key=object_key))

        file_row = Vehicle_dossier_files(
            dossier_id=dossier.id,
            offer_id=dossier.offer_id,
            plate=dossier.plate,
            file_type=file_type,
            file_name=file_name,
            storage_bucket=DOSSIER_BUCKET,
            storage_key=object_key,
            mime_type=mime_type,
            file_size=file_size,
            uploaded_by_user_id=user.id if user else None,
            is_admin_only=not is_released_to_buyer,
            is_released_to_buyer=is_released_to_buyer,
        )
        self.db.add(file_row)
        await self.db.commit()
        await self.db.refresh(file_row)

        return {
            "file": file_row,
            "upload_url": upload.upload_url,
            "expires_at": upload.expires_at,
        }

    async def update_file_permissions(
        self,
        file_id: int,
        is_released_to_buyer: bool,
        file_type: Optional[str] = None,
    ) -> Vehicle_dossier_files:
        file_row = await self.db.get(Vehicle_dossier_files, file_id)
        if not file_row:
            raise ValueError("Arquivo nao encontrado")
        file_row.is_released_to_buyer = is_released_to_buyer
        file_row.is_admin_only = not is_released_to_buyer
        if file_type:
            file_row.file_type = file_type
        await self.db.commit()
        await self.db.refresh(file_row)
        return file_row

    async def delete_file(self, file_id: int) -> None:
        file_row = await self.db.get(Vehicle_dossier_files, file_id)
        if not file_row:
            raise ValueError("Arquivo nao encontrado")
        await self.db.delete(file_row)
        await self.db.commit()

    async def create_download_url(self, file_row: Vehicle_dossier_files) -> str:
        storage = StorageService()
        download = await storage.create_download_url(
            FileUpDownRequest(bucket_name=file_row.storage_bucket or DOSSIER_BUCKET, object_key=file_row.storage_key)
        )
        return download.download_url

    async def assemble_detail(self, dossier: Vehicle_dossiers, buyer_view: bool = False) -> dict[str, Any]:
        offer = None
        if dossier.offer_id:
            result = await self.db.execute(select(Offers).where(Offers.id == dossier.offer_id))
            offer = result.scalar_one_or_none()

        buyer = None
        buyer_id = dossier.sold_buyer_id or (offer.sold_buyer_id if offer else None)
        if buyer_id:
            buyer = await self.db.get(Buyers, buyer_id)

        consultations_result = await self.db.execute(
            select(Vehicle_plate_consultations)
            .where(Vehicle_plate_consultations.dossier_id == dossier.id)
            .order_by(Vehicle_plate_consultations.created_at.desc(), Vehicle_plate_consultations.id.desc())
        )
        consultations = list(consultations_result.scalars().all())

        files_query = select(Vehicle_dossier_files).where(Vehicle_dossier_files.dossier_id == dossier.id)
        if buyer_view:
            files_query = files_query.where(Vehicle_dossier_files.is_released_to_buyer == True)
        files_result = await self.db.execute(
            files_query.order_by(Vehicle_dossier_files.created_at.desc(), Vehicle_dossier_files.id.desc())
        )
        files = list(files_result.scalars().all())

        history = []
        if offer:
            hist_result = await self.db.execute(
                select(Negotiation_history)
                .where(Negotiation_history.offer_id == offer.id)
                .order_by(Negotiation_history.created_at.desc(), Negotiation_history.id.desc())
            )
            history = list(hist_result.scalars().all())

        return {
            "dossier": dossier,
            "offer": offer,
            "buyer": buyer,
            "consultations": consultations,
            "files": files,
            "negotiation_history": history,
        }

    async def assert_buyer_can_access(self, dossier_id: int, user: UserResponse) -> Vehicle_dossiers:
        buyer = await self.get_buyer_for_user(user)
        if not buyer:
            raise PermissionError("Comprador nao vinculado ao usuario atual")
        result = await self.db.execute(
            select(Vehicle_dossier_access).where(
                Vehicle_dossier_access.dossier_id == dossier_id,
                Vehicle_dossier_access.buyer_id == buyer.id,
            )
        )
        access = result.scalar_one_or_none()
        if not access:
            raise PermissionError("Dossie nao liberado para este comprador")
        return await self.get_dossier(dossier_id)

    async def list_buyer_dossiers(self, user: UserResponse) -> list[Vehicle_dossiers]:
        buyer = await self.get_buyer_for_user(user)
        if not buyer:
            return []
        result = await self.db.execute(
            select(Vehicle_dossiers)
            .join(Vehicle_dossier_access, Vehicle_dossier_access.dossier_id == Vehicle_dossiers.id)
            .where(Vehicle_dossier_access.buyer_id == buyer.id)
            .order_by(Vehicle_dossiers.updated_at.desc(), Vehicle_dossiers.id.desc())
        )
        return list(result.scalars().all())
