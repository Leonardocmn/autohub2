"""
Offer approval workflow service.
Handles the multi-step approval process:
  draft → pending_approval → approved → confirmed → distributed
Admin can approve/reject/confirm/go back via WhatsApp commands or web panel.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.offers import Offers
from models.buyers import Buyers
from models.buyer_categories import Buyer_categories
from models.categories import Categories
from models.offer_distributions import Offer_distributions
from models.negotiation_numbers import Negotiation_numbers
from models.whatsapp_admin_phones import Whatsapp_admin_phones
from services.whatsapp import send_text_message, send_media_message, is_configured
from services.whatsapp_conversation import notify_admin
from services.formatting import format_brl_price

logger = logging.getLogger(__name__)

# Offer status flow
OFFER_STATUS_FLOW = {
    "draft": "pending_approval",
    "pending_approval": "approved",
    "approved": "confirmed",
    "confirmed": "distributed",
}

VALID_STATUSES = ["draft", "pending_approval", "approved", "confirmed", "distributed", "rejected"]


def format_offer_for_admin(offer: Offers) -> str:
    """Format an offer in the company template for admin review via WhatsApp."""
    brand = offer.brand or ""
    model = offer.model or ""
    version = offer.version or ""
    vehicle_line = f"{brand} {model} {version}".strip() or offer.title or "Veículo"

    lines = [
        f"📋 *OFERTA #{offer.code}* (ID: {offer.id})",
        "",
        f"🚗 {vehicle_line}",
    ]
    if offer.year:
        lines.append(f"📅 Ano: {offer.year}")
    if offer.mileage:
        lines.append(f"📍 KM: {offer.mileage}")
    if offer.transmission:
        lines.append(f"⚙️ Câmbio: {offer.transmission}")
    if offer.fuel:
        lines.append(f"⛽ Combustível: {offer.fuel}")
    if offer.color:
        lines.append(f"🎨 Cor: {offer.color}")
    if offer.fipe:
        lines.append(f"📊 FIPE: {offer.fipe}")
    if offer.supplier_price:
        lines.append(f"🏷️ Preço Fornecedor: {format_brl_price(offer.supplier_price)}")
    if offer.price:
        lines.append(f"💰 Preço Venda: {format_brl_price(offer.price)}")
    if offer.plate:
        lines.append(f"🔖 Placa: {offer.plate}")
    lines.append(f"📋 Manual: {'Sim' if offer.has_manual else 'Não informado'}")
    lines.append(f"🔑 Chave Reserva: {'Sim' if offer.has_spare_key else 'Não informado'}")
    if offer.is_auction:
        lines.append("⚠️ Veículo de leilão")
    if offer.suggested_category:
        lines.append(f"📁 Categoria sugerida: {offer.suggested_category}")
    if offer.description:
        lines.append(f"\n📝 Observações: {offer.description}")

    lines.extend([
        "",
        f"Status: *{offer.status}*",
        "",
    ])

    return "\n".join(lines)


def format_offer_for_buyer(offer: Offers, negotiation_phone: str = "") -> str:
    """Format an offer for buyer distribution using the standard AutoHub template (§7.1)."""
    brand = offer.brand or ""
    model = offer.model or ""
    version = offer.version or ""
    vehicle_line = f"{brand} {model} {version}".strip() or offer.title or "Veículo"

    lines = [
        f"[#{offer.code}]",
        "",
        f"🚗 {vehicle_line}",
    ]
    if offer.year:
        lines.append(f"📅 Ano: {offer.year}")
    if offer.mileage:
        lines.append(f"📍 KM: {offer.mileage}")
    if offer.transmission:
        lines.append(f"⚙️ Câmbio: {offer.transmission}")
    if offer.fuel:
        lines.append(f"⛽ Combustível: {offer.fuel}")
    if offer.color:
        lines.append(f"🎨 Cor: {offer.color}")
    if offer.price:
        lines.append(f"💰 Valor: {format_brl_price(offer.price)}")

    if offer.description:
        lines.append("")
        lines.append("Observações:")
        desc_lines = [l.strip() for l in offer.description.split("\n") if l.strip()]
        for dl in desc_lines[:5]:
            lines.append(f"- {dl}")

    lines.append("")
    if negotiation_phone:
        lines.append("💬 Para negociar, responda com o código da oferta ou NEGOCIAR.")
    else:
        lines.append("💬 Interessado? Entre em contato!")

    return "\n".join(lines)


async def send_offer_to_admin_for_approval(
    offer_id: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Send offer details to admin via WhatsApp for approval."""
    stmt = select(Offers).where(Offers.id == offer_id)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    if not offer:
        return {"error": "Oferta não encontrada"}

    if offer.status not in ("draft", "pending_approval"):
        return {"error": f"Oferta não está em rascunho. Status atual: {offer.status}"}

    offer.status = "pending_approval"
    await db.commit()

    admin_msg = format_offer_for_admin(offer)
    admin_msg += "\n\n✅ Responda *APROVAR* para aprovar\n❌ Responda *REJEITAR* para recusar"

    await notify_admin(admin_msg, db)

    if offer.processed_images:
        try:
            images = json.loads(offer.processed_images) if isinstance(offer.processed_images, str) else offer.processed_images
            if images and len(images) > 0:
                first_img = images[0] if isinstance(images[0], str) else images[0].get("processed_url", images[0].get("url", ""))
                if first_img:
                    for admin_phone in await _get_admin_phones(db):
                        await send_media_message(admin_phone, f"📸 Foto da oferta #{offer.code}", first_img, "image", db)
        except Exception as e:
            logger.error(f"Failed to send offer image to admin: {e}")

    return {"success": True, "offer_id": offer.id, "status": "pending_approval"}


