"""
Vehicle plate lookup service using ConsultarPlaca API (primary) and BrasilAPI (fallback).

ConsultarPlaca API (https://api.consultarplaca.com.br):
- Rich vehicle data: brand, model, year, color, fuel, chassi, municipality, UF, segment
- FIPE price with historical data and multiple versions
- Authentication: Basic Auth (email + API key)

BrasilAPI (https://brasilapi.com.br):
- Free, no API key required
- Basic vehicle data + FIPE code lookup
- Fallback when ConsultarPlaca credentials are not configured
"""

import logging
from typing import Dict

import httpx

from services.consultarplaca import has_credentials, fetch_fipe
from services.formatting import (
    extract_consultarplaca_vehicle,
    extract_consultarplaca_fipe,
    format_brl_price,
)

logger = logging.getLogger(__name__)

# BrasilAPI (fallback)
BRASIL_API_PLATE_URL = "https://brasilapi.com.br/api/placa/v1/{plate}"
BRASIL_API_FIPE_PRICE_URL = "https://brasilapi.com.br/api/fipe/preco/v1/{codigo_fipe}"


async def lookup_plate(plate: str) -> Dict:
    """
    Look up vehicle information by license plate.

    Uses ConsultarPlaca API (primary) if credentials are configured,
    otherwise falls back to BrasilAPI (free, no key required).

    Returns a dict with:
      - success: bool
      - source: "consultarplaca" | "brasilapi"
      - plate, brand, model, year, color, fuel, chassi, fipe_code, fipe_price
      - ConsultarPlaca extras: municipality, uf, segment, procedence,
        ano_fabricacao, ano_modelo, fipe_versions (list of FIPE entries)
      - error: str (on failure)
    """
    # Clean plate: remove spaces, dashes, convert to uppercase
    clean_plate = plate.strip().upper().replace("-", "").replace(" ", "")

    if not clean_plate or len(clean_plate) < 7:
        return {"success": False, "error": "Placa inválida. Use o formato ABC1D23 ou ABC1234."}

    # Try ConsultarPlaca first if credentials are available
    if has_credentials():
        result = await _lookup_consultarplaca(clean_plate)
        if result.get("success"):
            return result
        # If ConsultarPlaca fails, log and fall back to BrasilAPI
        logger.warning(
            f"ConsultarPlaca lookup failed for {clean_plate}: {result.get('error')}. "
            "Falling back to BrasilAPI."
        )

    # Fallback to BrasilAPI
    return await _lookup_brasilapi(clean_plate)


async def _lookup_consultarplaca(plate: str) -> Dict:
    """
    Look up vehicle information using ConsultarPlaca API.

    Uses the shared fetch_fipe client which returns the full API response.
    """
    data = await fetch_fipe(plate)

    if not data.get("success", True):  # fetch_fipe returns error dict on failure
        return data

    # Extract vehicle data using shared parser
    vehicle = extract_consultarplaca_vehicle(data)
    fipe = extract_consultarplaca_fipe(data)

    result = {
        "success": True,
        "source": "consultarplaca",
        "plate": vehicle["plate"] or plate,
        "brand": vehicle["brand"],
        "model": vehicle["model"],
        "year": vehicle["year"],
        "color": vehicle["color"],
        "fuel": vehicle["fuel"],
        "chassi": vehicle["chassi"],
        "segment": vehicle["segment"],
        "procedence": vehicle["procedence"],
        "municipality": vehicle["municipality"],
        "uf": vehicle["uf"],
        "ano_fabricacao": vehicle["ano_fabricacao"],
        "ano_modelo": vehicle["ano_modelo"],
        "vehicle_type": vehicle["vehicle_type"],
        "sub_segment": vehicle["sub_segment"],
        "power": vehicle["power"],
        "displacement": vehicle["displacement"],
        # FIPE data
        "fipe_code": fipe["fipe_code"],
        "fipe_price": fipe["fipe_price"],
        "fipe_reference": fipe["fipe_reference"],
        "fipe_versions": fipe["fipe_versions"],
    }

    logger.info(
        f"ConsultarPlaca lookup success: {plate} -> "
        f"{result['brand']} {result['model']} {result['year']} "
        f"(FIPE: {result['fipe_price']}, {len(result.get('fipe_versions', []))} versões)"
    )
    return result


