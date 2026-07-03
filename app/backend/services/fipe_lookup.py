"""
FIPE price lookup service with consultation logging.

Provides direct FIPE code lookup and plate-based FIPE lookup,
automatically logging every consultation for audit purposes.
"""

import json
import logging
from typing import Dict, List, Optional

import httpx
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.fipe_consultation_logs import Fipe_consultation_logs
from services.consultarplaca import has_credentials, fetch_fipe
from services.formatting import (
    extract_consultarplaca_vehicle,
    extract_consultarplaca_fipe,
    format_brl_price,
    build_vehicle_description,
)

logger = logging.getLogger(__name__)

# BrasilAPI FIPE endpoints
BRASIL_API_FIPE_PRICE_URL = "https://brasilapi.com.br/api/fipe/preco/v1/{codigo_fipe}"


async def lookup_fipe_by_code(
    fipe_code: str,
    db: AsyncSession,
    phone: str = "",
    source: str = "admin",
    user_id: str = "",
) -> Dict:
    """
    Look up FIPE reference price by FIPE code.

    Uses BrasilAPI to get all price entries for a given FIPE code.
    Logs the consultation to the database.
    """
    clean_code = fipe_code.strip().upper().replace("-", "").replace(" ", "")
    if not clean_code or len(clean_code) < 5:
        return {"success": False, "error": "Código FIPE inválido."}

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.get(
                BRASIL_API_FIPE_PRICE_URL.format(codigo_fipe=clean_code),
            )

            if response.status_code == 404:
                result = {"success": False, "error": f"Código FIPE '{clean_code}' não encontrado."}
                await _log_consultation(db, phone=phone, fipe_code=clean_code, source=source, user_id=user_id, result_json=result, vehicle_description="", price_returned="")
                return result

            if response.status_code != 200:
                result = {"success": False, "error": f"Erro ao consultar FIPE: HTTP {response.status_code}"}
                await _log_consultation(db, phone=phone, fipe_code=clean_code, source=source, user_id=user_id, result_json=result, vehicle_description="", price_returned="")
                return result

            data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            result = {"success": False, "error": "Nenhum preço FIPE encontrado para este código."}
            await _log_consultation(db, phone=phone, fipe_code=clean_code, source=source, user_id=user_id, result_json=result, vehicle_description="", price_returned="")
            return result

        # Sort by reference month (most recent first)
        entries = sorted(data, key=lambda x: x.get("mesReferencia", ""), reverse=True)
        latest = entries[0]

        vehicle_desc = f"{latest.get('modelo', '')} {latest.get('anoModelo', '')}".strip()
        price_returned = latest.get("valor", "")

        # Build prices list
        prices = []
        for entry in entries[:12]:  # Last 12 months
            prices.append({
                "valor": entry.get("valor", ""),
                "mes_referencia": entry.get("mesReferencia", ""),
                "ano_modelo": entry.get("anoModelo", ""),
                "combustivel": entry.get("combustivel", ""),
                "codigo_fipe": entry.get("codigoFipe", clean_code),
                "modelo": entry.get("modelo", ""),
            })

        result = {
            "success": True,
            "source": "brasilapi",
            "fipe_code": clean_code,
            "vehicle_description": vehicle_desc,
            "price_returned": price_returned,
            "reference_month": latest.get("mesReferencia", ""),
            "prices": prices,
        }

        # Log the consultation
        consultation = await _log_consultation(
            db, phone=phone, fipe_code=clean_code, source=source, user_id=user_id,
            result_json=result, vehicle_description=vehicle_desc, price_returned=price_returned,
        )
        result["consultation_id"] = consultation.id if consultation else None

        logger.info(f"FIPE lookup by code: {clean_code} -> {vehicle_desc} ({price_returned})")
        return result

    except httpx.ConnectError:
        return {"success": False, "error": "Não foi possível conectar à BrasilAPI. Verifique a conexão."}
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout ao consultar FIPE. Tente novamente."}
    except Exception as e:
        logger.error(f"FIPE lookup by code error: {e}")
        return {"success": False, "error": f"Erro inesperado: {str(e)}"}


