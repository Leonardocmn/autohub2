"""
WhatsApp conversation management service.
Handles message grouping, conversation windowing, and AI processing triggers.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.whatsapp_messages import Whatsapp_messages
from models.whatsapp_conversations import Whatsapp_conversations
from models.suppliers import Suppliers
from models.buyers import Buyers
from models.offers import Offers
from services.whatsapp_ai import (
    parse_offer_from_messages,
    classify_buyer_message,
    generate_buyer_auto_reply,
    should_escalate_to_admin,
)
from services.whatsapp import send_text_message, is_configured
from services.formatting import build_offer_title, build_offer_description, parse_price
from models.whatsapp_settings import Whatsapp_settings
from models.whatsapp_admin_phones import Whatsapp_admin_phones

logger = logging.getLogger(__name__)

# Conversation window: configurable via DB setting GROUPING_TIMEOUT_SECONDS (default 600s = 10 min)
DEFAULT_GROUPING_TIMEOUT_SECONDS = 600  # 10 minutes


async def get_grouping_timeout_seconds(db: AsyncSession) -> int:
    """Read the configurable grouping timeout from DB settings (30-90s range per spec, but we allow up to 600s for flexibility)."""
    try:
        stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == "GROUPING_TIMEOUT_SECONDS")
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.setting_value:
            val = int(row.setting_value)
            # Clamp to reasonable range: 30 seconds to 600 seconds (10 min)
            return max(30, min(600, val))
    except Exception as e:
        logger.warning(f"Failed to read GROUPING_TIMEOUT_SECONDS: {e}")
    return DEFAULT_GROUPING_TIMEOUT_SECONDS

# AI settings defaults
DEFAULT_AI_MODEL = os.environ.get("AUTOHUB_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
AI_DEFAULTS = {
    "AI_AUTO_REPLY_ENABLED": "true",
    "AI_ESCALATE_PRICE": "true",
    "AI_ESCALATE_INTEREST": "true",
    "AI_CUSTOM_INSTRUCTIONS": "",
    "AI_OFFER_PARSER_MODEL": DEFAULT_AI_MODEL,
    "AI_BUYER_ASSISTANT_MODEL": DEFAULT_AI_MODEL,
    "AI_AUTO_ANALYSIS_ENABLED": "true",
}


async def get_ai_setting(db: AsyncSession, key: str) -> str:
    """Read a single AI setting from the database, falling back to defaults."""
    try:
        stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == key)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.setting_value is not None:
            return row.setting_value
    except Exception as e:
        logger.warning(f"Failed to read AI setting {key}: {e}")
    return AI_DEFAULTS.get(key, "")


async def get_ai_settings(db: AsyncSession) -> Dict[str, Any]:
    """Load all AI-related settings from the database."""
    keys = list(AI_DEFAULTS.keys())
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key.in_(keys))
    result = await db.execute(stmt)
    rows = result.scalars().all()
    db_values = {row.setting_key: row.setting_value for row in rows}
    
    settings = {}
    for key, default in AI_DEFAULTS.items():
        settings[key] = db_values.get(key, default)
    
    return {
        "auto_reply_enabled": settings["AI_AUTO_REPLY_ENABLED"].lower() == "true",
        "escalate_price": settings["AI_ESCALATE_PRICE"].lower() == "true",
        "escalate_interest": settings["AI_ESCALATE_INTEREST"].lower() == "true",
        "custom_instructions": settings["AI_CUSTOM_INSTRUCTIONS"],
        "offer_parser_model": settings["AI_OFFER_PARSER_MODEL"],
        "buyer_assistant_model": settings["AI_BUYER_ASSISTANT_MODEL"],
        "auto_analysis_enabled": settings["AI_AUTO_ANALYSIS_ENABLED"].lower() == "true",
    }


def _clean_phone(phone: str) -> str:
    """Clean a phone number to digits only."""
    return "".join(c for c in phone if c.isdigit())


# Cache for contact identification (avoid DB query per webhook for known contacts)
_contact_cache: Dict[str, Any] = {}
_CONTACT_CACHE_TTL = 60  # seconds


async def identify_contact(phone: str, db: AsyncSession, push_name: str = "") -> Dict[str, Any]:
    """
    Identify if a phone number belongs to a registered supplier or buyer.
    
    Uses a 60-second TTL cache to avoid DB queries on every webhook call
    for the same phone number.
    
    Args:
        phone: The sender's phone number.
        db: Database session.
        push_name: WhatsApp pushName from the Evolution API webhook (contact's display name).
    
    Returns:
        Dict with 'is_supplier', 'is_buyer', 'name', 'id' fields.
    """
    import time as _time
    clean = _clean_phone(phone)
    now = _time.time()
    
    # Check cache first
    cache_key = clean
    cached = _contact_cache.get(cache_key)
    if cached and now < cached["_expires_at"]:
        result = {k: v for k, v in cached.items() if k != "_expires_at"}
        # Update push_name if provided and different
        if push_name and not result.get("name"):
            result["name"] = push_name
        return result
    
    result = {"is_supplier": False, "is_buyer": False, "name": push_name or None, "id": None}
    
    # Check suppliers - use endswith for index-friendly query instead of contains
    stmt = select(Suppliers).where(Suppliers.phone.endswith(clean))
    supplier_res = await db.execute(stmt)
    supplier = supplier_res.scalar_one_or_none()
    if supplier:
        result["is_supplier"] = True
        result["name"] = supplier.name
        result["id"] = supplier.id
    else:
        # Check buyers - use endswith for index-friendly query
        stmt = select(Buyers).where(Buyers.phone.endswith(clean))
        buyer_res = await db.execute(stmt)
        buyer = buyer_res.scalar_one_or_none()
        if buyer:
            result["is_buyer"] = True
            result["name"] = buyer.name
            result["id"] = buyer.id
    
    # Cache the result
    result["_expires_at"] = now + _CONTACT_CACHE_TTL
    _contact_cache[cache_key] = result
    
    # Return without the internal expiry field
    return {k: v for k, v in result.items() if k != "_expires_at"}


async def get_admin_phones(db: AsyncSession) -> List[str]:
    """Get all active admin phone numbers from the admin phones table."""
    stmt = select(Whatsapp_admin_phones).where(Whatsapp_admin_phones.active == True)
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [row.phone.strip() for row in rows if row.phone]


async def notify_admin(message: str, db: AsyncSession) -> bool:
    """Send a WhatsApp notification to all active admin phones."""
    phones = await get_admin_phones(db)
    if not phones:
        logger.warning("No active admin phones configured, skipping notification")
        return False
    if not await is_configured(db):
        logger.warning("WhatsApp not configured, skipping admin notification")
        return False
    success = False
    for phone in phones:
        try:
            result = await send_text_message(phone, message, db)
            if result.get("success", False):
                success = True
        except Exception as e:
            logger.error(f"Failed to notify admin {phone}: {e}")
    return success


async def store_message(
    phone: str,
    direction: str,
    message_type: str,
    content: str,
    media_url: str = "",
    message_id: str = "",
    contact_name: str = "",
    is_supplier: bool = False,
    is_buyer: bool = False,
    conversation_id: Optional[int] = None,
    timestamp: str = "",
    db: AsyncSession = None,
) -> Whatsapp_messages:
    """Store a WhatsApp message in the database."""
    msg = Whatsapp_messages(
        phone=phone,
        contact_name=contact_name,
        direction=direction,
        message_type=message_type,
        content=content,
        media_url=media_url if media_url else None,
        message_id=message_id if message_id else None,
        conversation_id=conversation_id,
        processed=False,
        is_supplier=is_supplier,
        is_buyer=is_buyer,
        timestamp=timestamp or datetime.utcnow().isoformat(),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def find_or_create_conversation(
    phone: str,
    contact_name: str,
    is_supplier: bool,
    db: AsyncSession,
) -> Whatsapp_conversations:
    """
    Find an active conversation for this phone or create a new one.
    A conversation is considered active if:
    - It belongs to the same phone
    - Status is 'active'
    - Last message was within the configurable grouping timeout window
    """
    clean = _clean_phone(phone)
    
    # Get configurable timeout
    timeout_seconds = await get_grouping_timeout_seconds(db)
    timeout_delta = timedelta(seconds=timeout_seconds)
    
    # Look for an active conversation
    stmt = (
        select(Whatsapp_conversations)
        .where(
            and_(
                Whatsapp_conversations.supplier_phone.contains(clean),
                Whatsapp_conversations.status == "active",
                Whatsapp_conversations.window_closed == False,
            )
        )
        .order_by(desc(Whatsapp_conversations.id))
        .limit(1)
    )
    res = await db.execute(stmt)
    conversation = res.scalar_one_or_none()
    
    if conversation:
        # Check if within window
        last_msg_at = conversation.last_message_at
        if last_msg_at:
            try:
                last_dt = datetime.fromisoformat(last_msg_at)
                now = datetime.utcnow()
                if now - last_dt > timeout_delta:
                    # Window expired, close old conversation
                    conversation.window_closed = True
                    conversation.status = "expired"
                    await db.commit()
                    await db.refresh(conversation)
                    # Create new conversation
                    conversation = None
            except (ValueError, TypeError):
                pass
    
    if not conversation:
        conversation = Whatsapp_conversations(
            supplier_phone=clean,
            supplier_name=contact_name or None,
            status="active",
            message_count=0,
            window_closed=False,
            last_message_at=datetime.utcnow().isoformat(),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    return conversation


async def update_conversation_message_count(
    conversation_id: int,
    db: AsyncSession,
) -> None:
    """Update the message count and last_message_at for a conversation."""
    stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    if conv:
        conv.message_count = (conv.message_count or 0) + 1
        conv.last_message_at = datetime.utcnow().isoformat()
        await db.commit()


async def process_supplier_message(
    phone: str,
    contact_name: str,
    message_type: str,
    content: str,
    media_url: str,
    message_id: str,
    timestamp: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Process an incoming message from a supplier.
    - Store the message
    - Find or create conversation
    - Link message to conversation
    - Trigger AI analysis on any expired conversations for this phone
    - Schedule auto-analysis after conversation window expires
    """
    # Find or create conversation (this may close expired conversations)
    conversation = await find_or_create_conversation(phone, contact_name, True, db)
    
    # Store message linked to conversation
    msg = await store_message(
        phone=phone,
        direction="incoming",
        message_type=message_type,
        content=content,
        media_url=media_url,
        message_id=message_id,
        contact_name=contact_name,
        is_supplier=True,
        conversation_id=conversation.id,
        timestamp=timestamp,
        db=db,
    )
    
    # Update conversation message count
    await update_conversation_message_count(conversation.id, db)
    
    # Load AI settings
    ai_settings = await get_ai_settings(db)
    
    # Trigger analysis on any expired but unanalyzed conversations for this phone
    analyzed_conversations = []
    if ai_settings["auto_analysis_enabled"]:
        clean = _clean_phone(phone)
        expired_stmt = (
            select(Whatsapp_conversations)
            .where(
                and_(
                    Whatsapp_conversations.supplier_phone.contains(clean),
                    Whatsapp_conversations.window_closed == True,
                    Whatsapp_conversations.status == "expired",
                    Whatsapp_conversations.ai_analysis == None,
                )
            )
        )
        expired_res = await db.execute(expired_stmt)
        expired_convs = expired_res.scalars().all()
        
        for expired_conv in expired_convs:
            try:
                logger.info(f"Auto-triggering analysis for expired conversation {expired_conv.id}")
                result = await trigger_conversation_analysis(expired_conv.id, db)
                analyzed_conversations.append({"conversation_id": expired_conv.id, "status": result.get("status", "error")})
            except Exception as e:
                logger.error(f"Failed to analyze expired conversation {expired_conv.id}: {e}")
                analyzed_conversations.append({"conversation_id": expired_conv.id, "error": str(e)})
    
    # Schedule auto-analysis for current conversation as a background fallback
    if ai_settings["auto_analysis_enabled"]:
        import asyncio
        timeout_seconds = await get_grouping_timeout_seconds(db)
        asyncio.create_task(_schedule_auto_analysis(conversation.id, timeout_seconds))
    
    return {
        "message_id": msg.id,
        "conversation_id": conversation.id,
        "status": "stored",
        "auto_analysis_scheduled": ai_settings["auto_analysis_enabled"],
        "expired_analyzed": analyzed_conversations,
    }


async def _schedule_auto_analysis(conversation_id: int, delay_seconds: int) -> None:
    """
    Wait for the conversation window to expire, then trigger AI analysis.
    Runs as a background task so it doesn't block the webhook response.
    """
    import asyncio
    await asyncio.sleep(delay_seconds + 5)  # Wait window + 5s buffer
    
    try:
        from core.database import db_manager
        if not db_manager.async_session_maker:
            return
        async with db_manager.async_session_maker() as db:
            # Check if conversation still needs analysis
            stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
            res = await db.execute(stmt)
            conversation = res.scalar_one_or_none()
            
            if not conversation:
                return
            
            # Only analyze if window is still open and no analysis done yet
            if conversation.window_closed or conversation.status in ("analyzing", "draft_created"):
                return
            
            # Check if there are unprocessed messages
            msg_stmt = (
                select(Whatsapp_messages)
                .where(
                    and_(
                        Whatsapp_messages.conversation_id == conversation_id,
                        Whatsapp_messages.processed == False,
                    )
                )
            )
            msg_res = await db.execute(msg_stmt)
            unprocessed = msg_res.scalars().all()
            
            if not unprocessed:
                return
            
            logger.info(f"Auto-triggering AI analysis for conversation {conversation_id}")
            result = await trigger_conversation_analysis(conversation_id, db)
            logger.info(f"Auto-analysis result for conversation {conversation_id}: {result.get('status', 'error')}")
    
    except Exception as e:
        logger.error(f"Auto-analysis failed for conversation {conversation_id}: {e}")


async def check_expired_conversations(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Find conversations whose window has expired but haven't been analyzed yet.
    Can be called periodically or on-demand.
    """
    timeout_seconds = await get_grouping_timeout_seconds(db)
    now = datetime.utcnow()
    cutoff = (now - timedelta(seconds=timeout_seconds)).isoformat()
    
    stmt = (
        select(Whatsapp_conversations)
        .where(
            and_(
                Whatsapp_conversations.status == "active",
                Whatsapp_conversations.window_closed == False,
                Whatsapp_conversations.last_message_at < cutoff,
            )
        )
    )
    res = await db.execute(stmt)
    expired = res.scalars().all()
    
    results = []
    for conv in expired:
        try:
            result = await trigger_conversation_analysis(conv.id, db)
            results.append({"conversation_id": conv.id, "result": result})
        except Exception as e:
            logger.error(f"Failed to analyze expired conversation {conv.id}: {e}")
            results.append({"conversation_id": conv.id, "error": str(e)})
    
    return results


async def trigger_conversation_analysis(
    conversation_id: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Trigger AI analysis on a conversation's messages.
    Called when the conversation window closes or manually by admin.
    """
    # Get conversation
    stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
    res = await db.execute(stmt)
    conversation = res.scalar_one_or_none()
    if not conversation:
        return {"error": "Conversa não encontrada"}
    
    # Get all messages in this conversation
    msg_stmt = (
        select(Whatsapp_messages)
        .where(Whatsapp_messages.conversation_id == conversation_id)
        .order_by(Whatsapp_messages.id)
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()
    
    if not messages:
        return {"error": "Nenhuma mensagem encontrada na conversa"}
    
    # Mark conversation as analyzing
    conversation.status = "analyzing"
    # Save supplier_phone before commit expires the object
    supplier_phone = conversation.supplier_phone
    await db.commit()
    
    # Prepare messages for AI analysis
    message_dicts = [
        {
            "content": m.content or "",
            "message_type": m.message_type or "text",
            "media_url": m.media_url or "",
        }
        for m in messages
    ]
    
    # Close DB transaction before slow AI call
    await db.rollback()
    
    # Run AI analysis
    analysis_result = await parse_offer_from_messages(message_dicts, db=db)
    
    if "error" in analysis_result:
        # Re-fetch and update status
        stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
        res = await db.execute(stmt)
        conversation = res.scalar_one_or_none()
        if conversation:
            conversation.status = "active"
            conversation.ai_analysis = json.dumps(analysis_result, ensure_ascii=False)
            await db.commit()
        return analysis_result
    
    # Store analysis result and create draft offer
    stmt = select(Whatsapp_conversations).where(Whatsapp_conversations.id == conversation_id)
    res = await db.execute(stmt)
    conversation = res.scalar_one_or_none()
    if not conversation:
        return {"error": "Conversa não encontrada após análise"}
    
    conversation.ai_analysis = json.dumps(analysis_result, ensure_ascii=False)
    conversation.window_closed = True
    
    # Create draft offer from analysis using company template format
    # AI parser returns English field names (brand, model, version, year, etc.)
    offer = Offers(
        code=str(100000 + conversation_id),  # Use conversation_id param (int), not expired ORM attr
        supplier_id=0,  # Will be filled by admin
        title=build_offer_title(analysis_result),
        brand=analysis_result.get("brand"),
        model=analysis_result.get("model"),
        version=analysis_result.get("version"),
        year=analysis_result.get("year"),
        color=analysis_result.get("color"),
        mileage=analysis_result.get("mileage"),
        price=parse_price(analysis_result.get("supplier_price")),
        supplier_price=parse_price(analysis_result.get("supplier_price")),
        fipe=analysis_result.get("fipe_value"),
        fuel=analysis_result.get("fuel"),
        transmission=analysis_result.get("transmission"),
        has_manual=bool(analysis_result.get("has_manual")),
        has_spare_key=bool(analysis_result.get("has_spare_key")),
        is_auction=bool(analysis_result.get("is_auction")),
        suggested_category=analysis_result.get("suggested_category"),
        description=build_offer_description(analysis_result),
        status="draft",
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    # Save offer.id before next commit expires it
    offer_id = offer.id
    offer_code = offer.code
    
    # Link offer to conversation
    conversation.offer_draft_id = offer_id
    conversation.status = "draft_created"
    await db.commit()
    
    # Notify admin about new draft offer with company template
    try:
        admin_msg = (
            f"🆕 *Novo rascunho de oferta criado!*\n\n"
            f"📋 Oferta #{offer_id} (Código: {offer_code})\n"
            f"📱 Fornecedor: {supplier_phone}\n\n"
        )
        brand = analysis_result.get("brand", "")
        model = analysis_result.get("model", "")
        version = analysis_result.get("version", "")
        vehicle = f"{brand} {model} {version}".strip()
        if vehicle:
            admin_msg += f"MODELO: {vehicle}\n"
        if analysis_result.get("year"):
            admin_msg += f"ANO: {analysis_result['year']}\n"
        if analysis_result.get("fipe_value"):
            admin_msg += f"FIPE: {analysis_result['fipe_value']}\n"
        if analysis_result.get("fuel"):
            admin_msg += f"COMBUSTIVEL: {analysis_result['fuel']}\n"
        if analysis_result.get("mileage"):
            admin_msg += f"KM: {analysis_result['mileage']}\n"
        if analysis_result.get("transmission"):
            admin_msg += f"CAMBIO: {analysis_result['transmission']}\n"
        manual_val = "sim" if analysis_result.get("has_manual") else "não informado"
        admin_msg += f"MANUAL: {manual_val}\n"
        chave_val = "sim" if analysis_result.get("has_spare_key") else "não informado"
        admin_msg += f"CHAVE RESERVA: {chave_val}\n"
        if analysis_result.get("description"):
            admin_msg += f"DESCRICAO: {analysis_result['description']}\n"
        if analysis_result.get("supplier_price"):
            admin_msg += f"VALOR: {analysis_result['supplier_price']}\n"
        if analysis_result.get("suggested_category"):
            admin_msg += f"CATEGORIA: {analysis_result['suggested_category']}\n"
        admin_msg += f"\nAcesse o painel para revisar e aprovar o anúncio."
        await notify_admin(admin_msg, db)
    except Exception as e:
        logger.error(f"Failed to notify admin about draft offer: {e}")
    
    # Mark messages as processed
    msg_stmt = (
        select(Whatsapp_messages)
        .where(Whatsapp_messages.conversation_id == conversation_id)
    )
    msg_res = await db.execute(msg_stmt)
    for msg in msg_res.scalars().all():
        msg.processed = True
    await db.commit()
    
    return {
        "conversation_id": conversation_id,
        "offer_id": offer_id,
        "analysis": analysis_result,
        "status": "draft_created",
    }


async def process_buyer_message(
    phone: str,
    contact_name: str,
    message_type: str,
    content: str,
    media_url: str,
    message_id: str,
    timestamp: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Process an incoming message from a buyer.
    - Store the message
    - Classify the message
    - Generate auto-reply or escalate to admin (respecting AI settings)
    """
    # Load AI settings
    ai_settings = await get_ai_settings(db)
    
    # Store message
    msg = await store_message(
        phone=phone,
        direction="incoming",
        message_type=message_type,
        content=content,
        media_url=media_url,
        message_id=message_id,
        contact_name=contact_name,
        is_buyer=True,
        timestamp=timestamp,
        db=db,
    )
    
    # Save msg.id before any rollback, since rollback expires ORM objects
    # and accessing attributes on expired objects triggers greenlet errors in async
    msg_id = msg.id

    # If auto-reply is disabled, just store and notify admin
    if not ai_settings["auto_reply_enabled"]:
        # Mark message as processed
        stmt = select(Whatsapp_messages).where(Whatsapp_messages.id == msg_id)
        res = await db.execute(stmt)
        msg_obj = res.scalar_one_or_none()
        if msg_obj:
            msg_obj.processed = True
            await db.commit()
        
        # Always notify admin when auto-reply is off
        try:
            admin_msg = (
                f"📩 *Nova mensagem de comprador*\n\n"
                f"📱 Comprador: {contact_name or phone}\n"
                f"💬 Mensagem: {(content or '')[:200]}\n\n"
                f"Resposta automática desativada. Acesse o painel para responder."
            )
            await notify_admin(admin_msg, db)
        except Exception as e:
            logger.error(f"Failed to notify admin about buyer message: {e}")
        
        return {
            "message_id": msg_id,
            "category": "manual",
            "escalate": True,
            "auto_reply": None,
            "reason": "auto_reply_disabled",
        }
    
    # Close DB transaction before slow AI calls
    await db.rollback()
    
    # Classify the message
    category = await classify_buyer_message(content or "", db=db)
    
    # Check if we should escalate based on settings
    escalate = should_escalate_to_admin(
        category,
        content or "",
        escalate_price=ai_settings["escalate_price"],
        escalate_interest=ai_settings["escalate_interest"],
    )
    
    # Generate auto-reply or escalate
    auto_reply = None
    if not escalate:
        auto_reply = await generate_buyer_auto_reply(
            message=content or "",
            category=category,
            custom_instructions=ai_settings["custom_instructions"],
            db=db,
        )
        
        # Send auto-reply via WhatsApp if configured
        if auto_reply and await is_configured(db):
            await send_text_message(phone, auto_reply, db)
    
    # Mark message as processed
    stmt = select(Whatsapp_messages).where(Whatsapp_messages.id == msg_id)
    res = await db.execute(stmt)
    msg_obj = res.scalar_one_or_none()
    if msg_obj:
        msg_obj.processed = True
        await db.commit()
    
    # Notify admin if escalated
    if escalate:
        try:
            admin_msg = (
                f"⚠️ *Atenção: mensagem de comprador requer intervenção!*\n\n"
                f"📱 Comprador: {contact_name or phone}\n"
                f"💬 Mensagem: {(content or '')[:200]}\n"
                f"🏷️ Categoria: {category}\n\n"
                f"Acesse o painel para responder."
            )
            await notify_admin(admin_msg, db)
        except Exception as e:
            logger.error(f"Failed to notify admin about escalated buyer message: {e}")
    
    return {
        "message_id": msg_id,
        "category": category,
        "escalate": escalate,
        "auto_reply": auto_reply,
    }


async def process_buyer_message_with_offer(
    phone: str,
    contact_name: str,
    content: str,
    offer_code: str,
    custom_instructions: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Process a buyer message with a known offer context.
    Used when the offer can be identified from the conversation.
    Respects AI settings for auto-reply and escalation.
    """
    # Load AI settings
    ai_settings = await get_ai_settings(db)
    
    # If auto-reply is disabled, just notify admin
    if not ai_settings["auto_reply_enabled"]:
        try:
            admin_msg = (
                f"📩 *Mensagem de comprador (oferta #{offer_code})*\n\n"
                f"📱 Comprador: {contact_name or phone}\n"
                f"💬 Mensagem: {(content or '')[:200]}\n\n"
                f"Resposta automática desativada. Acesse o painel para responder."
            )
            await notify_admin(admin_msg, db)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        return {
            "category": "manual",
            "escalate": True,
            "auto_reply": None,
            "offer_found": bool(offer_code),
            "reason": "auto_reply_disabled",
        }
    
    # Find the offer
    stmt = select(Offers).where(Offers.code == offer_code)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()
    
    offer_data = None
    if offer:
        offer_data = {
            "code": offer.code,
            "brand": offer.brand,
            "model": offer.model,
            "version": "",
            "year": offer.year,
            "price": f"R$ {offer.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if offer.price else None,
            "status": offer.status,
        }
    
    # Close DB transaction before slow AI calls
    await db.rollback()
    
    # Use custom instructions from settings if none provided
    effective_instructions = custom_instructions or ai_settings["custom_instructions"]
    
    # Classify
    category = await classify_buyer_message(content or "", db=db)
    escalate = should_escalate_to_admin(
        category,
        content or "",
        escalate_price=ai_settings["escalate_price"],
        escalate_interest=ai_settings["escalate_interest"],
    )
    
    auto_reply = None
    if not escalate:
        auto_reply = await generate_buyer_auto_reply(
            message=content or "",
            category=category,
            offer_data=offer_data,
            custom_instructions=effective_instructions,
            db=db,
        )
        
        if auto_reply and await is_configured(db):
            await send_text_message(phone, auto_reply, db)
    
    # Notify admin if escalated
    if escalate:
        try:
            admin_msg = (
                f"⚠️ *Comprador requer intervenção (oferta #{offer_code})*\n\n"
                f"📱 Comprador: {contact_name or phone}\n"
                f"💬 Mensagem: {(content or '')[:200]}\n"
                f"🏷️ Categoria: {category}\n\n"
                f"Acesse o painel para responder."
            )
            await notify_admin(admin_msg, db)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    return {
        "category": category,
        "escalate": escalate,
        "auto_reply": auto_reply,
        "offer_found": offer is not None,
    }

