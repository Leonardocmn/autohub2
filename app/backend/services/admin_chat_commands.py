"""
Admin chat commands service for WhatsApp.

Allows the admin to manage the entire system directly from WhatsApp chat:
- Contact management (add/remove buyers and suppliers)
- Category/group management (create, remove, assign)
- System behavior settings (AI, auto-reply, etc.)
- Ad creation (delegated to admin_ad_workflow)

Commands:
  AJUDA / COMANDOS          - Show all available commands
  COMPRADORES               - List all buyers
  ADICIONAR COMPRADOR <nome> <telefone>  - Add a buyer
  REMOVER COMPRADOR <telefone>           - Remove a buyer
  FORNECEDORES              - List all suppliers
  ADICIONAR FORNECEDOR <nome> <telefone> - Add a supplier
  REMOVER FORNECEDOR <telefone>          - Remove a supplier
  CATEGORIAS                - List all categories with member count
  CRIAR CATEGORIA <nome>    - Create a new category
  REMOVER CATEGORIA <nome>  - Remove a category
  VINCULAR <telefone> <categoria>  - Add buyer to category
  DESVINCULAR <telefone> <categoria> - Remove buyer from category
  CONFIG                    - Show current system settings
  CONFIG <chave> <valor>    - Update a system setting
  CRIAR ANUNCIO             - Start ad creation flow
  CANCELAR                  - Cancel current flow
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.buyers import Buyers
from models.suppliers import Suppliers
from models.categories import Categories
from models.buyer_categories import Buyer_categories
from models.whatsapp_settings import Whatsapp_settings
from services.whatsapp import send_text_message, is_configured
from services.whatsapp_conversation import notify_admin
from services.formatting import format_brl_price

logger = logging.getLogger(__name__)

# ==================== Command Parser ====================

def parse_command(text: str) -> Tuple[str, List[str]]:
    """Parse a WhatsApp message into a command and arguments.
    
    Returns (command, args) where command is uppercase and args are remaining tokens.
    Handles multi-word category names by joining remaining args after a certain position.
    """
    text = text.strip()
    if not text:
        return ("", [])
    
    parts = text.split()
    command = parts[0].upper()
    args = parts[1:] if len(parts) > 1 else []
    return (command, args)


def join_args(args: List[str], start: int = 0, end: Optional[int] = None) -> str:
    """Join argument tokens from start index (inclusive) to end index (exclusive) into a single string.
    
    If end is None, joins all args from start to the end.
    If end is negative, it counts from the end (e.g., -1 excludes the last element).
    """
    if end is None:
        return " ".join(args[start:]).strip()
    if end < 0:
        return " ".join(args[start:end]).strip()
    return " ".join(args[start:end]).strip()


def normalize_phone(phone: str) -> str:
    """Normalize a phone number by keeping only digits."""
    return "".join(c for c in phone if c.isdigit())


def sanitize_text(text: str, max_length: int = 200) -> str:
    """Sanitize user input text to prevent injection attacks.
    
    - Strips leading/trailing whitespace
    - Removes control characters
    - Limits length
    - Removes potential SQL/meta injection patterns
    """
    if not text:
        return ""
    # Remove control characters (keep printable + common whitespace)
    cleaned = "".join(c for c in text if c.isprintable() or c in "\t\n")
    # Strip whitespace
    cleaned = cleaned.strip()
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    # Remove obvious injection patterns
    injection_patterns = ["--", ";", "DROP ", "DELETE ", "INSERT ", "UPDATE ", "SELECT ", "UNION ", "<script", "javascript:", "onerror=", "onload="]
    for pattern in injection_patterns:
        cleaned = cleaned.replace(pattern, "")
    return cleaned


def sanitize_phone(phone: str) -> str:
    """Sanitize and validate a phone number. Returns empty string if invalid."""
    digits = normalize_phone(phone)
    if len(digits) < 10 or len(digits) > 15:
        return ""
    return digits


# ==================== Command Handlers ====================

async def cmd_help(phone: str, db: AsyncSession) -> Dict[str, Any]:
    """Show all available commands."""
    help_text = (
        "📋 *COMANDOS DO SISTEMA*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👥 *CONTATOS*\n"
        "• COMPRADORES\n"
        "• ADICIONAR COMPRADOR <nome> <telefone>\n"
        "• REMOVER COMPRADOR <telefone>\n"
        "• FORNECEDORES\n"
        "• ADICIONAR FORNECEDOR <nome> <telefone>\n"
        "• REMOVER FORNECEDOR <telefone>\n\n"
        "📁 *CATEGORIAS / GRUPOS*\n"
        "• CATEGORIAS\n"
        "• CRIAR CATEGORIA <nome>\n"
        "• REMOVER CATEGORIA <nome>\n"
        "• VINCULAR <telefone> <categoria>\n"
        "• DESVINCULAR <telefone> <categoria>\n\n"
        "⚙️ *CONFIGURAÇÕES*\n"
        "• CONFIG\n"
        "• CONFIG <chave> <valor>\n"
        "  Chaves: AUTO_REPLY, AUTO_ANALYSIS, ESCALATE_PRICE, ESCALATE_INTEREST, INSTRUCOES\n\n"
        "📢 *ANÚNCIO*\n"
        "• CRIAR ANUNCIO\n"
        "• CANCELAR\n\n"
        "🔍 *CONSULTA*\n"
        "• PLACA <placa> — Consultar dados do veículo\n"
        "• FIPE <placa> — Consultar preço FIPE pela placa\n\n"
        "💡 _Exemplo: ADICIONAR COMPRADOR João 5511999999999_"
    )
    await send_text_message(phone, help_text, db)
    return {"handled": True, "action": "help"}


async def cmd_list_buyers(phone: str, db: AsyncSession) -> Dict[str, Any]:
    """List all registered buyers."""
    stmt = select(Buyers).order_by(Buyers.id)
    res = await db.execute(stmt)
    buyers = res.scalars().all()
    
    if not buyers:
        await send_text_message(phone, "👥 Nenhum comprador registrado.", db)
        return {"handled": True, "action": "list_buyers", "count": 0}
    
    lines = [f"👥 *COMPRADORES* ({len(buyers)} total)\n"]
    for b in buyers:
        status_icon = "✅" if b.status == "active" else "❌"
        lines.append(f"{status_icon} {b.name} — {b.phone}")
    
    await send_text_message(phone, "\n".join(lines), db)
    return {"handled": True, "action": "list_buyers", "count": len(buyers)}


async def cmd_add_buyer(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Add a new buyer: ADICIONAR COMPRADOR <nome> <telefone>"""
    # args = ["João", "Silva", "5511999999999"] — name can be multi-word, last arg is phone
    if len(args) < 2:
        await send_text_message(
            phone,
            "⚠️ Formato: ADICIONAR COMPRADOR <nome> <telefone>\n"
            "Exemplo: ADICIONAR COMPRADOR João Silva 5511999999999",
            db,
        )
        return {"handled": True, "action": "add_buyer_error"}
    
    buyer_phone = sanitize_phone(args[-1])
    buyer_name = sanitize_text(join_args(args, 0, -1))  # Everything except last arg
    
    if not buyer_phone:
        await send_text_message(phone, "⚠️ Telefone inválido. Use formato: 5511999999999", db)
        return {"handled": True, "action": "add_buyer_error"}
    if not buyer_name:
        await send_text_message(phone, "⚠️ Nome inválido.", db)
        return {"handled": True, "action": "add_buyer_error"}
    
    # Check if already exists
    existing = await db.execute(
        select(Buyers).where(Buyers.phone.contains(buyer_phone))
    )
    if existing.scalar_one_or_none():
        await send_text_message(phone, f"⚠️ Comprador com telefone {buyer_phone} já existe.", db)
        return {"handled": True, "action": "add_buyer_exists"}
    
    buyer = Buyers(name=buyer_name, phone=buyer_phone, status="active")
    db.add(buyer)
    await db.commit()
    await db.refresh(buyer)
    
    # Auto-assign to "Geral" category (create it if it doesn't exist)
    try:
        geral_stmt = select(Categories).where(Categories.name.ilike("Geral"))
        geral_res = await db.execute(geral_stmt)
        geral_cat = geral_res.scalar_one_or_none()
        if not geral_cat:
            geral_cat = Categories(name="Geral")
            db.add(geral_cat)
            await db.commit()
            await db.refresh(geral_cat)
        # Link buyer to Geral (skip if already linked)
        existing_link = await db.execute(
            select(Buyer_categories).where(
                and_(
                    Buyer_categories.buyer_id == buyer.id,
                    Buyer_categories.category_id == geral_cat.id,
                )
            )
        )
        if not existing_link.scalar_one_or_none():
            link = Buyer_categories(buyer_id=buyer.id, category_id=geral_cat.id)
            db.add(link)
            await db.commit()
    except Exception as cat_err:
        logger.warning(f"Failed to auto-assign Geral category: {cat_err}")
    
    await send_text_message(
        phone,
        f"✅ Comprador adicionado!\n\n👤 {buyer_name}\n📞 {buyer_phone}\n📌 Categoria: Geral",
        db,
    )
    return {"handled": True, "action": "add_buyer", "buyer_id": buyer.id}