async def lookup_fipe_by_plate(
    plate: str,
    db: AsyncSession,
    phone: str = "",
    source: str = "admin",
    user_id: str = "",
) -> Dict:
    """
    Look up FIPE price by license plate.

    Uses ConsultarPlaca (primary) or BrasilAPI (fallback) to get vehicle data
    and FIPE prices. Logs the consultation.
    """
    clean_plate = plate.strip().upper().replace("-", "").replace(" ", "")
    if not clean_plate or len(clean_plate) < 7:
        return {"success": False, "error": "Placa inválida. Use o formato ABC1D23 ou ABC1234."}

    # Try ConsultarPlaca first
    if has_credentials():
        result = await _lookup_fipe_consultarplaca(clean_plate)
        if result.get("success"):
            consultation = await _log_consultation(
                db, phone=phone, plate=clean_plate, fipe_code=result.get("fipe_code", ""),
                source=source, user_id=user_id, result_json=result,
                vehicle_description=result.get("vehicle_description", ""),
                price_returned=result.get("fipe_price", ""),
            )
            result["consultation_id"] = consultation.id if consultation else None
            return result

    # Fallback to BrasilAPI plate lookup + FIPE price
    result = await _lookup_fipe_brasilapi_plate(clean_plate)
    consultation = await _log_consultation(
        db, phone=phone, plate=clean_plate, fipe_code=result.get("fipe_code", ""),
        source=source, user_id=user_id, result_json=result,
        vehicle_description=result.get("vehicle_description", ""),
        price_returned=result.get("fipe_price", ""),
    )
    result["consultation_id"] = consultation.id if consultation else None
    return result


async def _lookup_fipe_consultarplaca(plate: str) -> Dict:
    """Look up FIPE price using ConsultarPlaca API (shared client)."""
    data = await fetch_fipe(plate)

    if not data.get("success", True):
        return data

    # Extract using shared parsers
    vehicle = extract_consultarplaca_vehicle(data)
    fipe = extract_consultarplaca_fipe(data)

    vehicle_desc = build_vehicle_description(
        vehicle["brand"], vehicle["model"], year=vehicle["year"]
    )

    return {
        "success": True,
        "source": "consultarplaca",
        "plate": vehicle["plate"] or plate,
        "brand": vehicle["brand"],
        "model": vehicle["model"],
        "year": vehicle["year"],
        "color": vehicle["color"],
        "fuel": vehicle["fuel"],
        "vehicle_description": vehicle_desc,
        "fipe_code": fipe["fipe_code"],
        "fipe_price": fipe["fipe_price"],
        "fipe_reference": fipe["fipe_reference"],
        "fipe_versions": fipe["fipe_versions"],
    }


