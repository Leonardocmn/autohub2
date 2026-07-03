"""
Admin menu state machine for WhatsApp numeric navigation.

This service manages the conversation state for each admin, routing
numeric selections through the menu tree and executing action handlers.

Key behaviors:
- Each admin has a session with menu_path, menu_data, last_interaction_at
- Numeric input navigates menus; free-text input feeds input handlers
- "menu", "0", "cancelar" → return to main menu immediately
- 10-minute inactivity → auto-reset to main menu
- Natural language fallback → AI chat when no menu state is active
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.whatsapp_admin_sessions import Whatsapp_admin_sessions
from services.admin_menu_defs import (
    format_menu_message,
    get_input_handler,
    get_input_prompt,
    get_menu,
    get_parent_menu,
    is_input_menu,
    resolve_option,
)
from services.whatsapp import send_text_message

logger = logging.getLogger(__name__)

# Session timeout: 10 minutes of inactivity
SESSION_TIMEOUT_MINUTES = 10

# Global reset keywords
RESET_KEYWORDS = {"menu", "0", "cancelar", "cancel", "voltar", "inicio", "principal"}


# ==================== Session Management ====================

async def _get_session(db: AsyncSession, phone: str) -> tuple:
    """Get or create an admin menu session.
    
    Returns (session, is_new) where is_new indicates if the session was just created.
    """
    stmt = select(Whatsapp_admin_sessions).where(
        Whatsapp_admin_sessions.admin_phone == phone
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    is_new = False
    if not session:
        session = Whatsapp_admin_sessions(
            admin_phone=phone,
            state="menu",
            menu_path="main",
            menu_data="{}",
            last_interaction_at=None,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        is_new = True
    return (session, is_new)


async def _update_session(
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_path: Optional[str] = None,
    menu_data: Optional[Dict] = None,
) -> None:
    """Update session state and touch the interaction timestamp."""
    if menu_path is not None:
        session.menu_path = menu_path
    if menu_data is not None:
        session.menu_data = json.dumps(menu_data, ensure_ascii=False)
    session.last_interaction_at = datetime.now(timezone.utc)
    session.state = "menu"
    await db.commit()


def _get_menu_data(session: Whatsapp_admin_sessions) -> Dict:
    """Parse menu_data JSON from session."""
    try:
        return json.loads(session.menu_data or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


def _is_session_expired(session: Whatsapp_admin_sessions) -> bool:
    """Check if the session has been inactive for more than SESSION_TIMEOUT_MINUTES."""
    if not session.last_interaction_at:
        return True
    last = session.last_interaction_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - last) > timedelta(minutes=SESSION_TIMEOUT_MINUTES)


# ==================== Main Entry Point ====================

async def handle_admin_menu(
    phone: str,
    content: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Main entry point for admin menu navigation.

    Called from the webhook when an admin sends a message.
    Returns {"handled": True} if the message was processed by the menu system,
    or {"handled": False} if it should fall through to other handlers.

    Flow:
    1. Get/create session
    2. Check for timeout → reset to main
    3. Check for reset keywords → go to main
    4. If current menu expects input → route to input handler
    5. If numeric input → resolve option and navigate/execute
    6. If not handled → return False for AI chat fallback
    """
    if not content or not content.strip():
        return {"handled": False}

    text = content.strip()
    text_lower = text.lower()

    # Get or create session
    session, is_new = await _get_session(db, phone)

    # If this is a brand new session (just created), show the main menu
    if is_new:
        session.last_interaction_at = datetime.now(timezone.utc)
        await db.commit()
        await send_text_message(phone, format_menu_message("main"), db)
        return {"handled": True, "action": "menu_initialized"}

    # Check for session timeout
    if _is_session_expired(session):
        await _reset_to_main(db, session)
        await send_text_message(
            phone,
            "⏰ Sessão expirada por inatividade.\n\n" + format_menu_message("main"),
            db,
        )
        return {"handled": True, "action": "session_timeout"}

    # Check for global reset keywords
    if text_lower in RESET_KEYWORDS:
        current_path = session.menu_path or "main"
        if current_path == "main":
            # Already at main, just re-display
            await send_text_message(phone, format_menu_message("main"), db)
        else:
            await _reset_to_main(db, session)
            await send_text_message(phone, format_menu_message("main"), db)
        return {"handled": True, "action": "reset_to_main"}

    # If current menu expects free-text input
    current_path = session.menu_path or "main"
    if is_input_menu(current_path):
        handler_name = get_input_handler(current_path)
        if handler_name:
            result = await _execute_input_handler(handler_name, phone, text, db, session)
            return result
        # No handler defined, treat as invalid
        await send_text_message(phone, "❌ Erro interno. Digite *menu* para recomeçar.", db)
        await _reset_to_main(db, session)
        return {"handled": True, "action": "input_handler_missing"}

    # Try to parse as numeric option
    try:
        option_num = int(text.strip())
    except (ValueError, TypeError):
        # Not a number and not in an input menu — always show the menu
        # This is the default behavior: any unrecognized input shows the menu
        await send_text_message(
            phone,
            "⚠️ Opção não reconhecida. Digite apenas o *número* da opção desejada.\n\n"
            + format_menu_message(current_path),
            db,
        )
        return {"handled": True, "action": "show_menu_fallback"}

    # Resolve the numeric option
    menu_data = _get_menu_data(session)
    action = resolve_option(current_path, option_num, dynamic_data=menu_data)

    if action is None:
        # Invalid option number
        menu = get_menu(current_path)
        max_opt = 0
        if menu:
            opts = menu.get("options", [])
            if menu.get("dynamic_options") and menu_data:
                opts = menu_data.get("dynamic_options", [])
            if opts:
                max_opt = max(num for num, _, _ in opts)
        await send_text_message(
            phone,
            f"⚠️ Opção inválida. Digite um número de 1 a {max_opt}.\n"
            f"Ou digite *menu* para voltar ao menu principal.",
            db,
        )
        return {"handled": True, "action": "invalid_option"}

    # Execute the action
    return await _execute_action(action, phone, db, session, menu_data)


# ==================== Action Execution ====================

async def _execute_action(
    action: str,
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_data: Dict,
) -> Dict[str, Any]:
    """Execute a menu action (submenu, handler, or back)."""
    if action == "back":
        parent = get_parent_menu(session.menu_path or "main")
        await _update_session(db, session, menu_path=parent, menu_data={})
        await send_text_message(phone, format_menu_message(parent), db)
        return {"handled": True, "action": "back"}

    if action.startswith("submenu:"):
        target = action.split(":", 1)[1]
        await _update_session(db, session, menu_path=target, menu_data={})
        # Check if target is an input menu
        if is_input_menu(target):
            prompt = get_input_prompt(target)
            await send_text_message(
                phone,
                f"*{get_menu(target).get('title', '')}*\n\n{prompt}",
                db,
            )
        else:
            await send_text_message(phone, format_menu_message(target), db)
        return {"handled": True, "action": "submenu", "target": target}

    if action.startswith("handler:"):
        handler_name = action.split(":", 1)[1]
        result = await _execute_handler(handler_name, phone, db, session, menu_data)
        return result

    # Unknown action type
    logger.warning(f"Unknown menu action: {action}")
    await send_text_message(phone, "❌ Ação não reconhecida. Digite *menu*.", db)
    await _reset_to_main(db, session)
    return {"handled": True, "action": "unknown_action"}