async def cmd_remove_buyer(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Remove a buyer: REMOVER COMPRADOR <telefone>"""
    if not args:
        await send_text_message(
            phone,
            "⚠️ Formato: REMOVER COMPRADOR <telefone>\n"
            "Exemplo: REMOVER COMPRADOR 5511999999999",
            db,
        )
        return {"handled": True, "action": "remove_buyer_error"}
    
    buyer_phone = sanitize_phone(args[0])
    
    if not buyer_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "remove_buyer_error"}
    
    stmt = select(Buyers).where(Buyers.phone.contains(buyer_phone))
    res = await db.execute(stmt)
    buyer = res.scalar_one_or_none()
    
    if not buyer:
        await send_text_message(phone, f"⚠️ Comprador com telefone {buyer_phone} não encontrado.", db)
        return {"handled": True, "action": "remove_buyer_not_found"}
    
    # Remove category associations first
    await db.execute(
        delete(Buyer_categories).where(Buyer_categories.buyer_id == buyer.id)
    )
    
    buyer_name = buyer.name
    await db.delete(buyer)
    await db.commit()
    
    await send_text_message(phone, f"✅ Comprador *{buyer_name}* removido com sucesso.", db)
    return {"handled": True, "action": "remove_buyer"}


async def cmd_list_suppliers(phone: str, db: AsyncSession) -> Dict[str, Any]:
    """List all registered suppliers."""
    stmt = select(Suppliers).order_by(Suppliers.id)
    res = await db.execute(stmt)
    suppliers = res.scalars().all()
    
    if not suppliers:
        await send_text_message(phone, "🏭 Nenhum fornecedor registrado.", db)
        return {"handled": True, "action": "list_suppliers", "count": 0}
    
    lines = [f"🏭 *FORNECEDORES* ({len(suppliers)} total)\n"]
    for s in suppliers:
        status_icon = "✅" if s.status == "active" else "❌"
        company = f" ({s.company})" if s.company else ""
        lines.append(f"{status_icon} {s.name}{company} — {s.phone}")
    
    await send_text_message(phone, "\n".join(lines), db)
    return {"handled": True, "action": "list_suppliers", "count": len(suppliers)}


async def cmd_add_supplier(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Add a new supplier: ADICIONAR FORNECEDOR <nome> <telefone>"""
    if len(args) < 2:
        await send_text_message(
            phone,
            "⚠️ Formato: ADICIONAR FORNECEDOR <nome> <telefone>\n"
            "Exemplo: ADICIONAR FORNECEDOR Auto Peças 5511999999999",
            db,
        )
        return {"handled": True, "action": "add_supplier_error"}
    
    supplier_phone = sanitize_phone(args[-1])
    supplier_name = sanitize_text(join_args(args, 0, -1))
    
    if not supplier_phone:
        await send_text_message(phone, "⚠️ Telefone inválido. Use formato: 5511999999999", db)
        return {"handled": True, "action": "add_supplier_error"}
    if not supplier_name:
        await send_text_message(phone, "⚠️ Nome inválido.", db)
        return {"handled": True, "action": "add_supplier_error"}
    
    # Check if already exists
    existing = await db.execute(
        select(Suppliers).where(Suppliers.phone.contains(supplier_phone))
    )
    if existing.scalar_one_or_none():
        await send_text_message(phone, f"⚠️ Fornecedor com telefone {supplier_phone} já existe.", db)
        return {"handled": True, "action": "add_supplier_exists"}
    
    supplier = Suppliers(name=supplier_name, phone=supplier_phone, status="active")
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    
    await send_text_message(
        phone,
        f"✅ Fornecedor adicionado!\n\n🏭 {supplier_name}\n📞 {supplier_phone}",
        db,
    )
    return {"handled": True, "action": "add_supplier", "supplier_id": supplier.id}


async def cmd_remove_supplier(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Remove a supplier: REMOVER FORNECEDOR <telefone>"""
    if not args:
        await send_text_message(
            phone,
            "⚠️ Formato: REMOVER FORNECEDOR <telefone>\n"
            "Exemplo: REMOVER FORNECEDOR 5511999999999",
            db,
        )
        return {"handled": True, "action": "remove_supplier_error"}
    
    supplier_phone = sanitize_phone(args[0])
    
    if not supplier_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "remove_supplier_error"}
    
    stmt = select(Suppliers).where(Suppliers.phone.contains(supplier_phone))
    res = await db.execute(stmt)
    supplier = res.scalar_one_or_none()
    
    if not supplier:
        await send_text_message(phone, f"⚠️ Fornecedor com telefone {supplier_phone} não encontrado.", db)
        return {"handled": True, "action": "remove_supplier_not_found"}
    
    supplier_name = supplier.name
    await db.delete(supplier)
    await db.commit()
    
    await send_text_message(phone, f"✅ Fornecedor *{supplier_name}* removido com sucesso.", db)
    return {"handled": True, "action": "remove_supplier"}


async def cmd_list_categories(phone: str, db: AsyncSession) -> Dict[str, Any]:
    """List all categories with member count."""
    stmt = select(Categories).order_by(Categories.id)
    res = await db.execute(stmt)
    categories = res.scalars().all()
    
    if not categories:
        await send_text_message(phone, "📁 Nenhuma categoria registrada.", db)
        return {"handled": True, "action": "list_categories", "count": 0}
    
    lines = [f"📁 *CATEGORIAS* ({len(categories)} total)\n"]
    for cat in categories:
        # Count buyers in this category
        count_stmt = select(Buyer_categories).where(Buyer_categories.category_id == cat.id)
        count_res = await db.execute(count_stmt)
        member_count = len(count_res.scalars().all())
        
        desc = f" — {cat.description}" if cat.description else ""
        lines.append(f"📌 {cat.name}{desc} ({member_count} compradores)")
    
    await send_text_message(phone, "\n".join(lines), db)
    return {"handled": True, "action": "list_categories", "count": len(categories)}


async def cmd_create_category(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Create a new category: CRIAR CATEGORIA <nome>"""
    if not args:
        await send_text_message(
            phone,
            "⚠️ Formato: CRIAR CATEGORIA <nome>\n"
            "Exemplo: CRIAR CATEGORIA SUV Premium",
            db,
        )
        return {"handled": True, "action": "create_category_error"}
    
    cat_name = sanitize_text(join_args(args))
    
    if not cat_name:
        await send_text_message(phone, "⚠️ Nome de categoria inválido.", db)
        return {"handled": True, "action": "create_category_error"}
    
    # Check if already exists
    existing = await db.execute(
        select(Categories).where(Categories.name.ilike(cat_name))
    )
    if existing.scalar_one_or_none():
        await send_text_message(phone, f"⚠️ Categoria *{cat_name}* já existe.", db)
        return {"handled": True, "action": "create_category_exists"}
    
    category = Categories(name=cat_name)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    await send_text_message(
        phone,
        f"✅ Categoria criada!\n\n📌 {cat_name}",
        db,
    )
    return {"handled": True, "action": "create_category", "category_id": category.id}


async def cmd_remove_category(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Remove a category: REMOVER CATEGORIA <nome>"""
    if not args:
        await send_text_message(
            phone,
            "⚠️ Formato: REMOVER CATEGORIA <nome>\n"
            "Exemplo: REMOVER CATEGORIA SUV Premium",
            db,
        )
        return {"handled": True, "action": "remove_category_error"}
    
    cat_name = sanitize_text(join_args(args))
    
    if not cat_name:
        await send_text_message(phone, "⚠️ Nome de categoria inválido.", db)
        return {"handled": True, "action": "remove_category_error"}
    
    stmt = select(Categories).where(Categories.name.ilike(cat_name))
    res = await db.execute(stmt)
    category = res.scalar_one_or_none()
    
    if not category:
        await send_text_message(phone, f"⚠️ Categoria *{cat_name}* não encontrada.", db)
        return {"handled": True, "action": "remove_category_not_found"}
    
    # Remove buyer associations first
    await db.execute(
        delete(Buyer_categories).where(Buyer_categories.category_id == category.id)
    )
    
    await db.delete(category)
    await db.commit()
    
    await send_text_message(phone, f"✅ Categoria *{cat_name}* removida com sucesso.", db)
    return {"handled": True, "action": "remove_category"}


async def cmd_link_buyer_category(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Link a buyer to a category: VINCULAR <telefone> <categoria>"""
    if len(args) < 2:
        await send_text_message(
            phone,
            "⚠️ Formato: VINCULAR <telefone> <categoria>\n"
            "Exemplo: VINCULAR 5511999999999 SUV Premium",
            db,
        )
        return {"handled": True, "action": "link_error"}
    
    buyer_phone = sanitize_phone(args[0])
    cat_name = sanitize_text(join_args(args, 1))
    
    if not buyer_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "link_error"}
    if not cat_name:
        await send_text_message(phone, "⚠️ Nome de categoria inválido.", db)
        return {"handled": True, "action": "link_error"}
    
    # Find buyer
    buyer_stmt = select(Buyers).where(Buyers.phone.contains(buyer_phone))
    buyer_res = await db.execute(buyer_stmt)
    buyer = buyer_res.scalar_one_or_none()
    
    if not buyer:
        await send_text_message(phone, f"⚠️ Comprador com telefone {buyer_phone} não encontrado.", db)
        return {"handled": True, "action": "link_buyer_not_found"}
    
    # Find category
    cat_stmt = select(Categories).where(Categories.name.ilike(cat_name))
    cat_res = await db.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    
    if not category:
        await send_text_message(phone, f"⚠️ Categoria *{cat_name}* não encontrada.", db)
        return {"handled": True, "action": "link_category_not_found"}
    
    # Check if already linked
    existing = await db.execute(
        select(Buyer_categories).where(
            and_(
                Buyer_categories.buyer_id == buyer.id,
                Buyer_categories.category_id == category.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        await send_text_message(
            phone,
            f"⚠️ {buyer.name} já está na categoria *{category.name}*.",
            db,
        )
        return {"handled": True, "action": "link_already_exists"}
    
    link = Buyer_categories(buyer_id=buyer.id, category_id=category.id)
    db.add(link)
    await db.commit()
    
    await send_text_message(
        phone,
        f"✅ Vinculado!\n\n👤 {buyer.name} → 📌 {category.name}",
        db,
    )
    return {"handled": True, "action": "link_buyer_category"}


async def cmd_unlink_buyer_category(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Unlink a buyer from a category: DESVINCULAR <telefone> <categoria>"""
    if len(args) < 2:
        await send_text_message(
            phone,
            "⚠️ Formato: DESVINCULAR <telefone> <categoria>\n"
            "Exemplo: DESVINCULAR 5511999999999 SUV Premium",
            db,
        )
        return {"handled": True, "action": "unlink_error"}
    
    buyer_phone = sanitize_phone(args[0])
    cat_name = sanitize_text(join_args(args, 1))
    
    if not buyer_phone:
        await send_text_message(phone, "⚠️ Telefone inválido.", db)
        return {"handled": True, "action": "unlink_error"}
    if not cat_name:
        await send_text_message(phone, "⚠️ Nome de categoria inválido.", db)
        return {"handled": True, "action": "unlink_error"}
    
    # Find buyer
    buyer_stmt = select(Buyers).where(Buyers.phone.contains(buyer_phone))
    buyer_res = await db.execute(buyer_stmt)
    buyer = buyer_res.scalar_one_or_none()
    
    if not buyer:
        await send_text_message(phone, f"⚠️ Comprador com telefone {buyer_phone} não encontrado.", db)
        return {"handled": True, "action": "unlink_buyer_not_found"}
    
    # Find category
    cat_stmt = select(Categories).where(Categories.name.ilike(cat_name))
    cat_res = await db.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    
    if not category:
        await send_text_message(phone, f"⚠️ Categoria *{cat_name}* não encontrada.", db)
        return {"handled": True, "action": "unlink_category_not_found"}
    
    # Remove link
    result = await db.execute(
        delete(Buyer_categories).where(
            and_(
                Buyer_categories.buyer_id == buyer.id,
                Buyer_categories.category_id == category.id,
            )
        )
    )
    await db.commit()
    
    if result.rowcount > 0:
        await send_text_message(
            phone,
            f"✅ Desvinculado!\n\n👤 {buyer.name} ✂️ 📌 {category.name}",
            db,
        )
        return {"handled": True, "action": "unlink_buyer_category"}
    else:
        await send_text_message(
            phone,
            f"⚠️ {buyer.name} não está na categoria *{category.name}*.",
            db,
        )
        return {"handled": True, "action": "unlink_not_linked"}


# ==================== Config Settings ====================

CONFIG_KEYS = {
    "AUTO_REPLY": {
        "db_key": "AI_AUTO_REPLY_ENABLED",
        "label": "Resposta Automática",
        "type": "bool",
    },
    "AUTO_ANALYSIS": {
        "db_key": "AI_AUTO_ANALYSIS_ENABLED",
        "label": "Análise Automática",
        "type": "bool",
    },
    "ESCALATE_PRICE": {
        "db_key": "AI_ESCALATE_PRICE",
        "label": "Escalar Preço",
        "type": "bool",
    },
    "ESCALATE_INTEREST": {
        "db_key": "AI_ESCALATE_INTEREST",
        "label": "Escalar Interesse",
        "type": "bool",
    },
    "INSTRUCOES": {
        "db_key": "AI_CUSTOM_INSTRUCTIONS",
        "label": "Instruções Personalizadas",
        "type": "text",
    },
}


async def cmd_show_config(phone: str, db: AsyncSession) -> Dict[str, Any]:
    """Show current system configuration."""
    # Fetch all AI settings
    db_keys = [v["db_key"] for v in CONFIG_KEYS.values()]
    stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key.in_(db_keys))
    res = await db.execute(stmt)
    rows = res.scalars().all()
    db_values = {row.setting_key: row.setting_value for row in rows}
    
    defaults = {
        "AI_AUTO_REPLY_ENABLED": "true",
        "AI_AUTO_ANALYSIS_ENABLED": "true",
        "AI_ESCALATE_PRICE": "true",
        "AI_ESCALATE_INTEREST": "true",
        "AI_CUSTOM_INSTRUCTIONS": "",
    }
    
    lines = ["⚙️ *CONFIGURAÇÕES DO SISTEMA*\n"]
    for cmd_key, info in CONFIG_KEYS.items():
        db_key = info["db_key"]
        val = db_values.get(db_key, defaults.get(db_key, ""))
        label = info["label"]
        if info["type"] == "bool":
            icon = "✅" if val.lower() == "true" else "❌"
            lines.append(f"{icon} {label} ({cmd_key}): {val}")
        else:
            display_val = val if val else "_(vazio)_"
            lines.append(f"📝 {label} ({cmd_key}):\n{display_val}")
    
    lines.append("\n💡 Para alterar: CONFIG <chave> <valor>")
    lines.append("Exemplo: CONFIG AUTO_REPLY off")
    lines.append("Exemplo: CONFIG INSTRUCOES Sempre responder em português")
    
    await send_text_message(phone, "\n".join(lines), db)
    return {"handled": True, "action": "show_config"}


async def cmd_update_config(phone: str, args: List[str], db: AsyncSession) -> Dict[str, Any]:
    """Update a system setting: CONFIG <chave> <valor>"""
    if len(args) < 2:
        await send_text_message(
            phone,
            "⚠️ Formato: CONFIG <chave> <valor>\n"
            "Exemplo: CONFIG AUTO_REPLY off\n"
            "Exemplo: CONFIG INSTRUCOES Sempre responder em português\n\n"
            "Chaves: " + ", ".join(CONFIG_KEYS.keys()),
            db,
        )
        return {"handled": True, "action": "update_config_error"}
    
    key = args[0].upper()
    value = sanitize_text(join_args(args, 1), max_length=500)
    
    if key not in CONFIG_KEYS:
        await send_text_message(
            phone,
            f"⚠️ Chave desconhecida: {key}\n\nChaves disponíveis: " + ", ".join(CONFIG_KEYS.keys()),
            db,
        )
        return {"handled": True, "action": "update_config_invalid_key"}
    
    info = CONFIG_KEYS[key]
    
    # Validate value type
    if info["type"] == "bool":
        if value.lower() in ("on", "true", "sim", "1", "ligado"):
            value = "true"
        elif value.lower() in ("off", "false", "nao", "não", "0", "desligado"):
            value = "false"
        else:
            await send_text_message(
                phone,
                f"⚠️ Valor inválido para {key}. Use: on/true/sim ou off/false/nao",
                db,
            )
            return {"handled": True, "action": "update_config_invalid_value"}
    
    # Save to database
    from services.whatsapp import save_setting
    await save_setting(db, info["db_key"], value)
    
    # Format confirmation
    if info["type"] == "bool":
        status = "✅ ativado" if value == "true" else "❌ desativado"
        await send_text_message(
            phone,
            f"✅ Configuração atualizada!\n\n{info['label']} ({key}): {status}",
            db,
        )
    else:
        await send_text_message(
            phone,
            f"✅ Configuração atualizada!\n\n{info['label']} ({key}):\n{value}",
            db,
        )
    
    return {"handled": True, "action": "update_config", "key": key, "value": value}


# ==================== Main Command Router ====================

async def handle_admin_chat_command(
    phone: str,
    content: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Main router for admin chat commands via WhatsApp.
    
    This is called BEFORE the ad creation workflow and approval commands,
    so it can intercept general management commands.
    
    Returns {"handled": True} if the command was processed,
    or {"handled": False} if the message should be processed by other handlers.
    """
    if not content or not content.strip():
        return {"handled": False}
    
    text = content.strip()
    text_upper = text.upper()
    
    # ---- Help commands ----
    if text_upper in ("AJUDA", "COMANDOS", "HELP", "?"):
        return await cmd_help(phone, db)
    
    # ---- Buyer commands ----
    if text_upper == "COMPRADORES":
        return await cmd_list_buyers(phone, db)
    
    if text_upper.startswith("ADICIONAR COMPRADOR") or text_upper.startswith("ADD COMPRADOR"):
        # Extract args after "ADICIONAR COMPRADOR" or "ADD COMPRADOR"
        prefix_match = re.match(r"(?:ADICIONAR|ADD)\s+COMPRADOR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_add_buyer(phone, args, db)
        return {"handled": False}
    
    if text_upper.startswith("REMOVER COMPRADOR") or text_upper.startswith("DEL COMPRADOR"):
        prefix_match = re.match(r"(?:REMOVER|DEL)\s+COMPRADOR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_remove_buyer(phone, args, db)
        return {"handled": False}
    
    # ---- Supplier commands ----
    if text_upper == "FORNECEDORES":
        return await cmd_list_suppliers(phone, db)
    
    if text_upper.startswith("ADICIONAR FORNECEDOR") or text_upper.startswith("ADD FORNECEDOR"):
        prefix_match = re.match(r"(?:ADICIONAR|ADD)\s+FORNECEDOR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_add_supplier(phone, args, db)
        return {"handled": False}
    
    if text_upper.startswith("REMOVER FORNECEDOR") or text_upper.startswith("DEL FORNECEDOR"):
        prefix_match = re.match(r"(?:REMOVER|DEL)\s+FORNECEDOR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_remove_supplier(phone, args, db)
        return {"handled": False}
    
    # ---- Category commands ----
    if text_upper == "CATEGORIAS":
        return await cmd_list_categories(phone, db)
    
    if text_upper.startswith("CRIAR CATEGORIA"):
        prefix_match = re.match(r"CRIAR\s+CATEGORIA\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_create_category(phone, args, db)
        return {"handled": False}
    
    if text_upper.startswith("REMOVER CATEGORIA") or text_upper.startswith("DEL CATEGORIA"):
        prefix_match = re.match(r"(?:REMOVER|DEL)\s+CATEGORIA\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_remove_category(phone, args, db)
        return {"handled": False}
    
    # ---- Link/Unlink commands ----
    if text_upper.startswith("VINCULAR"):
        prefix_match = re.match(r"VINCULAR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_link_buyer_category(phone, args, db)
        return {"handled": False}
    
    if text_upper.startswith("DESVINCULAR"):
        prefix_match = re.match(r"DESVINCULAR\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            return await cmd_unlink_buyer_category(phone, args, db)
        return {"handled": False}
    
    # ---- Plate lookup command ----
    if text_upper.startswith("PLACA"):
        prefix_match = re.match(r"PLACA\s+", text, re.IGNORECASE)
        if prefix_match:
            plate = re.sub(r"[^A-Za-z0-9]", "", text[prefix_match.end():].strip()).upper()
            if not plate or len(plate) < 7:
                await send_text_message(
                    phone,
                    "⚠️ Formato: PLACA <placa>\n"
                    "Exemplo: PLACA ABC1D23\n\n"
                    "Consulta marca, modelo, ano, cor, combustível e FIPE.",
                    db,
                )
                return {"handled": True, "action": "plate_lookup_error"}
            from services.plate_lookup import lookup_plate
            from services.fipe_lookup import _log_consultation
            result = await lookup_plate(plate)
            if result.get("success"):
                source = result.get("source", "")
                source_label = "ConsultarPlaca" if source == "consultarplaca" else "BrasilAPI"
                lines = [
                    "🚗 *CONSULTA DE PLACA*",
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
                # ConsultarPlaca extras
                if result.get("segment"):
                    lines.append(f"🏷️ Segmento: {result['segment']}")
                if result.get("procedence"):
                    lines.append(f"🌎 Procedência: {result['procedence']}")
                if result.get("municipality"):
                    lines.append(f"🏙️ Município: {result['municipality']}")
                if result.get("uf"):
                    lines.append(f"📍 UF: {result['uf']}")
                if result.get("chassi"):
                    lines.append(f"🔢 Chassi: {result['chassi']}")
                if result.get("power"):
                    lines.append(f"⚡ Potência: {result['power']} cv")
                if result.get("displacement"):
                    lines.append(f"🔧 Cilindradas: {result['displacement']} cc")
                # FIPE price
                if result.get("fipe_price"):
                    lines.append(f"\n💰 *FIPE: {result['fipe_price']}*")
                if result.get("fipe_reference"):
                    lines.append(f"📊 Referência: {result['fipe_reference']}")
                if result.get("fipe_code"):
                    lines.append(f"📋 Código FIPE: {result['fipe_code']}")
                # Show FIPE versions if available (ConsultarPlaca)
                fipe_versions = result.get("fipe_versions", [])
                if len(fipe_versions) > 1:
                    lines.append(f"\n📋 *Versões FIPE ({len(fipe_versions)}):*")
                    for i, v in enumerate(fipe_versions[:5]):
                        version_name = v.get("modelo_versao", "-")
                        version_price = v.get("preco", "-")
                        if version_price and version_price != "-":
                            version_price = format_brl_price(version_price)
                        lines.append(f"  {i+1}. {version_name}: {version_price}")
                    if len(fipe_versions) > 5:
                        lines.append(f"  ... e mais {len(fipe_versions) - 5} versões")
                await send_text_message(phone, "\n".join(lines), db)
                # Log FIPE consultation for audit
                vehicle_desc = f"{result.get('brand', '')} {result.get('model', '')} {result.get('ano_modelo') or result.get('year', '')}".strip()
                await _log_consultation(
                    db, phone=phone, plate=plate, fipe_code=result.get("fipe_code", ""),
                    source="whatsapp_admin_plate", user_id="",
                    result_json=result, vehicle_description=vehicle_desc,
                    price_returned=result.get("fipe_price", ""),
                )
                return {"handled": True, "action": "plate_lookup", "plate": plate}
            else:
                await send_text_message(
                    phone,
                    f"❌ {result.get('error', 'Erro ao consultar placa')}",
                    db,
                )
                return {"handled": True, "action": "plate_lookup_error"}
        else:
            await send_text_message(
                phone,
                "⚠️ Formato: PLACA <placa>\n"
                "Exemplo: PLACA ABC1D23",
                db,
            )
            return {"handled": True, "action": "plate_lookup_help"}
    
    # ---- FIPE lookup command (by plate) ----
    if text_upper.startswith("FIPE"):
        prefix_match = re.match(r"FIPE\s+", text, re.IGNORECASE)
        if prefix_match:
            plate = re.sub(r"[^A-Za-z0-9]", "", text[prefix_match.end():].strip()).upper()
            if not plate or len(plate) < 7:
                await send_text_message(
                    phone,
                    "⚠️ Formato: FIPE <placa>\n"
                    "Exemplo: FIPE ABC1D23\n\n"
                    "Consulta preço FIPE pela placa do veículo.\n"
                    "Busca dados na ConsultarPlaca e preço na API FIPE.",
                    db,
                )
                return {"handled": True, "action": "fipe_lookup_error"}
            from services.fipe_lookup import lookup_fipe_by_plate
            result = await lookup_fipe_by_plate(plate, db, phone=phone, source="whatsapp_admin")
            if result.get("success"):
                source = result.get("source", "")
                source_label = "ConsultarPlaca" if source == "consultarplaca" else "BrasilAPI"
                lines = [
                    "💰 *CONSULTA FIPE POR PLACA*",
                    f"📡 Fonte: {source_label}",
                    "",
                    f"🔖 Placa: {result.get('plate', plate)}",
                    f"🏭 Marca: {result.get('brand', '-')}",
                    f"🚘 Modelo: {result.get('model', '-')}",
                    f"📅 Ano: {result.get('year', '-')}",
                    f"🎨 Cor: {result.get('color', '-')}",
                    f"⛽ Combustível: {result.get('fuel', '-')}",
                ]
                # FIPE code
                if result.get("fipe_code"):
                    lines.append(f"📋 Código FIPE: {result['fipe_code']}")
                # Main FIPE price
                if result.get("fipe_price"):
                    lines.append(f"\n💎 *FIPE: {result['fipe_price']}*")
                # FIPE versions
                fipe_versions = result.get("fipe_versions", [])
                if len(fipe_versions) > 1:
                    lines.append(f"\n📋 *Versões FIPE ({len(fipe_versions)}):*")
                    for i, v in enumerate(fipe_versions[:8]):
                        version_name = v.get("modelo_versao", "-")
                        version_price = v.get("preco", "-")
                        if version_price and version_price != "-":
                            version_price = format_brl_price(version_price)
                        lines.append(f"  {i+1}. {version_name}: {version_price}")
                    if len(fipe_versions) > 8:
                        lines.append(f"  ... e mais {len(fipe_versions) - 8} versões")
                # Price history from BrasilAPI
                prices = result.get("prices", [])
                if len(prices) > 1:
                    lines.append(f"\n📈 *Histórico ({min(len(prices), 6)} meses):*")
                    for p in prices[:6]:
                        lines.append(f"  • {p.get('mes_referencia', '-')}: {p.get('valor', '-')}")
                await send_text_message(phone, "\n".join(lines), db)
                return {"handled": True, "action": "fipe_lookup", "plate": plate}
            else:
                await send_text_message(
                    phone,
                    f"❌ {result.get('error', 'Erro ao consultar FIPE')}",
                    db,
                )
                return {"handled": True, "action": "fipe_lookup_error"}
        else:
            await send_text_message(
                phone,
                "⚠️ Formato: FIPE <placa>\n"
                "Exemplo: FIPE ABC1D23",
                db,
            )
            return {"handled": True, "action": "fipe_lookup_help"}

    # ---- Config commands ----
    if text_upper == "CONFIG":
        return await cmd_show_config(phone, db)
    
    if text_upper.startswith("CONFIG "):
        prefix_match = re.match(r"CONFIG\s+", text, re.IGNORECASE)
        if prefix_match:
            remaining = text[prefix_match.end():].strip()
            args = remaining.split() if remaining else []
            if len(args) >= 2:
                return await cmd_update_config(phone, args, db)
            else:
                await send_text_message(
                    phone,
                    "⚠️ Formato: CONFIG <chave> <valor>\n"
                    "Exemplo: CONFIG AUTO_REPLY off\n\n"
                    "Use apenas CONFIG para ver as configurações atuais.",
                    db,
                )
                return {"handled": True, "action": "config_help"}
        return {"handled": False}
    
    # Not a recognized management command
    return {"handled": False}