async def _lookup_fipe_brasilapi_plate(plate: str) -> Dict:
    """Look up FIPE price using BrasilAPI plate lookup + FIPE price."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.get(
                f"https://brasilapi.com.br/api/placa/v1/{plate}",
            )

            if response.status_code != 200:
                return {"success": False, "error": f"Placa '{plate}' não encontrada."}

            data = response.json()

        brand = data.get("marca", "")
        model = data.get("modelo", "")
        year = str(data.get("ano", ""))
        vehicle_desc = build_vehicle_description(brand, model, year=year)
        fipe_code = data.get("codigoFipe", "")
        fipe_price = ""
        fipe_versions = []

        # Get FIPE price if code available
        if fipe_code:
            try:
                async with httpx.AsyncClient(timeout=15.0) as http:
                    fipe_resp = await http.get(
                        BRASIL_API_FIPE_PRICE_URL.format(codigo_fipe=fipe_code),
                    )
                    if fipe_resp.status_code == 200:
                        fipe_data = fipe_resp.json()
                        if isinstance(fipe_data, list) and len(fipe_data) > 0:
                            entries = sorted(fipe_data, key=lambda x: x.get("mesReferencia", ""), reverse=True)
                            latest = entries[0]
                            fipe_price = latest.get("valor", "")
                            for entry in entries[:12]:
                                fipe_versions.append({
                                    "codigo_fipe": entry.get("codigoFipe", fipe_code),
                                    "modelo_versao": entry.get("modelo", ""),
                                    "preco": entry.get("valor", ""),
                                    "mes_referencia": entry.get("mesReferencia", ""),
                                })
            except Exception as e:
                logger.warning(f"FIPE price lookup failed for code {fipe_code}: {e}")

        return {
            "success": True,
            "source": "brasilapi",
            "plate": plate,
            "brand": brand,
            "model": model,
            "year": year,
            "color": data.get("cor", ""),
            "fuel": data.get("combustivel", ""),
            "vehicle_description": vehicle_desc,
            "fipe_code": fipe_code,
            "fipe_price": fipe_price,
            "fipe_reference": "",
            "fipe_versions": fipe_versions,
        }

    except Exception as e:
        logger.error(f"BrasilAPI FIPE plate lookup error: {e}")
        return {"success": False, "error": f"Erro inesperado: {str(e)}"}


async def _log_consultation(
    db: AsyncSession,
    phone: str = "",
    plate: str = "",
    fipe_code: str = "",
    source: str = "admin",
    user_id: str = "",
    result_json: Dict = None,
    vehicle_description: str = "",
    price_returned: str = "",
) -> Optional[Fipe_consultation_logs]:
    """Log a FIPE consultation to the database for audit purposes."""
    try:
        log_entry = Fipe_consultation_logs(
            phone=phone or "unknown",
            plate=plate or None,
            fipe_code=fipe_code or None,
            vehicle_description=vehicle_description or None,
            price_returned=price_returned or None,
            source=source,
            user_id=user_id or None,
            result_json=json.dumps(result_json, ensure_ascii=False, default=str) if result_json else None,
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        logger.info(f"FIPE consultation logged: id={log_entry.id}, plate={plate}, fipe_code={fipe_code}")
        return log_entry
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to log FIPE consultation: {e}")
        return None


async def get_consultation_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    phone: str = "",
    plate: str = "",
    fipe_code: str = "",
    source: str = "",
) -> Dict:
    """Get paginated FIPE consultation logs with optional filters."""
    try:
        query = select(Fipe_consultation_logs)
        count_query = select(func.count(Fipe_consultation_logs.id))

        if phone:
            query = query.where(Fipe_consultation_logs.phone.ilike(f"%{phone}%"))
            count_query = count_query.where(Fipe_consultation_logs.phone.ilike(f"%{phone}%"))
        if plate:
            query = query.where(Fipe_consultation_logs.plate.ilike(f"%{plate}%"))
            count_query = count_query.where(Fipe_consultation_logs.plate.ilike(f"%{plate}%"))
        if fipe_code:
            query = query.where(Fipe_consultation_logs.fipe_code.ilike(f"%{fipe_code}%"))
            count_query = count_query.where(Fipe_consultation_logs.fipe_code.ilike(f"%{fipe_code}%"))
        if source:
            query = query.where(Fipe_consultation_logs.source == source)
            count_query = count_query.where(Fipe_consultation_logs.source == source)

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(desc(Fipe_consultation_logs.id)).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return {
            "items": [_format_log(item) for item in items],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error fetching FIPE consultation logs: {e}")
        raise


def _format_log(item: Fipe_consultation_logs) -> Dict:
    """Format a consultation log entry for API response."""
    parsed_result = None
    if item.result_json:
        try:
            parsed_result = json.loads(item.result_json)
        except json.JSONDecodeError:
            parsed_result = {"raw": item.result_json}

    return {
        "id": item.id,
        "phone": item.phone,
        "plate": item.plate,
        "fipe_code": item.fipe_code,
        "vehicle_description": item.vehicle_description,
        "price_returned": item.price_returned,
        "source": item.source,
        "user_id": item.user_id,
        "result": parsed_result,
        "created_at": item.created_at.isoformat() if item.created_at and hasattr(item.created_at, "isoformat") else str(item.created_at or ""),
        "updated_at": item.updated_at.isoformat() if item.updated_at and hasattr(item.updated_at, "isoformat") else str(item.updated_at or ""),
    }