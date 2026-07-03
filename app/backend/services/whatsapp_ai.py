"""
AI services for WhatsApp integration.
- Offer parser: analyzes supplier messages to extract vehicle data
- Buyer assistant: auto-replies or escalates buyer messages
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.aihub import AIHubService
from schemas.aihub import GenTxtRequest, ChatMessage

logger = logging.getLogger(__name__)

DEFAULT_AI_MODEL = os.environ.get("AUTOHUB_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
DEFAULT_OFFER_PARSER_MODEL = DEFAULT_AI_MODEL
DEFAULT_BUYER_ASSISTANT_MODEL = DEFAULT_AI_MODEL


async def _get_model_setting(db: Optional[AsyncSession], key: str, default: str) -> str:
    """Read a model setting from the database, falling back to the default."""
    if db is None:
        return default
    try:
        from models.whatsapp_settings import Whatsapp_settings
        stmt = select(Whatsapp_settings).where(Whatsapp_settings.setting_key == key)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.setting_value:
            return row.setting_value
    except Exception as e:
        logger.warning(f"Failed to read model setting {key} from DB: {e}")
    return default

OFFER_PARSER_SYSTEM_PROMPT = """Você é um assistente especializado em interpretar ofertas de veículos recebidas via WhatsApp para a AutoHub.

Você receberá uma série de mensagens consecutivas de um fornecedor, que podem conter texto, descrições de veículos, preços, e referências a fotos/vídeos.

Sua tarefa é analisar TODAS as mensagens em conjunto e extrair as seguintes informações no formato JSON:

{
  "brand": "Marca do veículo (ex: Toyota, Honda, Volkswagen)",
  "model": "Modelo do veículo (ex: Corolla, Civic, Golf)",
  "version": "Versão do veículo (ex: XEi 2.0 Flex, Touring 1.5 Turbo)",
  "year": "Ano do veículo (ex: 2023, 2023/2024)",
  "fuel": "Tipo de combustível (ex: Flex, Gasolina, Diesel, Elétrico)",
  "transmission": "Tipo de câmbio (ex: Automático, Manual, CVT)",
  "mileage": "Quilometragem (ex: 48.000 km)",
  "color": "Cor do veículo, se mencionada",
  "fipe_value": "Valor de referência FIPE (ex: R$ 118.900)",
  "supplier_price": "Preço mencionado pelo fornecedor (ex: R$ 115.000)",
  "has_manual": true/false,
  "has_spare_key": true/false,
  "description": "Descrição livre com observações adicionais (estado, opcionais, acessórios)",
  "photo_count": 0,
  "video_count": 0,
  "is_auction": true/false,
  "suggested_category": "Categoria sugerida (ex: SUV, Hatch, Sedan, Premium, Diesel)",
  "city": "Cidade do veículo, se mencionada"
}

REGRAS IMPORTANTES:
- Separe marca, modelo e versão em campos distintos
- Se uma informação não estiver presente, use null
- Múltiplas mensagens consecutivas referem-se ao MESMO veículo
- Interprete abreviações (ex: "flex" = combustível flex, "aut" = automático)
- O campo "supplier_price" é o preço que o FORNECEDOR pediu (NUNCA enviar ao comprador)
- O campo "fipe_value" é a referência FIPE mencionada
- O campo "is_auction" deve ser true APENAS se houver menção explícita a leilão
- O campo "suggested_category" deve classificar o veículo para direcionar compradores
- Retorne APENAS o JSON, sem texto adicional ou markdown

ANONIMIZAÇÃO OBRIGATÓRIA:
- Remova QUALQUER placa, chassi ou RENAVAM mencionado
- Remova nome do vendedor, loja, concessionária ou empresa
- Remova telefone, WhatsApp, e-mail, links ou QR codes
- Remova endereço ou localização que identifique o fornecedor
- O campo "city" deve conter apenas a cidade genérica, sem endereço específico
"""

BUYER_ASSISTANT_SYSTEM_PROMPT = """Você é um assistente virtual da AutoHub, uma plataforma de intermediação de veículos.