# ==================== Handler Dispatch ====================

# Registry mapping handler names to async functions
_HANDLER_REGISTRY: Dict[str, Any] = {}


def register_handler(name: str):
    """Decorator to register a menu handler function."""
    def decorator(func):
        _HANDLER_REGISTRY[name] = func
        return func
    return decorator


async def _execute_handler(
    handler_name: str,
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_data: Dict,
) -> Dict[str, Any]:
    """Execute a registered handler by name."""
    handler = _HANDLER_REGISTRY.get(handler_name)
    if not handler:
        logger.error(f"Menu handler not found: {handler_name}")
        await send_text_message(phone, "❌ Função não disponível. Digite *menu*.", db)
        await _reset_to_main(db, session)
        return {"handled": True, "action": "handler_not_found"}

    try:
        result = await handler(phone, db, session, menu_data)
        return result
    except Exception as e:
        logger.error(f"Menu handler error ({handler_name}): {e}", exc_info=True)
        await send_text_message(
            phone,
            "❌ Erro ao processar. Digite *menu* para voltar.",
            db,
        )
        await _reset_to_main(db, session)
        return {"handled": True, "action": "handler_error", "error": str(e)}


async def _execute_input_handler(
    handler_name: str,
    phone: str,
    text: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
) -> Dict[str, Any]:
    """Execute a registered input handler by name."""
    handler = _HANDLER_REGISTRY.get(handler_name)
    if not handler:
        logger.error(f"Input handler not found: {handler_name}")
        await send_text_message(phone, "❌ Erro interno. Digite *menu*.", db)
        await _reset_to_main(db, session)
        return {"handled": True, "action": "input_handler_not_found"}

    try:
        result = await handler(phone, db, session, _get_menu_data(session), text)
        return result
    except Exception as e:
        logger.error(f"Input handler error ({handler_name}): {e}", exc_info=True)
        await send_text_message(
            phone,
            "❌ Erro ao processar. Digite *menu* para voltar.",
            db,
        )
        await _reset_to_main(db, session)
        return {"handled": True, "action": "input_handler_error", "error": str(e)}


# ==================== Utility Functions ====================

async def _reset_to_main(db: AsyncSession, session: Whatsapp_admin_sessions) -> None:
    """Reset session to main menu."""
    session.menu_path = "main"
    session.menu_data = "{}"
    session.state = "menu"
    session.last_interaction_at = datetime.now(timezone.utc)
    await db.commit()


async def _return_to_parent(
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    delay_message: str = "",
) -> None:
    """Return to parent menu after completing an action, optionally showing a result message first."""
    parent = get_parent_menu(session.menu_path or "main")
    await _update_session(db, session, menu_path=parent, menu_data={})
    if delay_message:
        await send_text_message(phone, delay_message, db)
    await send_text_message(phone, format_menu_message(parent), db)


async def _show_menu_and_update(
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_path: str,
    menu_data: Optional[Dict] = None,
    prefix_message: str = "",
) -> None:
    """Navigate to a menu, optionally showing a prefix message first."""
    await _update_session(db, session, menu_path=menu_path, menu_data=menu_data or {})
    if prefix_message:
        await send_text_message(phone, prefix_message, db)
    await send_text_message(phone, format_menu_message(menu_path, dynamic_data=menu_data), db)


# ==================== Handler Implementations ====================

# ---------- Help ----------

@register_handler("help")
async def handler_help(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Show help information."""
    help_text = (
        "📖 *AJUDA - AUTOHUB*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Navegue pelo menu digitando apenas números.\n\n"
        "📌 *Comandos especiais:*\n"
        "• *menu* ou *0* — Voltar ao menu principal\n"
        "• *cancelar* — Cancelar operação atual\n\n"
        "⏱️ Sessão expira após 10 min sem interação.\n\n"
        "💬 Você também pode digitar em linguagem natural "
        "que a IA entenderá e executará a ação."
    )
    await send_text_message(phone, help_text, db)
    # Return to main menu
    await _reset_to_main(db, session)
    await send_text_message(phone, format_menu_message("main"), db)
    return {"handled": True, "action": "help"}


# ---------- Vehicles ----------

@register_handler("vehicles_pending")
async def handler_vehicles_pending(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List pending offers."""
    from models.offers import Offers
    stmt = select(Offers).where(
        Offers.status.in_(["pending_approval", "approved", "confirmed"])
    ).order_by(Offers.id.desc()).limit(15)
    res = await db.execute(stmt)
    offers = res.scalars().all()

    if not offers:
        await _return_to_parent(phone, db, session, "📋 Nenhuma oferta pendente no momento.")
        return {"handled": True, "action": "vehicles_pending_empty"}

    lines = [f"📋 *OFERTAS PENDENTES* ({len(offers)})\n"]
    for o in offers:
        status_icon = {"pending_approval": "🟡", "approved": "🟢", "confirmed": "🔵"}.get(o.status, "⚪")
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        lines.append(f"{status_icon} #{o.code} — {o.title or o.brand + ' ' + o.model} {price_str}")
    lines.append(f"\n_Total: {len(offers)} ofertas_")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "vehicles_pending"}


@register_handler("vehicles_new_offer")
async def handler_vehicles_new_offer(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Start the ad creation flow via existing service."""
    from services.admin_ad_workflow import handle_admin_ad_command
    result = await handle_admin_ad_command(phone, "CRIAR ANUNCIO", "text", "", db)
    # Reset menu state since ad workflow manages its own session
    await _reset_to_main(db, session)
    return {"handled": True, "action": "vehicles_new_offer", "ad_result": result}


@register_handler("vehicles_search_query")
async def handler_vehicles_search(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Search vehicles by plate or name."""
    from models.offers import Offers
    search = re.sub(r"[^A-Za-z0-9\s]", "", text.strip())
    stmt = select(Offers).order_by(Offers.id.desc()).limit(20)
    res = await db.execute(stmt)
    all_offers = res.scalars().all()

    # Filter by plate or title/brand/model
    search_upper = search.upper()
    matches = []
    for o in all_offers:
        searchable = f"{o.code} {o.plate or ''} {o.title or ''} {o.brand or ''} {o.model or ''}".upper()
        if search_upper in searchable:
            matches.append(o)

    if not matches:
        await _return_to_parent(phone, db, session, f"🔍 Nenhum veículo encontrado para \"{search}\".")
        return {"handled": True, "action": "vehicles_search_empty"}

    lines = [f"🔍 *RESULTADO* ({len(matches)} encontrado(s))\n"]
    for o in matches[:10]:
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        plate_str = f" [{o.plate}]" if o.plate else ""
        lines.append(f"#{o.code} — {o.brand or ''} {o.model or ''}{plate_str} {price_str} ({o.status})")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "vehicles_search"}


