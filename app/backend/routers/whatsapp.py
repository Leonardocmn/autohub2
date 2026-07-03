import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from dependencies.auth import get_admin_user, get_current_user
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.auth import UserResponse

# Simple in-memory rate limiter for webhook endpoint
_webhook_rate_limit: Dict[str, List[float]] = {}
WEBHOOK_RATE_LIMIT_WINDOW = 60  # seconds
WEBHOOK_RATE_LIMIT_MAX = 120  # max requests per window per phone

# Cache for admin phone list (refreshed every 30s to avoid DB query per webhook)
_admin_phones_cache: Dict[str, Any] = {"phones": [], "expires_at": 0.0}
_ADMIN_PHONES_CACHE_TTL = 30  # seconds

from core.database import get_db
from models.whatsapp_messages import Whatsapp_messages
from models.whatsapp_conversations import Whatsapp_conversations
from models.whatsapp_settings import Whatsapp_settings
from models.offers import Offers
from services.whatsapp import (
    format_negotiation_update_message,
    format_offer_message,
    get_evolution_config,
    is_configured,
    process_incoming_media,
    save_setting,
    send_media_message,
    send_text_message,
    setup_webhook,
    get_webhook_status,
    test_connection,
)
from services.whatsapp_conversation import (
    identify_contact,
    process_supplier_message,
    process_buyer_message,
    process_buyer_message_with_offer,
    store_message,
    trigger_conversation_analysis,
)
from services.offer_workflow import (
    handle_admin_command,
    handle_buyer_negotiate,
    send_offer_to_admin_for_approval,
    distribute_offer_to_buyers,
)
from services.admin_ad_workflow import handle_admin_ad_command
from services.admin_chat_commands import handle_admin_chat_command
from services.admin_ai_chat import handle_admin_ai_chat
from services.admin_menu import handle_admin_menu, init_menu_session
from services.admin_menu_defs import format_menu_message
from services.vehicle_dossiers import VehicleDossierService, normalize_plate

