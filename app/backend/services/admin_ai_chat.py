"""
Admin AI chat service for WhatsApp.

When the admin sends a message that is not a recognized command,
this service engages in a natural conversation, providing help,
answering questions, and assisting with system management.

The AI has access to current system data (buyers, suppliers, offers, categories)
and can guide the admin through any operation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.buyers import Buyers
from models.suppliers import Suppliers
from models.categories import Categories
from models.buyer_categories import Buyer_categories
from models.offers import Offers
from models.offer_distributions import Offer_distributions
from models.negotiation_history import Negotiation_history
from models.whatsapp_settings import Whatsapp_settings
from models.whatsapp_conversations import Whatsapp_conversations
from services.aihub import AIHubService
from schemas.aihub import GenTxtRequest, ChatMessage
from services.whatsapp import send_text_message

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_AI_MODEL = "gpt-5.4"

ADMIN_AI_SYSTEM_PROMPT = """Você é a *AutoHub AI*, a assistente inteligente da plataforma de intermediação de veículos AutoHub.

Você conversa diretamente com o administrador pelo WhatsApp. Seu papel é:

1. **Ajudar com o sistema** — Explicar como usar comandos, sugerir ações, responder dúvidas sobre o funcionamento
2. **Fornecer insights** — Analisar dados de ofertas, compradores, fornecedores e negociações
3. **Sugerir comandos** — Quando o admin quiser fazer algo, sugira o comando exato
4. **Conversar naturalmente** — Seja amigável, profissional e proativo

REGRAS:
- Responda sempre em português do Brasil
- Seja conciso (respostas curtas, ideais para WhatsApp)
- Use emojis com moderação para tornar a conversa mais agradável
- Quando sugerir um comando, use o formato `COMANDO` com crase
- Se o admin pedir para fazer algo que requer um comando, explique o comando E ofereça para ajudar
- Você tem acesso aos dados atuais do sistema (fornecidos no contexto)
- Nunca invente dados — use apenas os dados fornecidos no contexto
- Se não souber algo, seja honesto e sugira como descobrir