@register_handler("vehicles_send_select")
async def handler_vehicles_send_select(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Select an offer to send by code or plate."""
    from models.offers import Offers
    search = text.strip().upper().lstrip("#")
    # Try by code first
    stmt = select(Offers).where(Offers.code == search)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    # Try by plate
    if not offer:
        plate_clean = re.sub(r"[^A-Za-z0-9]", "", search)
        stmt = select(Offers).where(Offers.plate == plate_clean)
        res = await db.execute(stmt)
        offer = res.scalar_one_or_none()

    if not offer:
        await _return_to_parent(phone, db, session, f"❌ Oferta \"{text.strip()}\" não encontrada.")
        return {"handled": True, "action": "vehicles_send_not_found"}

    # Show categories for selection
    from models.categories import Categories
    from models.buyer_categories import Buyer_categories
    from sqlalchemy import func as sqlfunc

    cat_stmt = select(Categories).order_by(Categories.id)
    cat_res = await db.execute(cat_stmt)
    categories = cat_res.scalars().all()

    if not categories:
        await _return_to_parent(phone, db, session, "❌ Nenhuma categoria cadastrada. Crie categorias primeiro.")
        return {"handled": True, "action": "vehicles_send_no_categories"}

    # Build dynamic options
    dyn_opts = []
    for i, cat in enumerate(categories, 1):
        count_stmt = select(sqlfunc.count(Buyer_categories.id)).where(Buyer_categories.category_id == cat.id)
        count_res = await db.execute(count_stmt)
        buyer_count = count_res.scalar_one_or_none() or 0
        dyn_opts.append((i, f"{cat.name} ({buyer_count} compradores)", f"handler:vehicles_send_to_category_{cat.id}"))
    dyn_opts.append((len(categories) + 1, "Todas as categorias", f"handler:vehicles_send_to_all"))
    dyn_opts.append((len(categories) + 2, "Cancelar", "back"))

    new_data = {
        "dynamic_options": dyn_opts,
        "offer_id": offer.id,
        "offer_code": offer.code,
        "offer_title": offer.title or f"{offer.brand} {offer.model}",
    }

    prefix = f"📋 Oferta: *#{offer.code}* — {offer.title or offer.brand + ' ' + offer.model}\n"
    await _show_menu_and_update(phone, db, session, "vehicles_send_confirm", new_data, prefix)
    return {"handled": True, "action": "vehicles_send_select"}


async def _send_offer_to_categories(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, category_ids: list) -> Dict:
    """Send an offer to specified categories."""
    from services.offer_workflow import distribute_offer_to_buyers
    offer_id = menu_data.get("offer_id")
    if not offer_id:
        await _return_to_parent(phone, db, session, "❌ Erro: oferta não encontrada na sessão.")
        return {"handled": True, "action": "send_error"}

    try:
        result = await distribute_offer_to_buyers(offer_id, category_ids, db)
        if "error" in result:
            await _return_to_parent(phone, db, session, f"❌ {result['error']}")
        else:
            count = result.get("sent_count", 0)
            await _return_to_parent(phone, db, session, f"✅ Oferta enviada para {count} comprador(es)!")
    except Exception as e:
        logger.error(f"Error sending offer: {e}")
        await _return_to_parent(phone, db, session, f"❌ Erro ao enviar: {str(e)[:100]}")
    return {"handled": True, "action": "vehicles_send_done"}


@register_handler("vehicles_sold_select_buyer")
async def handler_vehicles_sold_select(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Select an offer for marking as sold, then show buyer selection."""
    from models.offers import Offers
    search = text.strip().upper().lstrip("#")
    # Try by code
    stmt = select(Offers).where(Offers.code == search)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    # Try by plate
    if not offer:
        plate_clean = re.sub(r"[^A-Za-z0-9]", "", search)
        stmt = select(Offers).where(Offers.plate == plate_clean)
        res = await db.execute(stmt)
        offer = res.scalar_one_or_none()

    if not offer:
        await _return_to_parent(phone, db, session, f"❌ Oferta \"{text.strip()}\" não encontrada.")
        return {"handled": True, "action": "sold_not_found"}

    # Get buyers who received this offer
    from models.offer_distributions import Offer_distributions
    from models.buyers import Buyers
    dist_stmt = (
        select(Buyers)
        .join(Offer_distributions, Offer_distributions.buyer_id == Buyers.id)
        .where(Offer_distributions.offer_id == offer.id)
        .order_by(Buyers.name)
    )
    dist_res = await db.execute(dist_stmt)
    buyers = dist_res.scalars().all()

    # Also get all active buyers as fallback
    if not buyers:
        all_stmt = select(Buyers).where(Buyers.status == "active").order_by(Buyers.name).limit(20)
        all_res = await db.execute(all_stmt)
        buyers = all_res.scalars().all()

    dyn_opts = []
    for i, b in enumerate(buyers[:20], 1):
        dyn_opts.append((i, b.name, f"handler:vehicles_sold_buyer_{b.id}"))
    dyn_opts.append((len(buyers[:20]) + 1, "Buscar comprador", "submenu:vehicles_sold_search_buyer"))
    dyn_opts.append((len(buyers[:20]) + 2, "Cancelar", "back"))

    new_data = {
        "dynamic_options": dyn_opts,
        "offer_id": offer.id,
        "offer_code": offer.code,
        "offer_title": offer.title or f"{offer.brand} {offer.model}",
    }

    prefix = f"📋 Oferta: *#{offer.code}* — {offer.title or offer.brand + ' ' + offer.model}\n"
    await _show_menu_and_update(phone, db, session, "vehicles_sold_select_buyer", new_data, prefix)
    return {"handled": True, "action": "sold_select_buyer"}


@register_handler("vehicles_sold_entered_yes")
async def handler_vehicles_sold_entered_yes(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Buyer entered - proceed to docs."""
    menu_data["entered"] = "yes"
    await _show_menu_and_update(phone, db, session, "vehicles_sold_docs", menu_data)
    return {"handled": True, "action": "sold_entered_yes"}


@register_handler("vehicles_sold_entered_no")
async def handler_vehicles_sold_entered_no(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Buyer did not enter - finalize as not entered."""
    from models.offers import Offers
    offer_id = menu_data.get("offer_id")
    if offer_id:
        stmt = select(Offers).where(Offers.id == offer_id)
        res = await db.execute(stmt)
        offer = res.scalar_one_or_none()
        if offer:
            offer.negotiation_status = "negotiated"
            offer.negotiation_substatus = "not_entered"
            await db.commit()

    buyer_name = menu_data.get("buyer_name", "Comprador")
    await _return_to_parent(phone, db, session, f"✅ Registrado: *{buyer_name}* — Não Entrou.")
    return {"handled": True, "action": "sold_not_entered"}


@register_handler("vehicles_sold_docs_ok")
async def handler_vehicles_sold_docs_ok(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Docs OK - proceed to status."""
    menu_data["docs"] = "ok"
    await _show_menu_and_update(phone, db, session, "vehicles_sold_status", menu_data)
    return {"handled": True, "action": "sold_docs_ok"}


@register_handler("vehicles_sold_docs_pending")
async def handler_vehicles_sold_docs_pending(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Docs pending - proceed to status."""
    menu_data["docs"] = "pending"
    await _show_menu_and_update(phone, db, session, "vehicles_sold_status", menu_data)
    return {"handled": True, "action": "sold_docs_pending"}


@register_handler("vehicles_sold_status_exchange")
async def handler_vehicles_sold_status_exchange(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Mark as in exchange process."""
    await _finalize_sold(phone, db, session, menu_data, "exchange")
    return {"handled": True, "action": "sold_status_exchange"}


@register_handler("vehicles_sold_status_available")
async def handler_vehicles_sold_status_available(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Mark as available for pickup."""
    await _finalize_sold(phone, db, session, menu_data, "available")
    return {"handled": True, "action": "sold_status_available"}


@register_handler("vehicles_sold_status_withdrawn")
async def handler_vehicles_sold_status_withdrawn(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Mark as withdrawn - finalize."""
    await _finalize_sold(phone, db, session, menu_data, "withdrawn")
    return {"handled": True, "action": "sold_status_withdrawn"}


async def _finalize_sold(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, status: str) -> None:
    """Finalize the sold flow by updating the offer."""
    from models.offers import Offers
    offer_id = menu_data.get("offer_id")
    buyer_name = menu_data.get("buyer_name", "Comprador")

    status_labels = {
        "exchange": "Em processo de troca",
        "available": "Disponível para retirada",
        "withdrawn": "Veículo retirado",
    }

    if offer_id:
        stmt = select(Offers).where(Offers.id == offer_id)
        res = await db.execute(stmt)
        offer = res.scalar_one_or_none()
        if offer:
            offer.negotiation_status = "negotiated"
            offer.negotiation_substatus = "entered" if menu_data.get("entered") == "yes" else "not_entered"
            if status == "withdrawn":
                offer.status = "finalized"
            await db.commit()

    label = status_labels.get(status, status)
    msg = f"✅ *Negociação finalizada com sucesso.*\n\n👤 {buyer_name}\n📊 {label}"
    if menu_data.get("docs") == "ok":
        msg += "\n📄 Documentação OK"
    elif menu_data.get("docs") == "pending":
        msg += "\n📄 Documentação Pendente"

    await _return_to_parent(phone, db, session, msg)


@register_handler("vehicles_edit_show")
async def handler_vehicles_edit_show(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Show offer details for editing."""
    from models.offers import Offers
    search = text.strip().upper().lstrip("#")
    stmt = select(Offers).where(Offers.code == search)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    if not offer:
        plate_clean = re.sub(r"[^A-Za-z0-9]", "", search)
        stmt = select(Offers).where(Offers.plate == plate_clean)
        res = await db.execute(stmt)
        offer = res.scalar_one_or_none()

    if not offer:
        await _return_to_parent(phone, db, session, f"❌ Oferta \"{text.strip()}\" não encontrada.")
        return {"handled": True, "action": "edit_not_found"}

    price_str = f"R$ {offer.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if offer.price else "-"
    lines = [
        f"📋 *OFERTA #{offer.code}*",
        "",
        f"🏷️ Título: {offer.title or '-'}",
        f"🏭 Marca: {offer.brand or '-'}",
        f"🚘 Modelo: {offer.model or '-'}",
        f"📅 Ano: {offer.year or '-'}",
        f"🎨 Cor: {offer.color or '-'}",
        f"💰 Preço: {price_str}",
        f"📏 KM: {offer.km or '-'}",
        f"🔖 Placa: {offer.plate or '-'}",
        f"📊 Status: {offer.status}",
        "",
        "💡 Para editar, acesse o painel web ou use comandos diretos.",
    ]
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "vehicles_edit_show"}


@register_handler("vehicles_history_query")
async def handler_vehicles_history(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Show vehicle history by plate."""
    from models.offers import Offers
    from models.negotiation_history import Negotiation_history
    from models.offer_distributions import Offer_distributions
    from models.buyers import Buyers

    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await _return_to_parent(phone, db, session, "⚠️ Placa inválida. Digite uma placa válida (ex: ABC1D23).")
        return {"handled": True, "action": "history_invalid_plate"}

    # Find offers with this plate
    stmt = select(Offers).where(Offers.plate == plate).order_by(Offers.id.desc())
    res = await db.execute(stmt)
    offers = res.scalars().all()

    if not offers:
        await _return_to_parent(phone, db, session, f"🔍 Nenhum histórico encontrado para a placa {plate}.")
        return {"handled": True, "action": "history_not_found"}

    lines = [f"📋 *HISTÓRICO — {plate}*\n"]
    for o in offers:
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        lines.append(f"#{o.code} — {o.brand or ''} {o.model or ''} {price_str}")
        lines.append(f"  Status: {o.status} | Negociação: {o.negotiation_status or '-'}")

        # Get negotiation history
        hist_stmt = select(Negotiation_history).where(Negotiation_history.offer_id == o.id).order_by(Negotiation_history.id)
        hist_res = await db.execute(hist_stmt)
        histories = hist_res.scalars().all()
        for h in histories[:5]:
            buyer_name = ""
            if h.buyer_id:
                b_stmt = select(Buyers).where(Buyers.id == h.buyer_id)
                b_res = await db.execute(b_stmt)
                buyer = b_res.scalar_one_or_none()
                if buyer:
                    buyer_name = buyer.name
            lines.append(f"  → {buyer_name or 'Comprador'}: {h.status or '-'} ({h.substatus or '-'})")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "vehicles_history"}


# ---------- Queries ----------

@register_handler("query_basic")
async def handler_query_basic(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Basic plate lookup."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida. Digite uma placa válida (ex: ABC1D23).", db)
        return {"handled": True, "action": "query_basic_invalid"}

    from services.plate_lookup import lookup_plate
    result = await lookup_plate(plate)
    if result.get("success"):
        source = result.get("source", "")
        source_label = "ConsultarPlaca" if source == "consultarplaca" else "BrasilAPI"
        lines = [
            "🚗 *CONSULTA BÁSICA*",
            f"📡 Fonte: {source_label}",
            "",
            f"🔖 Placa: {result['plate']}",
            f"🏭 Marca: {result.get('brand', '-')}",
            f"🚘 Modelo: {result.get('model', '-')}",
            f"📅 Ano: {result.get('ano_modelo') or result.get('year', '-')}",
            f"🎨 Cor: {result.get('color', '-')}",
            f"⛽ Combustível: {result.get('fuel', '-')}",
        ]
        if result.get("fipe_price"):
            lines.append(f"\n💰 *FIPE: {result['fipe_price']}*")
        await _return_to_parent(phone, db, session, "\n".join(lines))
    else:
        await _return_to_parent(phone, db, session, f"❌ {result.get('error', 'Erro ao consultar placa')}")
    return {"handled": True, "action": "query_basic"}


@register_handler("query_complete")
async def handler_query_complete(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Complete plate lookup with all details."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida. Digite uma placa válida.", db)
        return {"handled": True, "action": "query_complete_invalid"}

    from services.plate_lookup import lookup_plate
    from services.formatting import format_brl_price
    result = await lookup_plate(plate)
    if result.get("success"):
        source = result.get("source", "")
        source_label = "ConsultarPlaca" if source == "consultarplaca" else "BrasilAPI"
        lines = [
            "🚗 *CONSULTA COMPLETA*",
            f"📡 Fonte: {source_label}",
            "",
            f"🔖 Placa: {result['plate']}",
            f"🏭 Marca: {result.get('brand', '-')}",
            f"🚘 Modelo: {result.get('model', '-')}",
            f"📅 Ano Fabricação: {result.get('ano_fabricacao') or result.get('year', '-')}",
            f"📅 Ano Modelo: {result.get('ano_modelo') or result.get('year', '-')}",
            f"🎨 Cor: {result.get('color', '-')}",
            f"⛽ Combustível: {result.get('fuel', '-')}",
        ]
        for key, icon, label in [
            ("segment", "🏷️", "Segmento"),
            ("procedence", "🌎", "Procedência"),
            ("municipality", "🏙️", "Município"),
            ("uf", "📍", "UF"),
            ("chassi", "🔢", "Chassi"),
            ("power", "⚡", "Potência"),
            ("displacement", "🔧", "Cilindradas"),
        ]:
            if result.get(key):
                unit = " cv" if key == "power" else (" cc" if key == "displacement" else "")
                lines.append(f"{icon} {label}: {result[key]}{unit}")
        if result.get("fipe_price"):
            lines.append(f"\n💰 *FIPE: {result['fipe_price']}*")
        if result.get("fipe_reference"):
            lines.append(f"📊 Referência: {result['fipe_reference']}")
        if result.get("fipe_code"):
            lines.append(f"📋 Código FIPE: {result['fipe_code']}")
        fipe_versions = result.get("fipe_versions", [])
        if len(fipe_versions) > 1:
            lines.append(f"\n📋 *Versões FIPE ({len(fipe_versions)}):*")
            for i, v in enumerate(fipe_versions[:5]):
                vn = v.get("modelo_versao", "-")
                vp = v.get("preco", "-")
                if vp and vp != "-":
                    vp = format_brl_price(vp)
                lines.append(f"  {i+1}. {vn}: {vp}")
            if len(fipe_versions) > 5:
                lines.append(f"  ... e mais {len(fipe_versions) - 5} versões")
        await _return_to_parent(phone, db, session, "\n".join(lines))
    else:
        await _return_to_parent(phone, db, session, f"❌ {result.get('error', 'Erro ao consultar placa')}")
    return {"handled": True, "action": "query_complete"}


@register_handler("query_debts")
async def handler_query_debts(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Debts query (placeholder - uses basic lookup for now)."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida.", db)
        return {"handled": True, "action": "query_debts_invalid"}
    await _return_to_parent(phone, db, session, f"🔍 Consulta de débitos para {plate}.\n⚠️ Consulta de débitos requer integração com SINESP/SENAT. Em breve disponível.")
    return {"handled": True, "action": "query_debts"}


@register_handler("query_fines")
async def handler_query_fines(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Fines query (placeholder)."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida.", db)
        return {"handled": True, "action": "query_fines_invalid"}
    await _return_to_parent(phone, db, session, f"🔍 Consulta de multas para {plate}.\n⚠️ Consulta de multas requer integração com SINESP/SENAT. Em breve disponível.")
    return {"handled": True, "action": "query_fines"}


@register_handler("query_encumbrance")
async def handler_query_encumbrance(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Encumbrance query (placeholder)."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida.", db)
        return {"handled": True, "action": "query_encumbrance_invalid"}
    await _return_to_parent(phone, db, session, f"🔍 Consulta de gravame para {plate}.\n⚠️ Consulta de gravame requer integração com SINESP/SENAT. Em breve disponível.")
    return {"handled": True, "action": "query_encumbrance"}


@register_handler("query_auction")
async def handler_query_auction(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Auction history query (placeholder)."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida.", db)
        return {"handled": True, "action": "query_auction_invalid"}
    await _return_to_parent(phone, db, session, f"🔍 Histórico de leilão para {plate}.\n⚠️ Consulta de leilão requer integração com SINESP/SENAT. Em breve disponível.")
    return {"handled": True, "action": "query_auction"}


@register_handler("query_accident")
async def handler_query_accident(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Accident query (placeholder)."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida.", db)
        return {"handled": True, "action": "query_accident_invalid"}
    await _return_to_parent(phone, db, session, f"🔍 Consulta de sinistro para {plate}.\n⚠️ Consulta de sinistro requer integração com SINESP/SENAT. Em breve disponível.")
    return {"handled": True, "action": "query_accident"}


@register_handler("query_fipe")
async def handler_query_fipe(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """FIPE lookup by plate."""
    plate = re.sub(r"[^A-Za-z0-9]", "", text.strip()).upper()
    if len(plate) < 7:
        await send_text_message(phone, "⚠️ Placa inválida. Digite uma placa válida (ex: ABC1D23).", db)
        return {"handled": True, "action": "query_fipe_invalid"}

    from services.fipe_lookup import lookup_fipe_by_plate
    from services.formatting import format_brl_price
    result = await lookup_fipe_by_plate(plate, db, phone=phone, source="whatsapp_menu")
    if result.get("success"):
        source = result.get("source", "")
        source_label = "ConsultarPlaca" if source == "consultarplaca" else "BrasilAPI"
        lines = [
            "💰 *CONSULTA FIPE*",
            f"📡 Fonte: {source_label}",
            "",
            f"🔖 Placa: {result.get('plate', plate)}",
            f"🏭 Marca: {result.get('brand', '-')}",
            f"🚘 Modelo: {result.get('model', '-')}",
            f"📅 Ano: {result.get('year', '-')}",
            f"🎨 Cor: {result.get('color', '-')}",
            f"⛽ Combustível: {result.get('fuel', '-')}",
        ]
        if result.get("fipe_code"):
            lines.append(f"📋 Código FIPE: {result['fipe_code']}")
        if result.get("fipe_price"):
            lines.append(f"\n💎 *FIPE: {result['fipe_price']}*")
        fipe_versions = result.get("fipe_versions", [])
        if len(fipe_versions) > 1:
            lines.append(f"\n📋 *Versões FIPE ({len(fipe_versions)}):*")
            for i, v in enumerate(fipe_versions[:8]):
                vn = v.get("modelo_versao", "-")
                vp = v.get("preco", "-")
                if vp and vp != "-":
                    vp = format_brl_price(vp)
                lines.append(f"  {i+1}. {vn}: {vp}")
            if len(fipe_versions) > 8:
                lines.append(f"  ... e mais {len(fipe_versions) - 8} versões")
        prices = result.get("prices", [])
        if len(prices) > 1:
            lines.append(f"\n📈 *Histórico ({min(len(prices), 6)} meses):*")
            for p in prices[:6]:
                lines.append(f"  • {p.get('mes_referencia', '-')}: {p.get('valor', '-')}")
        await _return_to_parent(phone, db, session, "\n".join(lines))
    else:
        await _return_to_parent(phone, db, session, f"❌ {result.get('error', 'Erro ao consultar FIPE')}")
    return {"handled": True, "action": "query_fipe"}


@register_handler("query_vehicle_history")
async def handler_query_vehicle_history(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Vehicle history query - same as vehicles_history_query."""
    return await handler_vehicles_history(phone, db, session, menu_data, text)


# ---------- Buyers ----------

@register_handler("buyers_list")
async def handler_buyers_list(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List all buyers."""
    from models.buyers import Buyers
    stmt = select(Buyers).order_by(Buyers.name)
    res = await db.execute(stmt)
    buyers = res.scalars().all()

    if not buyers:
        await _return_to_parent(phone, db, session, "👥 Nenhum comprador registrado.")
        return {"handled": True, "action": "buyers_list_empty"}

    lines = [f"👥 *COMPRADORES* ({len(buyers)})\n"]
    for b in buyers:
        icon = "✅" if b.status == "active" else "❌"
        lines.append(f"{icon} {b.name} — {b.phone}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "buyers_list"}


@register_handler("buyers_add")
async def handler_buyers_add(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Add a buyer from menu input. Auto-assigns to 'Geral' category."""
    from services.admin_chat_commands import cmd_add_buyer, sanitize_phone, sanitize_text
    parts = text.strip().split()
    if len(parts) < 2:
        await send_text_message(phone, "⚠️ Informe nome e telefone.\nExemplo: João Silva 5511999999999", db)
        return {"handled": True, "action": "buyers_add_error"}

    buyer_phone = sanitize_phone(parts[-1])
    buyer_name = sanitize_text(" ".join(parts[:-1]))

    if not buyer_phone or not buyer_name:
        await send_text_message(phone, "⚠️ Nome ou telefone inválido.", db)
        return {"handled": True, "action": "buyers_add_error"}

    # cmd_add_buyer already auto-assigns to "Geral" category
    result = await cmd_add_buyer(phone, [buyer_name, buyer_phone], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("buyers_remove")
async def handler_buyers_remove(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Remove a buyer from menu input."""
    from services.admin_chat_commands import cmd_remove_buyer, sanitize_phone
    buyer_phone = sanitize_phone(text.strip())
    if not buyer_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "buyers_remove_error"}

    result = await cmd_remove_buyer(phone, [buyer_phone], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("buyers_link")
async def handler_buyers_link(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Link buyer to category from menu input."""
    from services.admin_chat_commands import cmd_link_buyer_category, sanitize_phone, sanitize_text
    parts = text.strip().split()
    if len(parts) < 2:
        await send_text_message(phone, "⚠️ Informe telefone e categoria.\nExemplo: 5511999999999 SUV Premium", db)
        return {"handled": True, "action": "buyers_link_error"}

    buyer_phone = sanitize_phone(parts[0])
    cat_name = sanitize_text(" ".join(parts[1:]))
    result = await cmd_link_buyer_category(phone, [buyer_phone, cat_name], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("buyers_unlink")
async def handler_buyers_unlink(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Unlink buyer from category from menu input."""
    from services.admin_chat_commands import cmd_unlink_buyer_category, sanitize_phone, sanitize_text
    parts = text.strip().split()
    if len(parts) < 2:
        await send_text_message(phone, "⚠️ Informe telefone e categoria.\nExemplo: 5511999999999 SUV Premium", db)
        return {"handled": True, "action": "buyers_unlink_error"}

    buyer_phone = sanitize_phone(parts[0])
    cat_name = sanitize_text(" ".join(parts[1:]))
    result = await cmd_unlink_buyer_category(phone, [buyer_phone, cat_name], db)
    await _return_to_parent(phone, db, session)
    return result


# ---------- Suppliers ----------

@register_handler("suppliers_list")
async def handler_suppliers_list(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List all suppliers."""
    from models.suppliers import Suppliers
    stmt = select(Suppliers).order_by(Suppliers.name)
    res = await db.execute(stmt)
    suppliers = res.scalars().all()

    if not suppliers:
        await _return_to_parent(phone, db, session, "🏭 Nenhum fornecedor registrado.")
        return {"handled": True, "action": "suppliers_list_empty"}

    lines = [f"🏭 *FORNECEDORES* ({len(suppliers)})\n"]
    for s in suppliers:
        icon = "✅" if s.status == "active" else "❌"
        company = f" ({s.company})" if s.company else ""
        lines.append(f"{icon} {s.name}{company} — {s.phone}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "suppliers_list"}


@register_handler("suppliers_add")
async def handler_suppliers_add(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Add a supplier from menu input."""
    from services.admin_chat_commands import cmd_add_supplier, sanitize_phone, sanitize_text
    parts = text.strip().split()
    if len(parts) < 2:
        await send_text_message(phone, "⚠️ Informe nome e telefone.\nExemplo: Auto Peças 5511999999999", db)
        return {"handled": True, "action": "suppliers_add_error"}

    supplier_phone = sanitize_phone(parts[-1])
    supplier_name = sanitize_text(" ".join(parts[:-1]))
    result = await cmd_add_supplier(phone, [supplier_name, supplier_phone], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("suppliers_remove")
async def handler_suppliers_remove(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Remove a supplier from menu input."""
    from services.admin_chat_commands import cmd_remove_supplier, sanitize_phone
    supplier_phone = sanitize_phone(text.strip())
    if not supplier_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "suppliers_remove_error"}

    result = await cmd_remove_supplier(phone, [supplier_phone], db)
    await _return_to_parent(phone, db, session)
    return result


# ---------- Negotiations ----------

@register_handler("negotiations_active")
async def handler_negotiations_active(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List active negotiations."""
    from models.offers import Offers
    stmt = select(Offers).where(
        Offers.status == "distributed",
        Offers.negotiation_status == "awaiting_update",
    ).order_by(Offers.id.desc()).limit(15)
    res = await db.execute(stmt)
    offers = res.scalars().all()

    if not offers:
        await _return_to_parent(phone, db, session, "📋 Nenhuma negociação em andamento.")
        return {"handled": True, "action": "negotiations_active_empty"}

    lines = [f"🔄 *NEGOCIAÇÕES EM ANDAMENTO* ({len(offers)})\n"]
    for o in offers:
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        lines.append(f"#{o.code} — {o.brand or ''} {o.model or ''} {price_str}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "negotiations_active"}


@register_handler("negotiations_finished")
async def handler_negotiations_finished(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List finished negotiations."""
    from models.offers import Offers
    stmt = select(Offers).where(
        Offers.negotiation_status.in_(["negotiated", "not_negotiated"]),
    ).order_by(Offers.id.desc()).limit(15)
    res = await db.execute(stmt)
    offers = res.scalars().all()

    if not offers:
        await _return_to_parent(phone, db, session, "📋 Nenhuma negociação finalizada.")
        return {"handled": True, "action": "negotiations_finished_empty"}

    lines = [f"✅ *NEGOCIAÇÕES FINALIZADAS* ({len(offers)})\n"]
    for o in offers:
        icon = "🟢" if o.negotiation_status == "negotiated" else "🔴"
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        lines.append(f"{icon} #{o.code} — {o.brand or ''} {o.model or ''} {price_str}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "negotiations_finished"}


@register_handler("negotiations_pending")
async def handler_negotiations_pending(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """List pending negotiations (distributed but no response)."""
    from models.offers import Offers
    stmt = select(Offers).where(
        Offers.status == "distributed",
        Offers.negotiation_status == "awaiting_update",
    ).order_by(Offers.id.desc()).limit(15)
    res = await db.execute(stmt)
    offers = res.scalars().all()

    if not offers:
        await _return_to_parent(phone, db, session, "📋 Nenhuma negociação pendente.")
        return {"handled": True, "action": "negotiations_pending_empty"}

    lines = [f"⏳ *NEGOCIAÇÕES PENDENTES* ({len(offers)})\n"]
    for o in offers:
        price_str = f"R$ {o.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if o.price else ""
        lines.append(f"#{o.code} — {o.brand or ''} {o.model or ''} {price_str}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "negotiations_pending"}


# ---------- Reports ----------

@register_handler("reports_monthly_offers")
async def handler_reports_monthly(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Monthly offers report."""
    from models.offers import Offers
    from sqlalchemy import func as sqlfunc
    from datetime import datetime as dt

    now = dt.now()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Count by status this month
    stmt = select(Offers.status, sqlfunc.count(Offers.id)).group_by(Offers.status)
    res = await db.execute(stmt)
    status_counts = dict(res.all())

    total = sum(status_counts.values())
    lines = [
        f"📊 *OFERTAS DO MÊS*",
        f"Período: {first_of_month.strftime('%d/%m/%Y')} - {now.strftime('%d/%m/%Y')}",
        "",
        f"Total: {total}",
    ]
    status_labels = {
        "draft": "Rascunho",
        "pending_approval": "Aguardando Aprovação",
        "approved": "Aprovadas",
        "confirmed": "Confirmadas",
        "distributed": "Distribuídas",
        "finalized": "Finalizadas",
        "rejected": "Rejeitadas",
    }
    for status, label in status_labels.items():
        count = status_counts.get(status, 0)
        if count > 0:
            lines.append(f"  • {label}: {count}")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "reports_monthly"}


@register_handler("reports_sales")
async def handler_reports_sales(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Sales report."""
    from models.offers import Offers
    from sqlalchemy import func as sqlfunc

    stmt = select(
        Offers.negotiation_substatus,
        sqlfunc.count(Offers.id),
    ).where(
        Offers.negotiation_status.in_(["negotiated", "not_negotiated"])
    ).group_by(Offers.negotiation_substatus)
    res = await db.execute(stmt)
    substatus_counts = dict(res.all())

    entered = substatus_counts.get("entered", 0)
    not_entered = substatus_counts.get("not_entered", 0)
    total = entered + not_entered

    lines = [
        "📊 *RELATÓRIO DE VENDAS*",
        "",
        f"Total negociados: {total}",
        f"✅ Entrou: {entered}",
        f"❌ Não Entrou: {not_entered}",
    ]
    if total > 0:
        rate = (entered / total) * 100
        lines.append(f"📈 Taxa de conversão: {rate:.1f}%")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "reports_sales"}


@register_handler("reports_active_buyers")
async def handler_reports_active_buyers(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Active buyers report."""
    from models.buyers import Buyers
    from models.offer_distributions import Offer_distributions
    from sqlalchemy import func as sqlfunc

    # Buyers with most distributions
    stmt = select(
        Buyers.name,
        sqlfunc.count(Offer_distributions.id).label("dist_count"),
    ).join(
        Offer_distributions, Offer_distributions.buyer_id == Buyers.id
    ).group_by(
        Buyers.id, Buyers.name
    ).order_by(
        sqlfunc.count(Offer_distributions.id).desc()
    ).limit(10)
    res = await db.execute(stmt)
    rows = res.all()

    lines = ["📊 *COMPRADORES ATIVOS*\n"]
    if not rows:
        lines.append("Nenhuma distribuição registrada.")
    else:
        for name, count in rows:
            lines.append(f"• {name}: {count} ofertas recebidas")

    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "reports_active_buyers"}


# ---------- Settings ----------

@register_handler("settings_show")
async def handler_settings_show(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Show current settings."""
    from services.admin_chat_commands import cmd_show_config
    result = await cmd_show_config(phone, db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_toggle_auto_reply")
async def handler_settings_toggle_auto_reply(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Toggle auto reply setting."""
    from services.admin_chat_commands import cmd_update_config
    from models.whatsapp_settings import Whatsapp_settings
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == "AI_AUTO_REPLY_ENABLED")
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()
    current = (row.setting_value if row else "true").lower() == "true"
    new_val = "false" if current else "true"
    result = await cmd_update_config(phone, ["AUTO_REPLY", new_val], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_toggle_auto_analysis")
async def handler_settings_toggle_auto_analysis(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Toggle auto analysis setting."""
    from services.admin_chat_commands import cmd_update_config
    from models.whatsapp_settings import Whatsapp_settings
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == "AI_AUTO_ANALYSIS_ENABLED")
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()
    current = (row.setting_value if row else "true").lower() == "true"
    new_val = "false" if current else "true"
    result = await cmd_update_config(phone, ["AUTO_ANALYSIS", new_val], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_toggle_escalate_price")
async def handler_settings_toggle_escalate_price(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Toggle escalate price setting."""
    from services.admin_chat_commands import cmd_update_config
    from models.whatsapp_settings import Whatsapp_settings
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == "AI_ESCALATE_PRICE")
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()
    current = (row.setting_value if row else "true").lower() == "true"
    new_val = "false" if current else "true"
    result = await cmd_update_config(phone, ["ESCALATE_PRICE", new_val], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_toggle_escalate_interest")
async def handler_settings_toggle_escalate_interest(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Toggle escalate interest setting."""
    from services.admin_chat_commands import cmd_update_config
    from models.whatsapp_settings import Whatsapp_settings
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == "AI_ESCALATE_INTEREST")
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()
    current = (row.setting_value if row else "true").lower() == "true"
    new_val = "false" if current else "true"
    result = await cmd_update_config(phone, ["ESCALATE_INTEREST", new_val], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_update_instructions")
async def handler_settings_update_instructions(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict, text: str) -> Dict:
    """Update custom AI instructions."""
    from services.admin_chat_commands import cmd_update_config, sanitize_text
    value = sanitize_text(text.strip(), max_length=500)
    if value.upper() == "LIMPAR":
        value = ""
    result = await cmd_update_config(phone, ["INSTRUCOES", value], db)
    await _return_to_parent(phone, db, session)
    return result


@register_handler("settings_negotiation_numbers")
async def handler_settings_negotiation_numbers(phone: str, db: AsyncSession, session: Whatsapp_admin_sessions, menu_data: Dict) -> Dict:
    """Show negotiation numbers info."""
    from models.negotiation_numbers import Negotiation_numbers
    stmt = select(Negotiation_numbers).order_by(Negotiation_numbers.id)
    res = await db.execute(stmt)
    numbers = res.scalars().all()

    if not numbers:
        await _return_to_parent(phone, db, session, "📞 Nenhum número de negociação cadastrado.\n💡 Cadastre pelo painel web.")
        return {"handled": True, "action": "settings_negotiation_numbers_empty"}

    lines = [f"📞 *NÚMEROS DE NEGOCIAÇÃO* ({len(numbers)})\n"]
    for n in numbers:
        status_icon = "✅" if n.status == "active" else "❌"
        lines.append(f"{status_icon} {n.name or n.number} — {n.number}")
    await _return_to_parent(phone, db, session, "\n".join(lines))
    return {"handled": True, "action": "settings_negotiation_numbers"}


# ==================== Dynamic Handler Registration ====================
# These handlers are generated dynamically for offer sending and buyer selection

def _register_dynamic_handlers():
    """Register handlers that need to be looked up dynamically at runtime.
    
    Since we can't know category/buyer IDs at import time, we use a 
    convention-based approach: handlers like vehicles_send_to_category_123
    are resolved dynamically.
    """
    pass  # Dynamic handlers are resolved in _execute_handler via name pattern


async def _resolve_dynamic_handler(
    handler_name: str,
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_data: Dict,
) -> Optional[Dict]:
    """Try to resolve a dynamic handler by name convention."""
    # vehicles_send_to_category_<id>
    if handler_name.startswith("vehicles_send_to_category_"):
        try:
            cat_id = int(handler_name.split("_")[-1])
            return await _send_offer_to_categories(phone, db, session, menu_data, [cat_id])
        except (ValueError, IndexError):
            return None

    # vehicles_send_to_all
    if handler_name == "vehicles_send_to_all":
        from models.categories import Categories
        stmt = select(Categories)
        res = await db.execute(stmt)
        categories = res.scalars().all()
        cat_ids = [c.id for c in categories]
        return await _send_offer_to_categories(phone, db, session, menu_data, cat_ids)

    # vehicles_sold_buyer_<id>
    if handler_name.startswith("vehicles_sold_buyer_"):
        try:
            buyer_id = int(handler_name.split("_")[-1])
            from models.buyers import Buyers
            stmt = select(Buyers).where(Buyers.id == buyer_id)
            res = await db.execute(stmt)
            buyer = res.scalar_one_or_none()
            if not buyer:
                await send_text_message(phone, "❌ Comprador não encontrado.", db)
                await _return_to_parent(phone, db, session)
                return {"handled": True, "action": "sold_buyer_not_found"}

            menu_data["buyer_id"] = buyer_id
            menu_data["buyer_name"] = buyer.name

            prefix = f"Comprador selecionado:\n*{buyer.name}*\n\nAgora informe:"
            await _show_menu_and_update(phone, db, session, "vehicles_sold_entered", menu_data, prefix)
            return {"handled": True, "action": "sold_select_buyer"}
        except (ValueError, IndexError):
            return None

    return None


# Override _execute_handler to support dynamic resolution
_original_execute_handler = _execute_handler


async def _execute_handler_with_dynamic(
    handler_name: str,
    phone: str,
    db: AsyncSession,
    session: Whatsapp_admin_sessions,
    menu_data: Dict,
) -> Dict[str, Any]:
    """Execute handler with dynamic handler support."""
    # Try static registry first
    handler = _HANDLER_REGISTRY.get(handler_name)
    if handler:
        try:
            result = await handler(phone, db, session, menu_data)
            return result
        except Exception as e:
            logger.error(f"Menu handler error ({handler_name}): {e}", exc_info=True)
            await send_text_message(phone, "❌ Erro ao processar. Digite *menu*.", db)
            await _reset_to_main(db, session)
            return {"handled": True, "action": "handler_error", "error": str(e)}

    # Try dynamic resolution
    result = await _resolve_dynamic_handler(handler_name, phone, db, session, menu_data)
    if result is not None:
        return result

    logger.error(f"Handler not found (static or dynamic): {handler_name}")
    await send_text_message(phone, "❌ Função não disponível. Digite *menu*.", db)
    await _reset_to_main(db, session)
    return {"handled": True, "action": "handler_not_found"}


# Replace the module-level _execute_handler
_execute_handler = _execute_handler_with_dynamic


# ==================== Initialize Menu Session ====================

async def init_menu_session(phone: str, db: AsyncSession) -> None:
    """Initialize or reset a menu session and send the main menu."""
    session, _ = await _get_session(db, phone)
    await _update_session(db, session, menu_path="main", menu_data={})
    await send_text_message(phone, format_menu_message("main"), db)