async def handle_admin_command(
    phone: str,
    command: str,
    offer_code: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Handle admin WhatsApp commands for offer approval."""
    admin_phones = await _get_admin_phones(db)
    clean_phone = "".join(c for c in phone if c.isdigit())
    is_admin = any(
        len(p) >= 10 and len(clean_phone) >= 10 and (clean_phone.endswith(p[-10:]) or p.endswith(clean_phone[-10:]))
        for p in admin_phones
    )

    if not is_admin:
        return {"error": "Número não autorizado"}

    stmt = select(Offers).where(Offers.code == offer_code)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    if not offer:
        return {"error": f"Oferta #{offer_code} não encontrada"}

    command = command.strip().upper()

    if command == "APROVAR":
        if offer.status not in ("pending_approval", "approved"):
            return {"error": f"Oferta não pode ser aprovada. Status: {offer.status}"}
        offer.status = "approved"
        await db.commit()

        confirm_msg = format_offer_for_admin(offer)
        confirm_msg += "\n\n✅ *OFERTA APROVADA*\n\nEnvie *CONFIRMAR* para enviar aos compradores\nEnvie *VOLTAR* para retornar à edição"
        await notify_admin(confirm_msg, db)

        return {"success": True, "offer_id": offer.id, "status": "approved"}

    elif command == "REJEITAR":
        offer.status = "rejected"
        await db.commit()

        reject_msg = f"❌ Oferta #{offer.code} foi *REJEITADA*."
        await notify_admin(reject_msg, db)

        return {"success": True, "offer_id": offer.id, "status": "rejected"}

    elif command == "CONFIRMAR":
        if offer.status != "approved":
            return {"error": f"Oferta precisa estar aprovada para confirmar. Status: {offer.status}"}
        offer.status = "confirmed"
        await db.commit()

        confirm_msg = f"✅ Oferta #{offer.code} *CONFIRMADA*! Pronta para distribuição."
        await notify_admin(confirm_msg, db)

        return {"success": True, "offer_id": offer.id, "status": "confirmed"}

    elif command == "VOLTAR":
        if offer.status == "approved":
            offer.status = "pending_approval"
        elif offer.status == "confirmed":
            offer.status = "approved"
        elif offer.status == "pending_approval":
            offer.status = "draft"
        else:
            return {"error": f"Não é possível voltar. Status: {offer.status}"}
        await db.commit()

        back_msg = f"⬅️ Oferta #{offer.code} retornou para status: *{offer.status}*"
        await notify_admin(back_msg, db)

        return {"success": True, "offer_id": offer.id, "status": offer.status}

    else:
        return {"error": f"Comando desconhecido: {command}"}


async def distribute_offer_to_buyers(
    offer_id: int,
    category_ids: List[int],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Distribute a confirmed offer to buyers in the selected categories."""
    stmt = select(Offers).where(Offers.id == offer_id)
    res = await db.execute(stmt)
    offer = res.scalar_one_or_none()

    if not offer:
        return {"error": "Oferta não encontrada"}

    if offer.status != "confirmed":
        return {"error": f"Oferta precisa estar confirmada para distribuir. Status: {offer.status}"}

    neg_stmt = select(Negotiation_numbers).where(Negotiation_numbers.status == "active").limit(1)
    neg_res = await db.execute(neg_stmt)
    neg_number = neg_res.scalar_one_or_none()
    negotiation_phone = neg_number.phone if neg_number else ""

    buyer_ids = set()
    for cat_id in category_ids:
        bc_stmt = select(Buyer_categories).where(Buyer_categories.category_id == cat_id)
        bc_res = await db.execute(bc_stmt)
        for bc in bc_res.scalars().all():
            buyer_ids.add(bc.buyer_id)

    if not buyer_ids:
        return {"error": "Nenhum comprador encontrado nas categorias selecionadas"}

    buyer_stmt = select(Buyers).where(Buyers.id.in_(buyer_ids))
    buyer_res = await db.execute(buyer_stmt)
    buyers = buyer_res.scalars().all()

    buyer_msg = format_offer_for_buyer(offer, negotiation_phone)

    images: List[str] = []
    if offer.selected_images:
        try:
            selected = json.loads(offer.selected_images) if isinstance(offer.selected_images, str) else offer.selected_images
            for item in selected:
                url = item if isinstance(item, str) else item.get("processed_url", item.get("url", ""))
                if url:
                    images.append(url)
        except Exception:
            pass
    elif offer.processed_images:
        try:
            processed = json.loads(offer.processed_images) if isinstance(offer.processed_images, str) else offer.processed_images
            for item in processed:
                url = item if isinstance(item, str) else item.get("processed_url", item.get("url", ""))
                if url:
                    images.append(url)
        except Exception:
            pass

    sent_count = 0
    errors = []

    for buyer in buyers:
        if not buyer.phone:
            continue

        try:
            result = None
            if images:
                first_img = images[0]
                result = await send_media_message(buyer.phone, buyer_msg, first_img, "image", db)

                if not result.get("success"):
                    logger.warning(f"Media send failed for buyer {buyer.id}, falling back to text")
                    result = await send_text_message(buyer.phone, buyer_msg, db)
                else:
                    for extra_img in images[1:]:
                        extra_result = await send_media_message(buyer.phone, "", extra_img, "image", db)
                        if not extra_result.get("success"):
                            logger.warning(f"Extra image send failed for buyer {buyer.id}")
            else:
                result = await send_text_message(buyer.phone, buyer_msg, db)

            if result.get("success"):
                sent_count += 1
                dist = Offer_distributions(
                    offer_id=offer.id,
                    buyer_id=buyer.id,
                    category_id=category_ids[0] if category_ids else None,
                    sent_at=str(int(time.time())),
                )
                db.add(dist)
            else:
                errors.append(f"Buyer {buyer.id}: {result.get('error', 'unknown')}")
        except Exception as e:
            errors.append(f"Buyer {buyer.id}: {str(e)}")

    offer.status = "distributed"
    offer.target_categories = json.dumps(category_ids)
    offer.distributed_at = str(int(time.time()))
    await db.commit()

    return {
        "success": True,
        "offer_id": offer.id,
        "status": "distributed",
        "sent_count": sent_count,
        "total_buyers": len(buyers),
        "errors": errors,
    }


async def handle_buyer_negotiate(
    phone: str,
    content: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Handle when a buyer sends NEGOCIAR in response to an offer."""
    content_upper = content.strip().upper()

    if "NEGOCIAR" not in content_upper:
        return {"handled": False}

    clean_phone = "".join(c for c in phone if c.isdigit())

    buyer_stmt = select(Buyers).where(Buyers.phone.contains(clean_phone))
    buyer_res = await db.execute(buyer_stmt)
    buyer = buyer_res.scalar_one_or_none()

    if not buyer:
        return {"handled": False, "reason": "buyer_not_found"}

    dist_stmt = (
        select(Offer_distributions)
        .where(Offer_distributions.buyer_id == buyer.id)
        .order_by(Offer_distributions.id.desc())
        .limit(5)
    )
    dist_res = await db.execute(dist_stmt)
    distributions = dist_res.scalars().all()

    if not distributions:
        return {"handled": False, "reason": "no_distributions"}

    for dist in distributions:
        offer_stmt = select(Offers).where(Offers.id == dist.offer_id, Offers.status == "distributed")
        offer_res = await db.execute(offer_stmt)
        offer = offer_res.scalar_one_or_none()
        if offer:
            neg_stmt = select(Negotiation_numbers).where(Negotiation_numbers.status == "active").limit(1)
            neg_res = await db.execute(neg_stmt)
            neg_number = neg_res.scalar_one_or_none()

            if neg_number:
                reply = (
                    f"🤝 *Negociação - AutoHub*\n\n"
                    f"Oferta: *{offer.title}*\n"
                    f"Código: #{offer.code}\n\n"
                    f"📞 Entre em contato pelo número: *{neg_number.phone}*\n"
                    f"Responsável: {neg_number.responsible_name}\n\n"
                    f"_AutoHub - Intermediação de Veículos_"
                )
            else:
                reply = (
                    f"🤝 Obrigado pelo interesse na oferta *{offer.title}*!\n\n"
                    f"Um de nossos consultores entrará em contato em breve."
                )

            if await is_configured(db):
                await send_text_message(phone, reply, db)

            return {"handled": True, "offer_id": offer.id, "buyer_id": buyer.id}

    return {"handled": False, "reason": "no_active_offer"}


async def check_negotiation_expirations(db: AsyncSession) -> List[Dict[str, Any]]:
    """Check for offers past their negotiation deadline and mark as not_negotiated."""
    from datetime import datetime, timezone, timedelta

    stmt = select(Offers).where(
        Offers.status == "distributed",
        Offers.negotiation_status == "awaiting_update",
    )
    res = await db.execute(stmt)
    offers = res.scalars().all()

    expired = []
    now = datetime.now(timezone.utc)

    for offer in offers:
        if not offer.distributed_at:
            continue
        try:
            dist_ts = int(offer.distributed_at)
            dist_time = datetime.fromtimestamp(dist_ts, tz=timezone.utc)
            deadline_hours = offer.negotiation_deadline_hours or 48
            if now > dist_time + timedelta(hours=deadline_hours):
                offer.negotiation_status = "not_negotiated"
                expired.append({"offer_id": offer.id, "code": offer.code})
        except (ValueError, OSError):
            continue

    if expired:
        await db.commit()

    return expired


async def _get_admin_phones(db: AsyncSession) -> List[str]:
    """Get all active admin phone numbers."""
    stmt = select(Whatsapp_admin_phones).where(Whatsapp_admin_phones.active == True)
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [row.phone.strip() for row in rows if row.phone]