COMANDOS DISPONÍVEIS (para referência):
- `AJUDA` — Lista todos os comandos
- `COMPRADORES` — Lista compradores
- `ADICIONAR COMPRADOR <nome> <telefone>` — Adiciona comprador
- `REMOVER COMPRADOR <telefone>` — Remove comprador
- `FORNECEDORES` — Lista fornecedores
- `ADICIONAR FORNECEDOR <nome> <telefone>` — Adiciona fornecedor
- `REMOVER FORNECEDOR <telefone>` — Remove fornecedor
- `CATEGORIAS` — Lista categorias
- `CRIAR CATEGORIA <nome>` — Cria categoria
- `REMOVER CATEGORIA <nome>` — Remove categoria
- `VINCULAR <telefone> <categoria>` — Adiciona comprador à categoria
- `DESVINCULAR <telefone> <categoria>` — Remove comprador da categoria
- `CONFIG` — Mostra configurações
- `CONFIG <chave> <valor>` — Altera configuração
- `CRIAR ANUNCIO` — Inicia criação de anúncio
- `CANCELAR` — Cancela fluxo atual
"""


async def _get_model_setting(db: AsyncSession, key: str, default: str) -> str:
    """Read a model setting from the database, falling back to the default."""
    try:
        stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == key)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.setting_value:
            return row.setting_value
    except Exception as e:
        logger.warning(f"Failed to read model setting {key} from DB: {e}")
    return default


# Simple in-memory cache for system context (refreshed every 60s)
_context_cache: Dict[str, Any] = {"data": "", "expires_at": 0.0}
_CONTEXT_CACHE_TTL = 60  # seconds


async def _gather_system_context(db: AsyncSession) -> str:
    """Gather current system data to provide context for the AI.
    
    Uses batched queries and a 60-second cache to minimize DB round-trips.
    """
    import time as _time
    now = _time.time()
    if _context_cache["data"] and now < _context_cache["expires_at"]:
        return _context_cache["data"]

    lines = []

    # Query 1: Buyers grouped by status (1 query instead of 2)
    buyer_stmt = select(Buyers.status, func.count(Buyers.id)).group_by(Buyers.status)
    buyer_res = await db.execute(buyer_stmt)
    buyer_counts = dict(buyer_res.all())
    buyer_total = sum(buyer_counts.values())
    buyer_active = buyer_counts.get("active", 0)
    lines.append(f"Compradores: {buyer_active} ativos de {buyer_total} total")

    # Query 2: Suppliers grouped by status (1 query instead of 2)
    supplier_stmt = select(Suppliers.status, func.count(Suppliers.id)).group_by(Suppliers.status)
    supplier_res = await db.execute(supplier_stmt)
    supplier_counts = dict(supplier_res.all())
    supplier_total = sum(supplier_counts.values())
    supplier_active = supplier_counts.get("active", 0)
    lines.append(f"Fornecedores: {supplier_active} ativos de {supplier_total} total")

    # Query 3: Categories count
    cat_count = await db.execute(select(func.count(Categories.id)))
    lines.append(f"Categorias: {cat_count.scalar_one_or_none() or 0}")

    # Query 4: Offers grouped by status (1 query instead of 6)
    offer_stmt = select(Offers.status, func.count(Offers.id)).group_by(Offers.status)
    offer_res = await db.execute(offer_stmt)
    offer_counts = dict(offer_res.all())
    status_labels = {
        "draft": "rascunho",
        "pending_approval": "aguardando aprovação",
        "approved": "aprovadas",
        "confirmed": "confirmadas",
        "distributed": "distribuídas",
        "rejected": "rejeitadas",
    }
    for status, label in status_labels.items():
        val = offer_counts.get(status, 0)
        if val > 0:
            lines.append(f"Ofertas {label}: {val}")

    # Query 5: Conversations (1 query with conditional count)
    conv_total = await db.execute(select(func.count(Whatsapp_conversations.id)))
    conv_analyzed = await db.execute(
        select(func.count(Whatsapp_conversations.id)).where(
            Whatsapp_conversations.ai_analysis.isnot(None),
            Whatsapp_conversations.ai_analysis != "",
        )
    )
    lines.append(f"Conversas WhatsApp: {conv_total.scalar_one_or_none() or 0} ({conv_analyzed.scalar_one_or_none() or 0} analisadas)")

    # Query 6: All AI settings in one query (1 query instead of 5)
    ai_keys = [
        "AI_AUTO_REPLY_ENABLED",
        "AI_AUTO_ANALYSIS_ENABLED",
        "AI_ESCALATE_PRICE",
        "AI_ESCALATE_INTEREST",
        "AI_CUSTOM_INSTRUCTIONS",
    ]
    ai_stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key.in_(ai_keys))
    ai_res = await db.execute(ai_stmt)
    ai_rows = ai_res.scalars().all()
    ai_values = {row.setting_key: row.setting_value for row in ai_rows}

    auto_reply = (ai_values.get("AI_AUTO_REPLY_ENABLED") or "true").lower() == "true"
    auto_analysis = (ai_values.get("AI_AUTO_ANALYSIS_ENABLED") or "true").lower() == "true"
    lines.append(f"IA Resposta automática: {'ativada' if auto_reply else 'desativada'}")
    lines.append(f"IA Análise automática: {'ativada' if auto_analysis else 'desativada'}")

    custom_instr = ai_values.get("AI_CUSTOM_INSTRUCTIONS", "")
    if custom_instr:
        lines.append(f"Instruções personalizadas IA: {custom_instr[:200]}")

    result = "\n".join(lines)
    _context_cache["data"] = result
    _context_cache["expires_at"] = now + _CONTEXT_CACHE_TTL
    return result


async def handle_admin_ai_chat(
    phone: str,
    content: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Handle a conversational message from the admin via WhatsApp.
    
    This is called when the admin's message is NOT a recognized command.
    The AI responds naturally with full system context.
    
    Returns:
        Dict with "handled": True and the AI response details.
    """
    if not content or not content.strip():
        return {"handled": False}

    try:
        # Gather current system context
        system_context = await _gather_system_context(db)

        # Get model
        model = await _get_model_setting(db, "AI_ADMIN_CHAT_MODEL", DEFAULT_ADMIN_AI_MODEL)

        # Build the full system prompt with live context
        full_system = (
            ADMIN_AI_SYSTEM_PROMPT
            + "\n\n--- DADOS ATUAIS DO SISTEMA ---\n"
            + system_context
            + "\n--- FIM DOS DADOS ---\n"
        )

        service = AIHubService()

        request = GenTxtRequest(
            messages=[
                ChatMessage(role="system", content=full_system),
                ChatMessage(role="user", content=content.strip()),
            ],
            model=model,
            temperature=0.6,
            max_tokens=500,
        )

        response = await service.gentxt(request)
        ai_reply = response.content.strip()

        if not ai_reply:
            ai_reply = "Desculpe, não consegui processar sua mensagem. Pode repetir?"

        # Send the AI response back to the admin
        await send_text_message(phone, ai_reply, db)

        return {"handled": True, "action": "admin_ai_chat", "reply": ai_reply}

    except Exception as e:
        logger.error(f"Admin AI chat error: {e}")
        # Fallback: still respond, just without AI
        await send_text_message(
            phone,
            "🤖 Não consegui processar sua mensagem no momento. "
            "Se precisar de ajuda, envie `AJUDA` para ver os comandos disponíveis.",
            db,
        )
        return {"handled": True, "action": "admin_ai_chat_error", "error": str(e)}