async def _lookup_brasilapi(plate: str) -> Dict:
    """
    Look up vehicle information using BrasilAPI (fallback).

    Free API, no credentials required. Returns basic vehicle data.
    FIPE price requires a separate lookup by FIPE code.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.get(
                BRASIL_API_PLATE_URL.format(plate=plate),
            )

            if response.status_code == 404:
                return {"success": False, "error": f"Placa '{plate}' não encontrada."}

            if response.status_code != 200:
                logger.error(f"BrasilAPI plate lookup error: {response.status_code} - {response.text[:300]}")
                return {"success": False, "error": f"Erro ao consultar placa: HTTP {response.status_code}"}

            data = response.json()

        # Extract vehicle info from BrasilAPI response
        result = {
            "success": True,
            "source": "brasilapi",
            "plate": plate,
            "brand": data.get("marca", ""),
            "model": data.get("modelo", ""),
            "year": str(data.get("ano", "")),
            "color": data.get("cor", ""),
            "fuel": data.get("combustivel", ""),
            "chassi": data.get("chassi", ""),
            "uf": data.get("uf", ""),
            "segment": "",
            "procedence": "",
            "municipality": "",
            "ano_fabricacao": "",
            "ano_modelo": "",
            "vehicle_type": "",
            "sub_segment": "",
            "power": "",
            "displacement": "",
            "fipe_code": "",
            "fipe_price": "",
            "fipe_reference": "",
            "fipe_versions": [],
        }

        # Try to get FIPE price if codigoFipe is available
        codigo_fipe = data.get("codigoFipe", "")
        if codigo_fipe:
            result["fipe_code"] = codigo_fipe
            fipe_result = await _lookup_fipe_price_brasilapi(codigo_fipe)
            if fipe_result.get("success"):
                result["fipe_price"] = fipe_result.get("price", "")
                result["fipe_reference"] = fipe_result.get("reference", "")

        logger.info(f"BrasilAPI lookup success: {plate} -> {result['brand']} {result['model']} {result['year']}")
        return result

    except httpx.ConnectError:
        return {"success": False, "error": "Não foi possível conectar à BrasilAPI. Verifique a conexão."}
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout ao consultar placa. Tente novamente."}
    except Exception as e:
        logger.error(f"BrasilAPI lookup error: {e}")
        return {"success": False, "error": f"Erro inesperado: {str(e)}"}


async def _lookup_fipe_price_brasilapi(codigo_fipe: str) -> Dict:
    """
    Look up FIPE reference price by FIPE code using BrasilAPI.

    Returns the most recent price for the vehicle.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.get(
                BRASIL_API_FIPE_PRICE_URL.format(codigo_fipe=codigo_fipe),
            )

            if response.status_code != 200:
                logger.warning(f"FIPE price lookup failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}

            data = response.json()

        if isinstance(data, list) and len(data) > 0:
            entries = sorted(data, key=lambda x: x.get("mesReferencia", ""), reverse=True)
            latest = entries[0]

            price_str = latest.get("valor", "")
            reference = latest.get("mesReferencia", "")

            return {
                "success": True,
                "price": price_str,
                "reference": reference,
                "model_year": latest.get("anoModelo", ""),
                "fuel_type": latest.get("combustivel", ""),
            }

        return {"success": False, "error": "Nenhum preço FIPE encontrado"}

    except Exception as e:
        logger.warning(f"FIPE price lookup error: {e}")
        return {"success": False, "error": str(e)}