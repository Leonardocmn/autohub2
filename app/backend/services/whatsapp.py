import base64
import hashlib
import logging
import os
import time
import urllib3
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Suppress InsecureRequestWarning for self-signed SSL certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Whether to verify SSL certificates (set to False for self-signed certs)
SSL_VERIFY = os.environ.get("EVOLUTION_SSL_VERIFY", "false").lower() == "true"

# In-memory cache for settings to avoid DB hits on every request
_settings_cache: dict = {}
_settings_cache_loaded: bool = False
_settings_cache_expires_at: float = 0.0
_SETTINGS_CACHE_TTL = 30  # seconds


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    return "****" + value[-4:] if len(value) > 4 else "****"


def _clean_whatsapp_number(phone: str) -> str:
    return "".join(c for c in (phone or "") if c.isdigit())


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def _extract_message_id(data: Any) -> str:
    if isinstance(data, dict):
        key = data.get("key")
        if isinstance(key, dict):
            return key.get("id", "") or ""
        message = data.get("message")
        if isinstance(message, dict) and isinstance(message.get("key"), dict):
            return message["key"].get("id", "") or ""
        return data.get("messageId", "") or data.get("id", "") or ""
    return ""


def _find_instance(instances: Any, instance_name: str) -> Optional[dict]:
    candidates = instances if isinstance(instances, list) else []
    if isinstance(instances, dict):
        if isinstance(instances.get("instances"), list):
            candidates = instances["instances"]
        elif isinstance(instances.get("data"), list):
            candidates = instances["data"]
        else:
            candidates = [instances]

    for inst in candidates:
        if not isinstance(inst, dict):
            continue
        nested = inst.get("instance") if isinstance(inst.get("instance"), dict) else {}
        inst_name = (
            inst.get("name")
            or inst.get("instanceName")
            or nested.get("instanceName")
            or nested.get("name")
            or ""
        )
        if inst_name == instance_name:
            return inst
    return None


def _instance_status(instance: Optional[dict]) -> str:
    if not instance:
        return "not_found"
    nested = instance.get("instance") if isinstance(instance.get("instance"), dict) else {}
    return (
        instance.get("connectionStatus")
        or instance.get("status")
        or nested.get("status")
        or nested.get("connectionStatus")
        or "unknown"
    )


async def _load_settings_from_db(db: Optional[AsyncSession] = None) -> dict:
    """Load WhatsApp settings from database, falling back to env vars.
    
    Uses a 30-second TTL cache to avoid hitting the DB on every webhook call.
    """
    global _settings_cache, _settings_cache_loaded, _settings_cache_expires_at

    # Start with env vars as defaults
    env_defaults = {
        "EVOLUTION_API_URL": os.environ.get("EVOLUTION_API_URL", "").rstrip("/"),
        "EVOLUTION_API_KEY": os.environ.get("EVOLUTION_API_KEY", ""),
        "EVOLUTION_INSTANCE_NAME": os.environ.get("EVOLUTION_INSTANCE_NAME", ""),
    }

    now = time.time()
    # Return cached settings if still valid
    if _settings_cache_loaded and now < _settings_cache_expires_at:
        return {**env_defaults, **_settings_cache}

    if db is None:
        # No DB session available, use cache or env vars
        if _settings_cache_loaded:
            return {**env_defaults, **_settings_cache}
        return env_defaults

    try:
        from models.whatsapp_settings import Whatsapp_settings
        stmt = select(Whatsapp_settings)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        db_settings = {}
        for row in rows:
            db_settings[row.setting_key] = row.setting_value or ""
        _settings_cache = db_settings
        _settings_cache_loaded = True
        _settings_cache_expires_at = now + _SETTINGS_CACHE_TTL
        return {**env_defaults, **db_settings}
    except Exception as e:
        logger.warning(f"Could not load WhatsApp settings from DB: {e}")
        return env_defaults


async def get_evolution_config(db: Optional[AsyncSession] = None) -> dict:
    """Get Evolution API configuration from database (preferred) or environment variables."""
    settings = await _load_settings_from_db(db)
    return {
        "api_url": (settings.get("EVOLUTION_API_URL", "") or "").rstrip("/"),
        "api_key": settings.get("EVOLUTION_API_KEY", "") or "",
        "instance_name": settings.get("EVOLUTION_INSTANCE_NAME", "") or "",
    }


