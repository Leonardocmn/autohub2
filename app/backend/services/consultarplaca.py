"""
Shared ConsultarPlaca API client.

Centralizes credentials, base URL, and common request logic
so that plate_lookup.py and fipe_lookup.py don't duplicate code.
"""

import logging
import os
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

CONSULTARPLACA_BASE_URL = "https://api.consultarplaca.com.br"
CONSULTARPLACA_FIPE_URL = f"{CONSULTARPLACA_BASE_URL}/v2/consultarPrecoFipe"
CONSULTARPLACA_PLATE_URL = f"{CONSULTARPLACA_BASE_URL}/v2/consultarPlaca"


def get_credentials() -> Tuple[str, str]:
    """Get ConsultarPlaca API credentials from environment variables.

    Returns (email, api_key) tuple. Both must be non-empty for the API to be used.
    """
    email = os.environ.get("CONSULTARPLACA_EMAIL", "").strip()
    api_key = os.environ.get("CONSULTARPLACA_API_KEY", "").strip()
    return (email, api_key)


def has_credentials() -> bool:
    """Check if ConsultarPlaca API credentials are configured."""
    email, api_key = get_credentials()
    return bool(email and api_key)


async def fetch_fipe(plate: str, timeout: float = 20.0) -> Dict:
    """Call ConsultarPlaca FIPE endpoint (vehicle info + FIPE prices).

    Returns the parsed JSON response dict, or an error dict on failure.
    """
    email, api_key = get_credentials()

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            response = await http.get(
                CONSULTARPLACA_FIPE_URL,
                params={"placa": plate},
                auth=(email, api_key),
            )

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "Credenciais da ConsultarPlaca inválidas. Verifique email e API key.",
                }

            if response.status_code == 404:
                return {"success": False, "error": f"Placa '{plate}' não encontrada na ConsultarPlaca."}

            if response.status_code == 429:
                return {
                    "success": False,
                    "error": "Limite de consultas atingido na ConsultarPlaca. Tente novamente em instantes.",
                }

            if response.status_code != 200:
                logger.error(f"ConsultarPlaca API error: {response.status_code} - {response.text[:300]}")
                return {
                    "success": False,
                    "error": f"Erro ao consultar placa (ConsultarPlaca): HTTP {response.status_code}",
                }

            data = response.json()

        if data.get("status") != "ok":
            msg = data.get("mensagem", "Erro desconhecido")
            return {"success": False, "error": f"ConsultarPlaca: {msg}"}

        return data

    except httpx.ConnectError:
        return {"success": False, "error": "Não foi possível conectar à ConsultarPlaca API. Verifique a conexão."}
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout ao consultar ConsultarPlaca. Tente novamente."}
    except Exception as e:
        logger.error(f"ConsultarPlaca fetch_fipe error: {e}")
        return {"success": False, "error": f"Erro inesperado (ConsultarPlaca): {str(e)}"}