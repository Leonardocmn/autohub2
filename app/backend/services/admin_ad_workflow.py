"""
Admin ad creation workflow via WhatsApp chat.

Flow:
1. Admin sends "CRIAR ANUNCIO" → system replies asking for photo + description
2. Admin sends photo + description → system creates offer and distributes to ALL registered buyers
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.whatsapp_admin_sessions import Whatsapp_admin_sessions
from models.offers import Offers
from models.buyers import Buyers
from models.offer_distributions import Offer_distributions
from models.negotiation_numbers import Negotiation_numbers
from services.whatsapp import send_text_message, send_media_message, is_configured
from services.offer_workflow import format_offer_for_buyer

logger = logging.getLogger(__name__)


async def get_admin_session(phone: str, db: AsyncSession) -> Optional[Whatsapp_admin_sessions]:
    """Get or create an admin session for the given phone number."""
    clean = "".join(c for c in phone if c.isdigit())
    stmt = select(Whatsapp_admin_sessions).where(
        Whatsapp_admin_sessions.admin_phone.contains(clean)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    
    if not session:
        session = Whatsapp_admin_sessions(
            admin_phone=clean,
            state="idle",
            temp_data="{}",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
    
    return session


async def handle_admin_ad_command(
    phone: str,
    content: str,
    message_type: str,
    media_url: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Handle admin ad creation commands via WhatsApp.
    
    Commands:
    - CRIAR ANUNCIO: Start ad creation flow
    - CANCELAR: Cancel current flow
    
    When in awaiting_ad_content state:
    - Photo + caption: Create offer and distribute
    - Text only: Ask for photo
    - Photo only: Ask for description
    """
    session = await get_admin_session(phone, db)
    content_upper = content.strip().upper() if content else ""
    
    # Handle CANCELAR at any point
    if content_upper == "CANCELAR":
        session.state = "idle"
        session.temp_data = "{}"
        await db.commit()
        await send_text_message(
            phone,
            "❌ Criação de anúncio cancelada.",
            db,
        )
        return {"handled": True, "action": "cancelled"}
    
    # Handle CRIAR ANUNCIO command
    if content_upper in ("CRIAR ANUNCIO", "CRIAR ANÚNCIO", "CRIAR_ANUNCIO", "NOVO ANUNCIO", "NOVO ANÚNCIO"):
        session.state = "awaiting_ad_content"
        session.temp_data = json.dumps({"started_at": str(int(time.time()))})
        await db.commit()
        
        await send_text_message(
            phone,
            "📸 *Criação de Anúncio*\n\n"
            "Envie a *foto* e a *descrição* do veículo.\n\n"
            "Você pode enviar foto + legenda juntos ou separados.\n\n"
            "Exemplo de descrição:\n"
            "Toyota Corolla XEi 2023\n"
            "48.000km | Flex\n"
            "R$ 115.000\n\n"
            "_Envie CANCELAR para interromper_",
            db,
        )
        return {"handled": True, "action": "awaiting_content"}
    
    # Handle content submission when in awaiting state
    if session.state == "awaiting_ad_content":
        temp_data = json.loads(session.temp_data) if session.temp_data else {}
        
        # Collect what we have
        has_image = bool(media_url) or message_type == "image"
        has_description = bool(content and content.strip())
        
        # Store incoming data in temp
        if has_image:
            images = temp_data.get("images", [])
            images.append(media_url)
            temp_data["images"] = images
        
        if has_description:
            existing_desc = temp_data.get("description", "")
            if existing_desc:
                temp_data["description"] = existing_desc + "\n" + content.strip()
            else:
                temp_data["description"] = content.strip()
        
        # Check if we have both image and description
        has_stored_image = bool(temp_data.get("images"))
        has_stored_desc = bool(temp_data.get("description"))
        
        if has_stored_image and has_stored_desc:
            # We have everything - create the offer and distribute
            result = await _create_and_distribute_ad(phone, temp_data, db)
            
            # Reset session
            session.state = "idle"
            session.temp_data = "{}"
            await db.commit()
            
            return {"handled": True, "action": "created_and_distributed", "result": result}
        
        elif has_stored_image and not has_stored_desc:
            # Got image but no description
            temp_data["awaiting"] = "description"
            session.temp_data = json.dumps(temp_data)
            await db.commit()
            
            await send_text_message(
                phone,
                "✅ Foto recebida!\n\nAgora envie a *descrição* do veículo (modelo, ano, km, preço, etc.):",
                db,
            )
            return {"handled": True, "action": "awaiting_description"}
        
        elif has_stored_desc and not has_stored_image:
            # Got description but no image
            temp_data["awaiting"] = "image"
            session.temp_data = json.dumps(temp_data)
            await db.commit()
            
            await send_text_message(
                phone,
                "✅ Descrição recebida!\n\nAgora envie a *foto* do veículo:",
                db,
            )
            return {"handled": True, "action": "awaiting_image"}
        
        else:
            # Neither - shouldn't happen but handle gracefully
            await send_text_message(
                phone,
                "⚠️ Não recebi conteúdo. Envie a foto e/ou descrição do veículo, ou CANCELAR para interromper.",
                db,
            )
            return {"handled": True, "action": "awaiting_content"}
    
    # Not in an ad creation flow
    return {"handled": False}