async def is_configured(db: Optional[AsyncSession] = None) -> bool:
    """Check if Evolution API is properly configured."""
    config = await get_evolution_config(db)
    return bool(config["api_url"] and config["api_key"] and config["instance_name"])


async def save_setting(db: AsyncSession, key: str, value: str) -> None:
    """Save or update a WhatsApp setting in the database."""
    global _settings_cache_loaded
    from models.whatsapp_settings import Whatsapp_settings
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == key)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.setting_value = value
    else:
        new_setting = Whatsapp_settings(setting_key=key, setting_value=value)
        db.add(new_setting)
    await db.commit()
    # Invalidate cache so next read picks up the change
    _settings_cache_loaded = False
    _settings_cache_expires_at = 0.0
    _settings_cache.pop(key, None)


async def test_connection(db: Optional[AsyncSession] = None) -> dict:
    """Test connection to Evolution API by fetching instance info."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {
            "connected": False,
            "error": "Evolution API não configurada. Defina EVOLUTION_API_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE_NAME.",
        }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.get(
                f"{config['api_url']}/instance/fetchInstances",
                params={"instanceName": config["instance_name"]},
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code in (301, 302, 307, 308):
                redirect_url = response.headers.get("location", "")
                return {
                    "connected": False,
                    "error": f"A URL está redirecionando para {redirect_url}. Verifique se a URL aponta para a API (ex: http://servidor:8080) e não para o painel web.",
                }
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "html" in content_type:
                    return {
                        "connected": False,
                        "error": "A URL retornou uma página HTML em vez de JSON. Verifique se a URL aponta para a API Evolution (ex: http://servidor:8080) e não para o painel web.",
                    }
                try:
                    instances = response.json()
                except Exception:
                    return {
                        "connected": False,
                        "error": "A resposta não é um JSON válido. Verifique se a URL aponta para a API Evolution corretamente.",
                    }
                instance = None
                if isinstance(instances, list):
                    for inst in instances:
                        if isinstance(inst, dict):
                            inst_name = (
                                inst.get("name")
                                or inst.get("instance", {}).get("instanceName", "")
                            )
                            if inst_name == config["instance_name"]:
                                instance = inst
                                break
                connection_status = "unknown"
                if instance and isinstance(instance, dict):
                    connection_status = (
                        instance.get("connectionStatus")
                        or instance.get("instance", {}).get("status", "unknown")
                    )
                return {
                    "connected": True,
                    "instance_name": config["instance_name"],
                    "status": connection_status,
                }
            else:
                return {
                    "connected": False,
                    "error": f"Erro na API: {response.status_code} - {response.text[:200]}",
                }
    except httpx.ConnectError:
        return {
            "connected": False,
            "error": "Não foi possível conectar ao servidor Evolution API. Verifique a URL.",
        }
    except httpx.TimeoutException:
        return {
            "connected": False,
            "error": "Timeout ao conectar ao Evolution API. O servidor demorou muito para responder.",
        }
    except Exception as e:
        logger.error(f"Evolution API test connection error: {e}")
        return {
            "connected": False,
            "error": f"Erro inesperado: {str(e)}",
        }


async def send_text_message(phone: str, message: str, db: Optional[AsyncSession] = None) -> dict:
    """Send a text message via Evolution API."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API não configurada"}

    # Clean phone number - remove non-numeric chars except +
    clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
    if not clean_phone.startswith("+"):
        clean_phone = f"+{clean_phone}"
    # Add @s.whatsapp.net suffix for Evolution API
    number = clean_phone.replace("+", "") + "@s.whatsapp.net"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.post(
                f"{config['api_url']}/message/sendText/{config['instance_name']}",
                json={
                    "number": number,
                    "text": message,
                },
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code in (200, 201):
                return {"success": True, "message_id": response.json().get("key", {}).get("id", "")}
            else:
                logger.error(f"Evolution API send error: {response.status_code} - {response.text[:300]}")
                return {
                    "success": False,
                    "error": f"Erro ao enviar: {response.status_code}",
                }
    except Exception as e:
        logger.error(f"Evolution API send message error: {e}")
        return {"success": False, "error": str(e)}


async def setup_webhook(webhook_url: str, db: Optional[AsyncSession] = None) -> dict:
    """Configure Evolution API to send webhook events to our server."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API não configurada"}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            webhook_data = {
                "enabled": True,
                "url": webhook_url,
                "webhookByEvents": True,
                "events": [
                    "MESSAGES_UPSERT",
                    "SEND_MESSAGE",
                ],
            }
            response = await http.post(
                f"{config['api_url']}/webhook/set/{config['instance_name']}",
                json={
                    **webhook_data,
                    "webhook": webhook_data,
                },
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code in (200, 201):
                return {"success": True, "webhook_url": webhook_url}
            else:
                logger.error(f"Evolution API webhook setup error: {response.status_code} - {response.text[:300]}")
                return {
                    "success": False,
                    "error": f"Erro ao configurar webhook: {response.status_code}",
                }
    except Exception as e:
        logger.error(f"Evolution API webhook setup error: {e}")
        return {"success": False, "error": str(e)}


async def get_webhook_status(db: Optional[AsyncSession] = None) -> dict:
    """Get the current webhook configuration from Evolution API."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"configured": False, "error": "Evolution API não configurada"}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.get(
                f"{config['api_url']}/webhook/find/{config['instance_name']}",
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200:
                data = response.json()
                if data is None:
                    return {
                        "configured": False,
                        "enabled": False,
                        "url": "",
                        "events": [],
                    }
                return {
                    "configured": True,
                    "enabled": data.get("enabled", False),
                    "url": data.get("url", ""),
                    "events": data.get("events", []),
                }
            else:
                return {
                    "configured": False,
                    "error": f"Erro ao verificar webhook: {response.status_code}",
                }
    except Exception as e:
        logger.error(f"Evolution API webhook status error: {e}")
        return {"configured": False, "error": str(e)}


async def _validate_public_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is publicly accessible via HTTPS.
    
    Returns (is_valid, mimetype_or_error).
    """
    if not url:
        return False, "Empty URL"
    if not url.startswith("https://"):
        return False, f"URL is not HTTPS: {url[:60]}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            resp = await http.head(url)
            if resp.status_code != 200:
                # Try GET in case HEAD is not supported
                resp = await http.get(url, headers={"Range": "bytes=0-0"})
            if resp.status_code in (200, 206):
                ct = resp.headers.get("content-type", "")
                if "image" in ct or "video" in ct or "audio" in ct:
                    return True, ct
                # Still valid even without explicit media content-type
                return True, ct or "image/jpeg"
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)


async def _url_to_base64_raw(url: str) -> tuple[str, str]:
    """Download media from a URL and return (raw_base64, mimetype).
    
    Returns ("", "") on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            resp = await http.get(url)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "image/jpeg")
                if not any(t in content_type for t in ("image", "video", "audio", "application")):
                    content_type = "image/jpeg"
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return b64, content_type
            else:
                logger.warning(f"Failed to download media from {url[:80]}: HTTP {resp.status_code}")
                return "", ""
    except Exception as e:
        logger.warning(f"Failed to download media from {url[:80]}: {e}")
        return "", ""