Seu papel é atender compradores que respondem a ofertas de veículos enviadas via WhatsApp.

REGRAS:
- Seja sempre educado e profissional
- NUNCA forneça informações do fornecedor (nome, telefone, empresa)
- NUNCA forneça o preço que o fornecedor pediu - apenas o preço de venda divulgado na oferta
- Se o comprador perguntar sobre disponibilidade, informe que pode verificar
- Se o comprador quiser negociar, informe que encaminhará ao responsável
- Se o comprador pedir mais fotos ou informações, informe que verificará e retornará
- Se a pergunta não puder ser respondida com segurança, diga que encaminhará ao responsável
- Sempre mencione o código da oferta quando relevante
- Mantenha respostas concisas (máximo 3 frases)

Responda sempre em português do Brasil.
"""

BUYER_CLASSIFY_PROMPT = """Classifique a mensagem do comprador em uma das seguintes categorias:

1. "availability" - Pergunta sobre disponibilidade do veículo
2. "price" - Pergunta sobre preço ou negociação de valor
3. "info" - Pede mais informações ou fotos do veículo
4. "status" - Pergunta sobre status da negociação
5. "interest" - Demonstra interesse em comprar ou visitar
6. "other" - Qualquer outra pergunta ou mensagem

Retorne APENAS a categoria como texto simples, sem explicação adicional.

Mensagem do comprador: {message}
"""


def extract_json_block(text: str) -> str:
    """Extract JSON block from AI response text."""
    # Remove markdown code blocks if present
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    # Find JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


async def parse_offer_from_messages(messages: List[Dict[str, Any]], db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """
    Analyze a list of WhatsApp messages from a supplier and extract vehicle data.
    
    Args:
        messages: List of message dicts with 'content', 'message_type', 'media_url', etc.
        db: Optional database session for reading model settings.
    
    Returns:
        Dict with extracted vehicle data fields.
    """
    service = AIHubService()
    model = await _get_model_setting(db, "AI_OFFER_PARSER_MODEL", DEFAULT_OFFER_PARSER_MODEL)
    
    # Build the user message from all conversation messages
    message_lines = []
    for i, msg in enumerate(messages, 1):
        content = msg.get("content", "")
        msg_type = msg.get("message_type", "text")
        if msg_type == "text" and content:
            message_lines.append(f"Mensagem {i} (texto): {content}")
        elif msg_type == "image":
            caption = f" - Legenda: {content}" if content else ""
            message_lines.append(f"Mensagem {i} (imagem){caption}")
        elif msg_type == "video":
            caption = f" - Legenda: {content}" if content else ""
            message_lines.append(f"Mensagem {i} (vídeo){caption}")
        elif msg_type == "document":
            caption = f" - Legenda: {content}" if content else ""
            message_lines.append(f"Mensagem {i} (documento){caption}")
        elif msg_type == "audio":
            message_lines.append(f"Mensagem {i} (áudio)")
        elif content:
            message_lines.append(f"Mensagem {i}: {content}")
    
    if not message_lines:
        return {"error": "Nenhuma mensagem para analisar"}
    
    user_content = "\n".join(message_lines)
    
    request = GenTxtRequest(
        messages=[
            ChatMessage(role="system", content=OFFER_PARSER_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ],
        model=model,
        temperature=0.1,
        max_tokens=2048,
    )
    
    try:
        response = await service.gentxt(request)
        raw_content = response.content.strip()
        payload_text = extract_json_block(raw_content)
        
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            # Try one repair attempt
            repair_request = GenTxtRequest(
                messages=[
                    ChatMessage(role="system", content="Corrija o texto abaixo para que seja um JSON válido. Retorne APENAS o JSON corrigido."),
                    ChatMessage(role="user", content=payload_text),
                ],
                model=model,
                temperature=0.0,
                max_tokens=2048,
            )
            repaired = await service.gentxt(repair_request)
            try:
                payload = json.loads(extract_json_block(repaired.content.strip()))
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI offer extraction output after repair")
                return {"error": "Falha ao interpretar resposta da IA", "raw": raw_content}
        
        # Validate expected fields exist (even if null)
        expected_fields = [
            "brand", "model", "version", "year", "fuel", "transmission",
            "mileage", "color", "fipe_value", "supplier_price",
            "has_manual", "has_spare_key", "description",
            "photo_count", "video_count", "is_auction",
            "suggested_category", "city"
        ]
        for field in expected_fields:
            if field not in payload:
                payload[field] = None
        
        return payload
        
    except Exception as e:
        logger.error(f"AI offer parsing error: {e}")
        return {"error": f"Erro na análise da IA: {str(e)}"}


async def classify_buyer_message(message: str, db: Optional[AsyncSession] = None) -> str:
    """
    Classify a buyer's message into a category.
    
    Returns:
        Category string: availability, price, info, status, interest, other
    """
    service = AIHubService()
    model = await _get_model_setting(db, "AI_BUYER_ASSISTANT_MODEL", DEFAULT_BUYER_ASSISTANT_MODEL)
    
    prompt = BUYER_CLASSIFY_PROMPT.format(message=message)
    
    request = GenTxtRequest(
        messages=[
            ChatMessage(role="user", content=prompt),
        ],
        model=model,
        temperature=0.0,
        max_tokens=50,
    )
    
    try:
        response = await service.gentxt(request)
        category = response.content.strip().lower()
        valid_categories = ["availability", "price", "info", "status", "interest", "other"]
        if category in valid_categories:
            return category
        return "other"
    except Exception as e:
        logger.error(f"Buyer message classification error: {e}")
        return "other"


async def generate_buyer_auto_reply(
    message: str,
    category: str,
    offer_data: Optional[Dict[str, Any]] = None,
    custom_instructions: str = "",
    db: Optional[AsyncSession] = None,
) -> str:
    """
    Generate an auto-reply for a buyer's message.
    
    Args:
        message: The buyer's message
        category: Classified category of the message
        offer_data: Optional offer data for context
        custom_instructions: Optional custom instructions from admin
        db: Optional database session for reading model settings
    
    Returns:
        Auto-reply message text
    """
    service = AIHubService()
    model = await _get_model_setting(db, "AI_BUYER_ASSISTANT_MODEL", DEFAULT_BUYER_ASSISTANT_MODEL)
    
    # Build context
    context_parts = []
    if offer_data:
        offer_context = f"""