async def _create_and_distribute_ad(
    admin_phone: str,
    temp_data: Dict[str, Any],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Create an offer from admin-submitted data and distribute to all registered buyers."""
    description = temp_data.get("description", "")
    images = temp_data.get("images", [])
    
    # Create the offer
    offer = Offers(
        title=description.split("\n")[0][:200] if description else "Anúncio via WhatsApp",
        description=description,
        status="confirmed",  # Skip approval since admin created it directly
        processed_images=json.dumps(images) if images else None,
        selected_images=json.dumps(images) if images else None,
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    
    # Generate offer code based on ID
    if not offer.code:
        offer.code = str(100000 + offer.id)
        await db.commit()
    
    logger.info(f"Created offer #{offer.code} from admin WhatsApp ad creation")
    
    # Get ALL registered buyers
    buyer_stmt = select(Buyers).where(Buyers.status == "active")
    buyer_res = await db.execute(buyer_stmt)
    buyers = buyer_res.scalars().all()
    
    if not buyers:
        await send_text_message(
            admin_phone,
            f"✅ Anúncio #{offer.code} criado, mas não há compradores registrados para distribuir.",
            db,
        )
        return {"offer_id": offer.id, "offer_code": offer.code, "distributed": False, "reason": "no_buyers"}
    
    # Get negotiation number
    neg_stmt = select(Negotiation_numbers).where(Negotiation_numbers.status == "active").limit(1)
    neg_res = await db.execute(neg_stmt)
    neg_number = neg_res.scalar_one_or_none()
    negotiation_phone = neg_number.phone if neg_number else ""
    
    # Format message for buyers
    buyer_msg = format_offer_for_buyer(offer, negotiation_phone)
    
    # Send to each buyer
    sent_count = 0
    errors = []
    
    for buyer in buyers:
        if not buyer.phone:
            continue
        
        try:
            result = None
            if images:
                # Send first image WITH caption (vehicle description)
                first_img = images[0]
                result = await send_media_message(buyer.phone, buyer_msg, first_img, "image", db)
                
                # Fallback to text-only if first image send fails
                if not result.get("success"):
                    logger.warning(f"Media send failed for buyer {buyer.id}, falling back to text: {result.get('error')}")
                    result = await send_text_message(buyer.phone, buyer_msg, db)
                else:
                    # Send additional images WITHOUT caption
                    for extra_img in images[1:]:
                        extra_result = await send_media_message(buyer.phone, "", extra_img, "image", db)
                        if not extra_result.get("success"):
                            logger.warning(f"Extra image send failed for buyer {buyer.id}: {extra_result.get('error')}")
            else:
                result = await send_text_message(buyer.phone, buyer_msg, db)
            
            if result.get("success"):
                sent_count += 1
                # Record distribution
                dist = Offer_distributions(
                    offer_id=offer.id,
                    buyer_id=buyer.id,
                    sent_at=str(int(time.time())),
                )
                db.add(dist)
            else:
                errors.append(f"Buyer {buyer.id}: {result.get('error', 'unknown')}")
        except Exception as e:
            errors.append(f"Buyer {buyer.id}: {str(e)}")
    
    # Update offer status
    offer.status = "distributed"
    offer.distributed_at = str(int(time.time()))
    await db.commit()
    
    # Notify admin of result
    result_msg = (
        f"✅ *Anúncio #{offer.code} criado e distribuído!*\n\n"
        f"📤 Enviado para {sent_count} de {len(buyers)} compradores"
    )
    if errors:
        result_msg += f"\n⚠️ {len(errors)} falha(s) no envio"
    
    await send_text_message(admin_phone, result_msg, db)
    
    return {
        "offer_id": offer.id,
        "offer_code": offer.code,
        "status": "distributed",
        "sent_count": sent_count,
        "total_buyers": len(buyers),
        "errors": errors,
    }