def _guess_mimetype(media_url: str, media_type: str = "image") -> str:
    """Guess MIME type from URL or media type."""
    url_lower = media_url.lower() if media_url else ""
    if ".png" in url_lower:
        return "image/png"
    elif ".webp" in url_lower:
        return "image/webp"
    elif ".mp4" in url_lower:
        return "video/mp4"
    elif ".pdf" in url_lower:
        return "application/pdf"
    # Default by media_type
    if media_type == "video":
        return "video/mp4"
    elif media_type == "audio":
        return "audio/ogg"
    elif media_type == "document":
        return "application/pdf"
    return "image/jpeg"


async def send_media_message(
    phone: str,
    message: str,
    media_url: str = "",
    media_type: str = "image",
    db: Optional[AsyncSession] = None,
) -> dict:
    """Send a media message via Evolution API sendMedia endpoint.

    Payload fields required by Evolution API:
      - number:   recipient phone (digits only + @s.whatsapp.net)
      - mediatype: "image" | "video" | "audio" | "document"
      - mimetype:  e.g. "image/jpeg", "image/png"
      - caption:   text description (goes with the media)
      - media:     public HTTPS URL or raw base64 string

    Before sending, validates that the image URL is publicly accessible.
    If not, downloads and converts to base64 as fallback.
    """
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API não configurada"}

    # Clean phone number: digits only, add @s.whatsapp.net
    clean_phone = "".join(c for c in phone if c.isdigit())
    if not clean_phone:
        return {"success": False, "error": "Número de telefone inválido"}
    number = clean_phone + "@s.whatsapp.net"

    # Determine media content and mimetype
    media_data = media_url
    mimetype = _guess_mimetype(media_url, media_type)

    if media_url and media_url.startswith("http"):
        # Step 1: Validate URL is publicly accessible
        is_valid, result = await _validate_public_url(media_url)
        if is_valid:
            # URL is accessible — use it directly
            media_data = media_url
            # Use the detected content-type if it's a media type
            if any(t in result for t in ("image", "video", "audio")):
                mimetype = result
            logger.info(f"Media URL validated as public: {media_url[:80]} (type: {mimetype})")
        else:
            # URL not publicly accessible — download and convert to base64
            logger.warning(f"Media URL not publicly accessible ({result}), converting to base64: {media_url[:80]}")
            b64_raw, detected_mimetype = await _url_to_base64_raw(media_url)
            if b64_raw:
                media_data = b64_raw
                if detected_mimetype and any(t in detected_mimetype for t in ("image", "video", "audio")):
                    mimetype = detected_mimetype
                logger.info(f"Converted media URL to raw base64 ({len(b64_raw)} chars, type: {mimetype})")
            else:
                logger.error(f"Cannot access media URL and failed to convert to base64: {media_url[:80]}")
                return {"success": False, "error": f"Imagem não acessível: {result}"}

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            payload: dict = {
                "number": number,
                "mediatype": media_type,
                "mimetype": mimetype,
                "caption": message,
                "media": media_data,
            }

            endpoint = f"/message/sendMedia/{config['instance_name']}"
            logger.info(
                f"Sending media to {number}: type={media_type}, mime={mimetype}, "
                f"media_len={len(media_data) if media_data else 0}, "
                f"caption_len={len(message) if message else 0}"
            )
            response = await http.post(
                f"{config['api_url']}{endpoint}",
                json=payload,
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code in (200, 201):
                resp_data = response.json()
                msg_id = resp_data.get("key", {}).get("id", "")
                logger.info(f"Media sent successfully to {number}: msg_id={msg_id}")
                return {"success": True, "message_id": msg_id}
            else:
                error_text = response.text[:500]
                logger.error(f"Evolution API send media error: {response.status_code} - {error_text}")
                return {
                    "success": False,
                    "error": f"Erro ao enviar mídia: {response.status_code} - {error_text}",
                }
    except Exception as e:
        logger.error(f"Evolution API send media error: {e}")
        return {"success": False, "error": str(e)}


async def test_connection(db: Optional[AsyncSession] = None) -> dict:
    """Stable Evolution API connection test used by the MVP."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {
            "connected": False,
            "error": "Evolution API nao configurada. Defina URL, API Key e instancia.",
        }

    headers = {"apikey": config["api_key"], "Content-Type": "application/json"}
    logger.info(
        "Testing Evolution API connection: url=%s instance=%s key=%s",
        config["api_url"],
        config["instance_name"],
        _mask_secret(config["api_key"]),
    )
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.get(
                f"{config['api_url']}/instance/fetchInstances",
                params={"instanceName": config["instance_name"]},
                headers=headers,
            )
        if response.status_code != 200:
            logger.error("Evolution API test error: %s - %s", response.status_code, response.text[:500])
            return {"connected": False, "error": f"Erro na Evolution API: {response.status_code} - {response.text[:200]}"}

        content_type = response.headers.get("content-type", "")
        if "html" in content_type.lower():
            return {"connected": False, "error": "A URL retornou HTML. Use a URL da API Evolution, nao a URL do painel."}

        instances = _safe_json(response)
        if instances is None:
            return {"connected": False, "error": "A Evolution API retornou uma resposta que nao e JSON valido."}

        instance = _find_instance(instances, config["instance_name"])
        status = _instance_status(instance)
        connected = status.lower() in ("open", "connected", "online")
        if instance is None:
            return {
                "connected": False,
                "instance_name": config["instance_name"],
                "status": status,
                "error": f"Instancia '{config['instance_name']}' nao encontrada na Evolution API.",
            }
        return {
            "connected": connected,
            "instance_name": config["instance_name"],
            "status": status,
            "error": "" if connected else f"Instancia encontrada, mas status atual e '{status}'.",
        }
    except httpx.ConnectError:
        return {"connected": False, "error": "Nao foi possivel conectar ao servidor Evolution API. Verifique a URL."}
    except httpx.TimeoutException:
        return {"connected": False, "error": "Timeout ao conectar ao Evolution API."}
    except Exception as e:
        logger.error("Evolution API test connection error: %s", e, exc_info=True)
        return {"connected": False, "error": f"Erro inesperado: {str(e)}"}


async def send_text_message(phone: str, message: str, db: Optional[AsyncSession] = None) -> dict:
    """Send text with the v2 digits format, retrying JID for older instances."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API nao configurada"}

    number = _clean_whatsapp_number(phone)
    if not number:
        return {"success": False, "error": "Numero de telefone invalido"}

    headers = {"apikey": config["api_key"], "Content-Type": "application/json"}
    endpoint = f"{config['api_url']}/message/sendText/{config['instance_name']}"
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.post(endpoint, json={"number": number, "text": message}, headers=headers)
            if response.status_code in (200, 201):
                return {"success": True, "message_id": _extract_message_id(_safe_json(response))}

            logger.warning(
                "Evolution API sendText failed with digits number. Retrying JID. status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            retry = await http.post(endpoint, json={"number": f"{number}@s.whatsapp.net", "text": message}, headers=headers)
            if retry.status_code in (200, 201):
                return {"success": True, "message_id": _extract_message_id(_safe_json(retry))}

        logger.error("Evolution API sendText error: %s - %s", retry.status_code, retry.text[:500])
        return {"success": False, "error": f"Erro ao enviar texto: {retry.status_code} - {retry.text[:200]}"}
    except Exception as e:
        logger.error("Evolution API sendText exception: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


async def setup_webhook(webhook_url: str, db: Optional[AsyncSession] = None) -> dict:
    """Configure Evolution API webhook, supporting nested and flat payload variants."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API nao configurada"}

    webhook_data = {
        "enabled": True,
        "url": webhook_url,
        "webhookByEvents": True,
        "events": ["MESSAGES_UPSERT", "SEND_MESSAGE"],
    }
    headers = {"apikey": config["api_key"], "Content-Type": "application/json"}
    endpoint = f"{config['api_url']}/webhook/set/{config['instance_name']}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.post(endpoint, json={"webhook": webhook_data}, headers=headers)
            if response.status_code not in (200, 201):
                logger.warning(
                    "Evolution API webhook setup nested payload failed. Retrying flat. status=%s body=%s",
                    response.status_code,
                    response.text[:300],
                )
                response = await http.post(endpoint, json=webhook_data, headers=headers)
        if response.status_code in (200, 201):
            return {"success": True, "webhook_url": webhook_url}
        logger.error("Evolution API webhook setup error: %s - %s", response.status_code, response.text[:500])
        return {"success": False, "error": f"Erro ao configurar webhook: {response.status_code} - {response.text[:200]}"}
    except Exception as e:
        logger.error("Evolution API webhook setup exception: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


async def get_webhook_status(db: Optional[AsyncSession] = None) -> dict:
    """Get Evolution API webhook status across common response shapes."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"configured": False, "error": "Evolution API nao configurada"}

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.get(
                f"{config['api_url']}/webhook/find/{config['instance_name']}",
                headers={"apikey": config["api_key"], "Content-Type": "application/json"},
            )
        if response.status_code != 200:
            logger.error("Evolution API webhook status error: %s - %s", response.status_code, response.text[:500])
            return {"configured": False, "error": f"Erro ao verificar webhook: {response.status_code}"}

        data = _safe_json(response)
        if not data:
            return {"configured": False, "enabled": False, "url": "", "events": []}
        webhook = data.get("webhook", data) if isinstance(data, dict) else {}
        return {
            "configured": bool(webhook),
            "enabled": bool(webhook.get("enabled", False)),
            "url": webhook.get("url", ""),
            "events": webhook.get("events", []),
        }
    except Exception as e:
        logger.error("Evolution API webhook status exception: %s", e, exc_info=True)
        return {"configured": False, "error": str(e)}


async def send_media_message(
    phone: str,
    message: str,
    media_url: str = "",
    media_type: str = "image",
    db: Optional[AsyncSession] = None,
) -> dict:
    """Send media via sendMedia with v2 payload and a JID retry fallback."""
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API nao configurada"}

    number = _clean_whatsapp_number(phone)
    if not number:
        return {"success": False, "error": "Numero de telefone invalido"}

    media_data = media_url
    mimetype = _guess_mimetype(media_url, media_type)
    if media_url and media_url.startswith("http"):
        is_valid, result = await _validate_public_url(media_url)
        if is_valid:
            media_data = media_url
            if any(t in result for t in ("image", "video", "audio", "application")):
                mimetype = result
        else:
            logger.warning("Media URL not public (%s), converting to base64: %s", result, media_url[:80])
            b64_raw, detected_mimetype = await _url_to_base64_raw(media_url)
            if not b64_raw:
                return {"success": False, "error": f"Midia nao acessivel: {result}"}
            media_data = b64_raw
            mimetype = detected_mimetype or mimetype

    ext = mimetype.split("/")[-1].split(";")[0] if "/" in mimetype else "jpg"
    payload = {
        "number": number,
        "mediatype": media_type,
        "mimetype": mimetype,
        "caption": message or "",
        "media": media_data,
        "fileName": f"autohub.{ext or 'jpg'}",
    }
    headers = {"apikey": config["api_key"], "Content-Type": "application/json"}
    endpoint = f"{config['api_url']}/message/sendMedia/{config['instance_name']}"
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.post(endpoint, json=payload, headers=headers)
            if response.status_code in (200, 201):
                return {"success": True, "message_id": _extract_message_id(_safe_json(response))}

            logger.warning(
                "Evolution API sendMedia failed with digits number. Retrying JID. status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            retry_payload = {**payload, "number": f"{number}@s.whatsapp.net"}
            retry = await http.post(endpoint, json=retry_payload, headers=headers)
            if retry.status_code in (200, 201):
                return {"success": True, "message_id": _extract_message_id(_safe_json(retry))}

        logger.error("Evolution API sendMedia error: %s - %s", retry.status_code, retry.text[:500])
        return {"success": False, "error": f"Erro ao enviar midia: {retry.status_code} - {retry.text[:200]}"}
    except Exception as e:
        logger.error("Evolution API sendMedia exception: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


async def decode_whatsapp_media(message_obj: dict, db: Optional[AsyncSession] = None) -> dict:
    """
    Decode WhatsApp media using Evolution API getBase64FromMediaMessage endpoint.
    The encrypted WhatsApp media URL from the webhook cannot be used directly
    to forward media to other contacts. This endpoint decodes it to base64.
    
    The API expects the full message data object (including 'key' and 'message' fields)
    as received from the webhook, NOT just the inner 'message' sub-object.
    """
    config = await get_evolution_config(db)
    if not (config["api_url"] and config["api_key"] and config["instance_name"]):
        return {"success": False, "error": "Evolution API not configured"}

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            # The Evolution API expects the full webhook message data structure
            # including 'key' and 'message' at the top level
            response = await http.post(
                f"{config['api_url']}/chat/getBase64FromMediaMessage/{config['instance_name']}",
                json={"message": message_obj},
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                },
            )
            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "success": True,
                    "base64": data.get("base64", ""),
                    "mimetype": data.get("mimetype", "image/jpeg"),
                    "filename": data.get("filename", "media.jpg"),
                }
            else:
                logger.error(f"Evolution API decode media error: {response.status_code} - {response.text[:300]}")
                return {"success": False, "error": f"Decode failed: {response.status_code}"}
    except Exception as e:
        logger.error(f"Evolution API decode media error: {e}")
        return {"success": False, "error": str(e)}


async def upload_media_to_storage(base64_data: str, object_key: str, content_type: str = "image/jpeg") -> str:
    """Upload base64-decoded media to object storage and return the public URL."""
    from services.storage import StorageService
    from schemas.storage import FileUpDownRequest

    try:
        image_bytes = base64.b64decode(base64_data)
        storage = StorageService()
        upload_req = FileUpDownRequest(bucket_name="vehicle-images", object_key=object_key)
        upload_resp = await storage.create_upload_url(upload_req)
        upload_url = upload_resp.upload_url
        if not upload_url:
            raise ValueError("Failed to get upload URL")

        async with httpx.AsyncClient(timeout=60.0, verify=SSL_VERIFY) as http:
            upload_res = await http.put(upload_url, content=image_bytes, headers={"Content-Type": content_type})
            upload_res.raise_for_status()

        download_req = FileUpDownRequest(bucket_name="vehicle-images", object_key=object_key)
        download_resp = await storage.create_download_url(download_req)
        return download_resp.download_url or ""
    except Exception as e:
        logger.error(f"Failed to upload media to storage: {e}")
        return ""


async def process_incoming_media(message_obj: dict, db: Optional[AsyncSession] = None) -> str:
    """
    Process incoming WhatsApp media: decode via Evolution API, upload to storage.
    Returns the public URL of the uploaded media, or empty string on failure.

    This is needed because the media_url from the webhook is an encrypted
    WhatsApp internal URL that cannot be used to forward media to other contacts.
    """
    decode_result = await decode_whatsapp_media(message_obj, db)
    if not decode_result.get("success"):
        logger.warning(f"Failed to decode WhatsApp media: {decode_result.get('error')}")
        return ""

    base64_data = decode_result.get("base64", "")
    mimetype = decode_result.get("mimetype", "image/jpeg")
    if not base64_data:
        logger.warning("Decoded media has no base64 data")
        return ""

    url_hash = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:12]
    ext = "jpg"
    if "png" in mimetype:
        ext = "png"
    elif "webp" in mimetype:
        ext = "webp"
    elif "mp4" in mimetype:
        ext = "mp4"
    elif "pdf" in mimetype:
        ext = "pdf"

    object_key = f"vehicle-images/whatsapp/{url_hash}.{ext}"
    public_url = await upload_media_to_storage(base64_data, object_key, mimetype)

    if public_url:
        logger.info(f"Successfully processed WhatsApp media: {object_key}")
    else:
        logger.warning("Failed to upload decoded media to storage")

    return public_url


def format_offer_message(offer: dict, supplier_name: str = "") -> str:
    """Format an offer as a WhatsApp message."""
    lines = [
        "🚗 *NOVA OFERTA - AUTOHUB*",
        "",
        f"📋 *Código:* #{offer.get('code', '')}",
        f"🏷️ *Título:* {offer.get('title', '')}",
        f"🏭 *Marca:* {offer.get('brand', '')}",
        f"🚘 *Modelo:* {offer.get('model', '')}",
    ]

    if offer.get("year"):
        lines.append(f"📅 *Ano:* {offer['year']}")
    if offer.get("color"):
        lines.append(f"🎨 *Cor:* {offer['color']}")
    if offer.get("price"):
        price_val = offer["price"]
        if isinstance(price_val, (int, float)):
            price_str = f"R$ {price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            price_str = str(price_val)
        lines.append(f"💰 *Preço:* {price_str}")
    if offer.get("km"):
        lines.append(f"📏 *KM:* {offer['km']}")
    if supplier_name:
        lines.append(f"🏢 *Fornecedor:* {supplier_name}")
    if offer.get("observations"):
        lines.append(f"📝 *Obs:* {offer['observations']}")

    lines.extend([
        "",
        "Interessado? Entre em contato! 📞",
    ])
    return "\n".join(lines)


def format_negotiation_update_message(offer: dict, buyer_name: str, status_label: str) -> str:
    """Format a negotiation update as a WhatsApp message."""
    lines = [
        "📢 *ATUALIZAÇÃO DE NEGOCIAÇÃO - AUTOHUB*",
        "",
        f"📋 *Oferta:* #{offer.get('code', '')} - {offer.get('title', '')}",
        f"👤 *Comprador:* {buyer_name}",
        f"📊 *Status:* {status_label}",
    ]
    if offer.get("observations"):
        lines.append(f"📝 *Obs:* {offer['observations']}")
    lines.extend(["", "_AutoHub - Intermediação de Veículos_"])
    return "\n".join(lines)