Dados da oferta referenciada:
- Código: #{offer_data.get('code', 'N/A')}
- Veículo: {offer_data.get('brand', '')} {offer_data.get('model', '')} {offer_data.get('version', '')}
- Ano: {offer_data.get('year', 'N/A')}
- Preço de venda: {offer_data.get('price', 'N/A')}
- Status: {offer_data.get('status', 'N/A')}
"""
        context_parts.append(offer_context)
    
    if custom_instructions:
        context_parts.append(f"Instruções adicionais do administrador: {custom_instructions}")
    
    context = "\n".join(context_parts) if context_parts else ""
    
    user_prompt = f"""
Mensagem do comprador: {message}
Categoria: {category}
{context}

Gere uma resposta adequada para o comprador. Lembre-se: NUNCA forneça dados do fornecedor.
"""
    
    request = GenTxtRequest(
        messages=[
            ChatMessage(role="system", content=BUYER_ASSISTANT_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ],
        model=model,
        temperature=0.5,
        max_tokens=300,
    )
    
    try:
        response = await service.gentxt(request)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Buyer auto-reply generation error: {e}")
        return "Olá! Recebi sua mensagem e vou encaminhar ao responsável. Em breve entraremos em contato. Obrigado!"


def should_escalate_to_admin(
    category: str,
    message: str,
    escalate_price: bool = True,
    escalate_interest: bool = True,
) -> bool:
    """
    Determine if a buyer message should be escalated to admin.
    
    Escalation rules (configurable via AI settings):
    - Price negotiation requests (if escalate_price is True)
    - Interest in purchasing (if escalate_interest is True)
    - Any message the AI can't confidently handle
    """
    if category == "price" and escalate_price:
        return True
    if category == "interest" and escalate_interest:
        return True
    return False