logger = logging.getLogger(__name__)
DEFAULT_AI_MODEL = os.environ.get("AUTOHUB_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


# ==================== Request/Response Models ====================

class TestConnectionResponse(BaseModel):
    connected: bool
    instance_name: str = ""
    status: str = ""
    error: str = ""


class SendMessageRequest(BaseModel):
    phone: str
    message: str


class SendOfferRequest(BaseModel):
    phone: str
    offer: dict
    supplier_name: str = ""


class SendNegotiationUpdateRequest(BaseModel):
    phone: str
    offer: dict
    buyer_name: str
    status_label: str


class SendMediaRequest(BaseModel):
    phone: str
    message: str
    media_url: str
    media_type: str = "image"


class SendMessageResponse(BaseModel):
    success: bool
    message_id: str = ""
    error: str = ""


class ConfigStatusResponse(BaseModel):
    configured: bool
    missing_vars: list[str] = []
    current_values: dict = {}


class SaveSettingsRequest(BaseModel):
    api_url: str = ""
    api_key: str = ""
    instance_name: str = ""


class WebhookSetupRequest(BaseModel):
    webhook_url: str


class WebhookStatusResponse(BaseModel):
    configured: bool
    enabled: bool = False
    url: str = ""
    events: list[str] = []
    error: str = ""


class TriggerAnalysisRequest(BaseModel):
    conversation_id: int


class BuyerReplyRequest(BaseModel):
    phone: str
    contact_name: str = ""
    content: str
    offer_code: str = ""
    custom_instructions: str = ""


class ConversationResponse(BaseModel):
    id: int
    supplier_phone: str = ""
    supplier_name: str = ""
    status: str = ""
    offer_draft_id: Optional[int] = None
    last_message_at: str = ""
    message_count: int = 0
    ai_analysis: str = ""
    window_closed: bool = False


class MessageResponse(BaseModel):
    id: int
    phone: str = ""
    contact_name: str = ""
    direction: str = ""
    message_type: str = ""
    content: str = ""
    media_url: str = ""
    processed: bool = False
    is_supplier: bool = False
    is_buyer: bool = False
    timestamp: str = ""


# ==================== Config & Connection ====================

@router.get("/config-status", response_model=ConfigStatusResponse)
async def get_config_status(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if Evolution API is configured."""
    config = await get_evolution_config(db)
    missing = []
    if not config["api_url"]:
        missing.append("EVOLUTION_API_URL")
    if not config["api_key"]:
        missing.append("EVOLUTION_API_KEY")
    if not config["instance_name"]:
        missing.append("EVOLUTION_INSTANCE_NAME")

    configured = await is_configured(db)
    return ConfigStatusResponse(
        configured=configured,
        missing_vars=missing,
        current_values={
            "api_url": config["api_url"],
            "api_key": "****" + config["api_key"][-4:] if len(config["api_key"]) > 4 else ("****" if config["api_key"] else ""),
            "instance_name": config["instance_name"],
        },
    )


@router.post("/save-settings", response_model=SendMessageResponse)
async def save_whatsapp_settings(
    data: SaveSettingsRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Save WhatsApp Evolution API settings to the database."""
    try:
        if data.api_url is not None and data.api_url.strip():
            await save_setting(db, "EVOLUTION_API_URL", data.api_url.strip().rstrip("/"))
        if data.api_key is not None and data.api_key.strip():
            await save_setting(db, "EVOLUTION_API_KEY", data.api_key.strip())
        if data.instance_name is not None and data.instance_name.strip():
            await save_setting(db, "EVOLUTION_INSTANCE_NAME", data.instance_name.strip())
        return SendMessageResponse(success=True)
    except Exception as e:
        logger.error(f"Error saving WhatsApp settings: {e}")
        return SendMessageResponse(success=False, error=str(e))


@router.get("/test-connection", response_model=TestConnectionResponse)
async def test_whatsapp_connection(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connection to Evolution API."""
    result = await test_connection(db)
    return TestConnectionResponse(
        connected=result.get("connected", False),
        instance_name=result.get("instance_name", ""),
        status=result.get("status", ""),
        error=result.get("error", ""),
    )


# ==================== Webhook Setup ====================

@router.post("/setup-webhook", response_model=SendMessageResponse)
async def setup_whatsapp_webhook(
    data: WebhookSetupRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Configure Evolution API to send webhook events to our server."""
    if not await is_configured(db):
        raise HTTPException(status_code=400, detail="Evolution API não configurada")

    result = await setup_webhook(data.webhook_url, db)
    return SendMessageResponse(
        success=result.get("success", False),
        error=result.get("error", ""),
    )


@router.get("/webhook-status", response_model=WebhookStatusResponse)
async def get_whatsapp_webhook_status(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current webhook configuration from Evolution API."""
    result = await get_webhook_status(db)
    return WebhookStatusResponse(
        configured=result.get("configured", False),
        enabled=result.get("enabled", False),
        url=result.get("url", ""),
        events=result.get("events", []),
        error=result.get("error", ""),
    )


# ==================== Webhook Receiver (PUBLIC - no auth) ====================

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Public webhook endpoint to receive incoming message events from Evolution API.
    No authentication required - this is called by the Evolution API server.
    """
    try:
        body = await request.json()
        logger.info(f"WhatsApp webhook received: {json.dumps(body, ensure_ascii=False)[:500]}")

        # Rate limiting: check per sender phone to prevent flood
        remote_jid_early = body.get("data", {}).get("key", {}).get("remoteJid", "")
        rl_phone = remote_jid_early.replace("@s.whatsapp.net", "").replace("@g.us", "")
        if rl_phone:
            now_ts = time.time()
            if rl_phone not in _webhook_rate_limit:
                _webhook_rate_limit[rl_phone] = []
            _webhook_rate_limit[rl_phone] = [t for t in _webhook_rate_limit[rl_phone] if now_ts - t < WEBHOOK_RATE_LIMIT_WINDOW]
            if len(_webhook_rate_limit[rl_phone]) >= WEBHOOK_RATE_LIMIT_MAX:
                logger.warning(f"Webhook rate limit exceeded for phone: {rl_phone}")
                return {"status": "rate_limited"}
            _webhook_rate_limit[rl_phone].append(now_ts)
            # Cleanup old entries periodically
            if len(_webhook_rate_limit) > 1000:
                cutoff = now_ts - WEBHOOK_RATE_LIMIT_WINDOW
                _webhook_rate_limit.update({
                    k: [t for t in v if t > cutoff]
                    for k, v in _webhook_rate_limit.items()
                })
                _webhook_rate_limit.update({
                    k: v for k, v in _webhook_rate_limit.items() if v
                })

        # Extract message data from Evolution API event format
        event = body.get("event", "")
        data = body.get("data", {})
        
        # Log raw event for audit trail
        try:
            from models.whatsapp_events import Whatsapp_events
            raw_data_str = json.dumps(body, ensure_ascii=False)
            # Truncate to prevent oversized rows
            if len(raw_data_str) > 10000:
                raw_data_str = raw_data_str[:10000] + "...[truncated]"
            evt = Whatsapp_events(
                event_type=event,
                instance=body.get("instance", ""),
                sender_phone=rl_phone or "",
                raw_data=raw_data_str,
                processed="pending",
            )
            db.add(evt)
            await db.commit()
        except Exception as evt_err:
            logger.warning(f"Failed to log webhook event: {evt_err}")
        
        # Only process incoming messages
        if event not in ("messages.upsert", "MESSAGES_UPSERT"):
            return {"status": "ignored", "event": event}

        # Validate webhook instance before doing any message/media processing.
        instance_name = data.get("instance") or body.get("instance", "")
        config = await get_evolution_config(db)
        if config["instance_name"] and instance_name and instance_name != config["instance_name"]:
            logger.warning(f"Webhook from unknown instance: {instance_name} (expected {config['instance_name']})")
            return {"status": "ignored", "reason": "instance_mismatch"}
        
        # Extract key info from the message
        key = data.get("key", {})
        message_type_dir = key.get("fromMe", False)
        
        # Skip outgoing messages (sent by us)
        if message_type_dir:
            return {"status": "ignored", "reason": "outgoing"}

        # Get sender phone
        remote_jid = key.get("remoteJid", "")
        sender_phone = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")
        
        if not sender_phone or sender_phone == "status":
            return {"status": "ignored", "reason": "invalid_sender"}

        # Extract pushName for contact identification (Evolution API provides this)
        push_name = data.get("pushName", "") or ""

        # Extract message content
        message_obj = data.get("message", {})
        message_id = key.get("id", "")
        timestamp = str(data.get("messageTimestamp", ""))
        
        content = ""
        media_url = ""
        message_type = "text"

        # Handle different message types
        # Note: WhatsApp media URLs from the webhook are encrypted and cannot
        # be used to forward media. We decode them via Evolution API and
        # upload to our object storage to get a usable public URL.
        has_media = False
        if message_obj.get("conversation"):
            content = message_obj["conversation"]
            message_type = "text"
        elif message_obj.get("extendedTextMessage"):
            content = message_obj["extendedTextMessage"].get("text", "")
            message_type = "text"
        elif message_obj.get("imageMessage"):
            content = message_obj["imageMessage"].get("caption", "")
            media_url = message_obj["imageMessage"].get("url", "")
            message_type = "image"
            has_media = True
        elif message_obj.get("videoMessage"):
            content = message_obj["videoMessage"].get("caption", "")
            media_url = message_obj["videoMessage"].get("url", "")
            message_type = "video"
            has_media = True
        elif message_obj.get("documentMessage"):
            content = message_obj["documentMessage"].get("caption", "")
            media_url = message_obj["documentMessage"].get("url", "")
            message_type = "document"
            has_media = True
        elif message_obj.get("audioMessage"):
            media_url = message_obj["audioMessage"].get("url", "")
            message_type = "audio"
            has_media = True
        else:
            # Unknown message type, try to extract any text
            content = str(message_obj)
            message_type = "unknown"

        # Decode encrypted WhatsApp media and upload to our storage
        # The Evolution API getBase64FromMediaMessage endpoint requires the FULL
        # data object from the webhook (including 'key', 'message', 'pushName', etc.)
        if has_media and media_url:
            try:
                decoded_url = await process_incoming_media(data, db)
                if decoded_url:
                    media_url = decoded_url
                    logger.info(f"Media decoded and uploaded: {decoded_url[:80]}")
                else:
                    logger.warning(f"Failed to decode media, keeping original URL: {media_url[:80]}")
            except Exception as e:
                logger.error(f"Error processing incoming media: {e}")

        # Identify if sender is supplier or buyer
        contact_info = await identify_contact(sender_phone, db, push_name=push_name)
        
        # Check if sender is an admin first (for command handling)
        # Use cached admin phones to avoid DB query on every webhook call
        now_ts_admin = time.time()
        if now_ts_admin >= _admin_phones_cache["expires_at"]:
            from models.whatsapp_admin_phones import Whatsapp_admin_phones
            admin_stmt = select(Whatsapp_admin_phones).where(Whatsapp_admin_phones.active == True)
            admin_res = await db.execute(admin_stmt)
            _admin_phones_cache["phones"] = [row.phone.strip() for row in admin_res.scalars().all() if row.phone]
            _admin_phones_cache["expires_at"] = now_ts_admin + _ADMIN_PHONES_CACHE_TTL
        admin_phones = _admin_phones_cache["phones"]
        clean_sender = "".join(c for c in sender_phone if c.isdigit())
        is_admin = False
        for p in admin_phones:
            clean_p = "".join(c for c in p if c.isdigit())
            # Exact match: both must have at least 10 digits and the last 10+ digits must match exactly
            if len(clean_p) >= 10 and len(clean_sender) >= 10:
                min_len = min(len(clean_p), len(clean_sender))
                if clean_p[-min_len:] == clean_sender[-min_len:]:
                    is_admin = True
                    break
        
        if not is_admin and not contact_info["is_supplier"] and not contact_info["is_buyer"]:
            try:
                await store_message(
                    phone=sender_phone,
                    direction="incoming",
                    message_type=message_type,
                    content=content,
                    media_url=media_url,
                    message_id=message_id,
                    contact_name=push_name,
                    is_supplier=False,
                    is_buyer=False,
                    timestamp=timestamp,
                    db=db,
                )
            except Exception as msg_err:
                logger.error(f"Failed to store incoming unregistered WhatsApp message: {msg_err}")

        # Handle admin commands via WhatsApp
        if is_admin:
            try:
                await store_message(
                    phone=sender_phone,
                    direction="incoming",
                    message_type=message_type,
                    content=content,
                    media_url=media_url,
                    message_id=message_id,
                    contact_name=push_name,
                    is_supplier=False,
                    is_buyer=False,
                    timestamp=timestamp,
                    db=db,
                )
            except Exception as msg_err:
                logger.error(f"Failed to store incoming admin WhatsApp message: {msg_err}")

            # 1. Handle approval commands (APROVAR/REJEITAR/CONFIRMAR/VOLTAR + offer code)
            #    High-priority: always intercepted regardless of menu state
            if content and message_type == "text":
                content_upper = content.strip().upper()
                import re
                cmd_match = re.match(r"(APROVAR|REJEITAR|CONFIRMAR|VOLTAR)\s+\x23?(\d+)", content_upper)
                if cmd_match:
                    command = cmd_match.group(1)
                    offer_code = cmd_match.group(2)
                    result = await handle_admin_command(sender_phone, command, offer_code, db)
                    return {"status": "processed", "type": "admin_command", "result": result}

            # 2. Check for ad creation flow (session-based, multi-step)
            #    Handles both text AND media messages (photos are essential for ad creation)
            from models.whatsapp_admin_sessions import Whatsapp_admin_sessions as _WAS
            session_stmt = select(_WAS).where(_WAS.admin_phone == sender_phone)
            session_res = await db.execute(session_stmt)
            admin_session = session_res.scalar_one_or_none()
            in_ad_flow = admin_session and admin_session.state in (
                "awaiting_ad_content", "awaiting_ad_description"
            )
            starts_ad = (content and message_type == "text" and
                         content.strip().upper().startswith("CRIAR ANUNCIO"))

            if in_ad_flow or starts_ad:
                ad_result = await handle_admin_ad_command(
                    phone=sender_phone,
                    content=content or "",
                    message_type=message_type,
                    media_url=media_url,
                    db=db,
                )
                if ad_result.get("handled"):
                    return {"status": "processed", "type": "admin_ad_workflow", "result": ad_result}

            # 3. Menu state machine - primary and default admin navigation
            #    ALL admin messages go through the menu system.
            #    Numeric input navigates menus; unrecognized input shows the menu again.
            #    This is the standard behavior: always respond with the menu.
            if content and message_type == "text":
                menu_result = await handle_admin_menu(
                    phone=sender_phone,
                    content=content,
                    db=db,
                )
                if menu_result.get("handled"):
                    return {"status": "processed", "type": "admin_menu", "result": menu_result}

            # 4. Non-text messages from admin (images, audio, etc.)
            #    Show the menu as default response
            if message_type != "text":
                await send_text_message(
                    sender_phone,
                    "📎 Mídia recebida. Para interagir, digite o *número* da opção desejada.\n\n"
                    + format_menu_message("main"),
                    db,
                )
                return {"status": "processed", "type": "admin_media_menu"}
        
        if contact_info["is_supplier"]:
            # Process as supplier message
            result = await process_supplier_message(
                phone=sender_phone,
                contact_name=contact_info["name"] or "",
                message_type=message_type,
                content=content,
                media_url=media_url,
                message_id=message_id,
                timestamp=timestamp,
                db=db,
            )
            return {"status": "processed", "type": "supplier", "result": result}
        
        elif contact_info["is_buyer"]:
            # Check for NEGOCIAR command from buyer first
            if content and message_type == "text":
                neg_result = await handle_buyer_negotiate(sender_phone, content, db)
                if neg_result.get("handled"):
                    return {"status": "processed", "type": "buyer_negotiate", "result": neg_result}
            
            # Process as buyer message
            result = await process_buyer_message(
                phone=sender_phone,
                contact_name=contact_info["name"] or "",
                message_type=message_type,
                content=content,
                media_url=media_url,
                message_id=message_id,
                timestamp=timestamp,
                db=db,
            )
            return {"status": "processed", "type": "buyer", "result": result}
        
        else:
            # Unknown/unregistered contact - per §6.4, do NOT generate offers automatically
            # Only acknowledge and log the message
            logger.info(f"Message from unregistered number ignored (§6.4): {sender_phone}")
            await send_text_message(
                sender_phone,
                "Olá! Obrigado pelo contato. Este número não está cadastrado no sistema AutoHub. "
                "Para enviar ofertas de veículos, solicite seu cadastro ao administrador.",
                db,
            )
            return {"status": "ignored", "reason": "unregistered_contact", "phone": sender_phone}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"status": "error", "error": str(e)}


# ==================== Messages ====================

@router.get("/messages")
async def list_messages(
    limit: int = 100,
    offset: int = 0,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all WhatsApp messages, including those without conversations."""
    stmt = (
        select(Whatsapp_messages)
        .order_by(desc(Whatsapp_messages.id))
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()

    count_stmt = select(func.count(Whatsapp_messages.id))
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one_or_none() or 0

    return {
        "items": [
            {
                "id": m.id,
                "phone": m.phone,
                "contact_name": m.contact_name,
                "direction": m.direction,
                "message_type": m.message_type,
                "content": m.content,
                "media_url": m.media_url,
                "processed": m.processed,
                "is_supplier": m.is_supplier,
                "is_buyer": m.is_buyer,
                "conversation_id": m.conversation_id,
                "timestamp": m.timestamp,
            }
            for m in messages
        ],
        "total": total,
    }


# ==================== Conversations ====================

@router.get("/conversations")
async def list_conversations(
    status: str = "",
    limit: int = 50,
    offset: int = 0,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List WhatsApp conversations with optional status filter."""
    conditions = []
    if status:
        conditions.append(Whatsapp_conversations.status == status)
    
    stmt = (
        select(Whatsapp_conversations)
        .where(and_(*conditions) if conditions else True)
        .order_by(desc(Whatsapp_conversations.id))
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    conversations = res.scalars().all()
    
    # Get total count
    count_stmt = select(func.count(Whatsapp_conversations.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one_or_none() or 0
    
    return {
        "items": [
            {
                "id": c.id,
                "supplier_phone": c.supplier_phone,
                "supplier_name": c.supplier_name,
                "status": c.status,
                "offer_draft_id": c.offer_draft_id,
                "last_message_at": c.last_message_at,
                "message_count": c.message_count,
                "ai_analysis": c.ai_analysis,
                "window_closed": c.window_closed,
                "created_at": str(c.created_at) if c.created_at else "",
            }
            for c in conversations
        ],
        "total": total,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation with its messages."""
    stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
    res = await db.execute(stmt)
    conversation = res.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    # Get messages
    msg_stmt = (
        select(Whatsapp_messages)
        .where(Whatsapp_messages.conversation_id == conversation_id)
        .order_by(Whatsapp_messages.id)
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()
    
    # Parse AI analysis
    ai_analysis = None
    if conversation.ai_analysis:
        try:
            ai_analysis = json.loads(conversation.ai_analysis)
        except json.JSONDecodeError:
            ai_analysis = {"raw": conversation.ai_analysis}
    
    return {
        "id": conversation.id,
        "supplier_phone": conversation.supplier_phone,
        "supplier_name": conversation.supplier_name,
        "status": conversation.status,
        "offer_draft_id": conversation.offer_draft_id,
        "last_message_at": conversation.last_message_at,
        "message_count": conversation.message_count,
        "ai_analysis": ai_analysis,
        "window_closed": conversation.window_closed,
        "created_at": str(conversation.created_at) if conversation.created_at else "",
        "messages": [
            {
                "id": m.id,
                "phone": m.phone,
                "contact_name": m.contact_name,
                "direction": m.direction,
                "message_type": m.message_type,
                "content": m.content,
                "media_url": m.media_url,
                "processed": m.processed,
                "timestamp": m.timestamp,
            }
            for m in messages
        ],
    }


@router.post("/trigger-analysis")
async def trigger_analysis(
    data: TriggerAnalysisRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger AI analysis on a conversation."""
    result = await trigger_conversation_analysis(data.conversation_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/check-expired-conversations")
async def check_expired_conversations(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Check for conversations whose window expired and trigger AI analysis."""
    from services.whatsapp_conversation import check_expired_conversations as do_check
    results = await do_check(db)
    return {"checked": True, "analyzed": len(results), "results": results}


# ==================== Buyer Assistant ====================

@router.post("/buyer-reply")
async def handle_buyer_reply(
    data: BuyerReplyRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process a buyer reply with optional offer context and generate auto-reply."""
    if data.offer_code:
        result = await process_buyer_message_with_offer(
            phone=data.phone,
            contact_name=data.contact_name,
            content=data.content,
            offer_code=data.offer_code,
            custom_instructions=data.custom_instructions,
            db=db,
        )
    else:
        result = await process_buyer_message(
            phone=data.phone,
            contact_name=data.contact_name,
            message_type="text",
            content=data.content,
            media_url="",
            message_id="",
            timestamp="",
            db=db,
        )
    return result


# ==================== Send Messages ====================

@router.post("/send-message", response_model=SendMessageResponse)
async def send_whatsapp_message(
    data: SendMessageRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a text message via WhatsApp."""
    if not await is_configured(db):
        raise HTTPException(status_code=400, detail="Evolution API não configurada")

    result = await send_text_message(data.phone, data.message, db)
    return SendMessageResponse(
        success=result.get("success", False),
        message_id=result.get("message_id", ""),
        error=result.get("error", ""),
    )


@router.post("/send-offer", response_model=SendMessageResponse)
async def send_whatsapp_offer(
    data: SendOfferRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send an offer message via WhatsApp."""
    if not await is_configured(db):
        raise HTTPException(status_code=400, detail="Evolution API não configurada")

    message = format_offer_message(data.offer, data.supplier_name)
    result = await send_text_message(data.phone, message, db)
    return SendMessageResponse(
        success=result.get("success", False),
        message_id=result.get("message_id", ""),
        error=result.get("error", ""),
    )


@router.post("/send-negotiation-update", response_model=SendMessageResponse)
async def send_whatsapp_negotiation_update(
    data: SendNegotiationUpdateRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a negotiation update message via WhatsApp."""
    if not await is_configured(db):
        raise HTTPException(status_code=400, detail="Evolution API não configurada")

    message = format_negotiation_update_message(
        data.offer, data.buyer_name, data.status_label
    )
    result = await send_text_message(data.phone, message, db)
    return SendMessageResponse(
        success=result.get("success", False),
        message_id=result.get("message_id", ""),
        error=result.get("error", ""),
    )


@router.post("/send-media", response_model=SendMessageResponse)
async def send_whatsapp_media(
    data: SendMediaRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a media message via WhatsApp."""
    if not await is_configured(db):
        raise HTTPException(status_code=400, detail="Evolution API não configurada")

    result = await send_media_message(
        data.phone, data.message, data.media_url, data.media_type, db
    )
    return SendMessageResponse(
        success=result.get("success", False),
        message_id=result.get("message_id", ""),
        error=result.get("error", ""),
    )


# ==================== AI Assistant Settings ====================

@router.get("/ai-settings")
async def get_ai_settings(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI assistant settings for buyer auto-reply."""
    from models.whatsapp_settings import Whatsapp_settings

    ai_keys = [
        "AI_AUTO_REPLY_ENABLED",
        "AI_AUTO_ANALYSIS_ENABLED",
        "AI_ESCALATE_PRICE",
        "AI_ESCALATE_INTEREST",
        "AI_CUSTOM_INSTRUCTIONS",
        "AI_OFFER_PARSER_MODEL",
        "AI_BUYER_ASSISTANT_MODEL",
        "AI_ADMIN_CHAT_MODEL",
        "GROUPING_TIMEOUT_SECONDS",
    ]
    defaults = {
        "AI_AUTO_REPLY_ENABLED": "true",
        "AI_AUTO_ANALYSIS_ENABLED": "true",
        "AI_ESCALATE_PRICE": "true",
        "AI_ESCALATE_INTEREST": "true",
        "AI_CUSTOM_INSTRUCTIONS": "",
        "AI_OFFER_PARSER_MODEL": DEFAULT_AI_MODEL,
        "AI_BUYER_ASSISTANT_MODEL": DEFAULT_AI_MODEL,
        "AI_ADMIN_CHAT_MODEL": DEFAULT_AI_MODEL,
        "GROUPING_TIMEOUT_SECONDS": "600",
    }

    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key.in_(ai_keys))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    db_values = {row.setting_key: row.setting_value for row in rows}

    return {
        "auto_reply_enabled": (db_values.get("AI_AUTO_REPLY_ENABLED") or defaults["AI_AUTO_REPLY_ENABLED"]).lower() == "true",
        "auto_analysis_enabled": (db_values.get("AI_AUTO_ANALYSIS_ENABLED") or defaults["AI_AUTO_ANALYSIS_ENABLED"]).lower() == "true",
        "escalate_price": (db_values.get("AI_ESCALATE_PRICE") or defaults["AI_ESCALATE_PRICE"]).lower() == "true",
        "escalate_interest": (db_values.get("AI_ESCALATE_INTEREST") or defaults["AI_ESCALATE_INTEREST"]).lower() == "true",
        "custom_instructions": db_values.get("AI_CUSTOM_INSTRUCTIONS", defaults["AI_CUSTOM_INSTRUCTIONS"]),
        "offer_parser_model": db_values.get("AI_OFFER_PARSER_MODEL", defaults["AI_OFFER_PARSER_MODEL"]),
        "buyer_assistant_model": db_values.get("AI_BUYER_ASSISTANT_MODEL", defaults["AI_BUYER_ASSISTANT_MODEL"]),
        "admin_chat_model": db_values.get("AI_ADMIN_CHAT_MODEL", defaults["AI_ADMIN_CHAT_MODEL"]),
        "grouping_timeout_seconds": int(db_values.get("GROUPING_TIMEOUT_SECONDS") or defaults["GROUPING_TIMEOUT_SECONDS"]),
    }


@router.put("/ai-settings")
async def update_ai_settings(
    request: Request,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update AI assistant settings for buyer auto-reply."""
    body = await request.json()
    key_map = {
        "auto_reply_enabled": "AI_AUTO_REPLY_ENABLED",
        "auto_analysis_enabled": "AI_AUTO_ANALYSIS_ENABLED",
        "escalate_price": "AI_ESCALATE_PRICE",
        "escalate_interest": "AI_ESCALATE_INTEREST",
        "custom_instructions": "AI_CUSTOM_INSTRUCTIONS",
        "offer_parser_model": "AI_OFFER_PARSER_MODEL",
        "buyer_assistant_model": "AI_BUYER_ASSISTANT_MODEL",
        "admin_chat_model": "AI_ADMIN_CHAT_MODEL",
        "grouping_timeout_seconds": "GROUPING_TIMEOUT_SECONDS",
    }
    for field_name, db_key in key_map.items():
        if field_name in body:
            value = body[field_name]
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif field_name == "grouping_timeout_seconds":
                # Validate and clamp timeout to 30-600 seconds
                try:
                    val = int(value)
                    val = max(30, min(600, val))
                    value = str(val)
                except (ValueError, TypeError):
                    value = "600"
            await save_setting(db, db_key, str(value))

    return {
        "success": True,
        "message": "Configurações da IA atualizadas",
        "settings": body,
    }


# ==================== Offer Workflow ====================

class PlateLookupRequest(BaseModel):
    plate: str
    offer_id: Optional[int] = None
    dossier_id: Optional[int] = None


@router.post("/plate-lookup")
async def lookup_vehicle_plate(
    data: PlateLookupRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Look up vehicle information by license plate and store the consultation history."""
    from services.plate_lookup import lookup_plate
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
    except ValueError:
        return result


class SendForApprovalRequest(BaseModel):
    offer_id: int

class DistributeOfferRequest(BaseModel):
    offer_id: int
    category_ids: List[int]


@router.post("/offer/send-for-approval")
async def send_offer_for_approval(
    data: SendForApprovalRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a draft offer to admin via WhatsApp for approval."""
    result = await send_offer_to_admin_for_approval(data.offer_id, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/offer/distribute")
async def distribute_offer(
    data: DistributeOfferRequest,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Distribute a confirmed offer to buyers in selected categories via WhatsApp."""
    result = await distribute_offer_to_buyers(data.offer_id, data.category_ids, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/offer/{offer_id}/workflow")
async def get_offer_workflow_status(
    offer_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current workflow status of an offer."""
    stmt = select(Offers).where(Offers.id == offer_id)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()
    
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta não encontrada")
    
    # Determine available next actions based on current status
    next_actions = []
    if offer.status == "draft":
        next_actions = ["send_for_approval", "edit", "reject"]
    elif offer.status == "pending_approval":
        next_actions = ["approve", "reject", "back_to_draft"]
    elif offer.status == "approved":
        next_actions = ["confirm", "back_to_pending", "reject"]
    elif offer.status == "confirmed":
        next_actions = ["distribute", "back_to_approved", "reject"]
    elif offer.status == "distributed":
        next_actions = ["view_distributions"]
    elif offer.status == "rejected":
        next_actions = ["reactivate"]
    
    return {
        "offer_id": offer.id,
        "code": offer.code,
        "status": offer.status,
        "next_actions": next_actions,
        "title": offer.title,
        "price": offer.price,
    }


# ==================== Negotiation Expiration ====================

@router.post("/check-negotiation-expiration")
async def check_negotiation_expiration(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check for distributed offers whose negotiation deadline has expired
    and mark them as 'not_negotiated' automatically.
    """
    from datetime import datetime, timedelta

    # Find distributed offers with negotiation_status awaiting_update
    # where distributed_at is older than negotiation_deadline_hours
    stmt = select(Offers).where(
        and_(
            Offers.status == "distributed",
            Offers.negotiation_status == "awaiting_update",
            Offers.distributed_at.isnot(None),
        )
    )
    res = await db.execute(stmt)
    offers = res.scalars().all()

    expired_count = 0
    expired_offers = []

    for offer in offers:
        try:
            # Parse distributed_at (stored as ISO string)
            dist_at = offer.distributed_at
            if not dist_at:
                continue
            if isinstance(dist_at, str):
                dist_dt = datetime.fromisoformat(dist_at)
            else:
                continue

            deadline_hours = offer.negotiation_deadline_hours or 48
            deadline = dist_dt + timedelta(hours=deadline_hours)

            if datetime.utcnow() > deadline:
                offer.negotiation_status = "not_negotiated"
                offer.negotiation_substatus = "expired"
                expired_count += 1
                expired_offers.append({
                    "offer_id": offer.id,
                    "code": offer.code,
                    "title": offer.title,
                    "deadline_hours": deadline_hours,
                    "distributed_at": str(dist_dt),
                })
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse distributed_at for offer {offer.id}: {e}")
            continue

    if expired_count > 0:
        await db.commit()

    return {
        "checked": True,
        "expired_count": expired_count,
        "expired_offers": expired_offers,
    }
