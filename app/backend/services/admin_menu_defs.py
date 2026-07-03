"""
Admin menu definitions for WhatsApp numeric navigation.

Defines the complete menu tree as a declarative structure.
Each menu has:
  - title: Display name shown to the admin
  - options: List of (number, label, action) tuples
  - input_prompt: If set, the menu expects free-text input (e.g., a plate number)

Actions:
  - "submenu:<path>" → Navigate to another menu
  - "handler:<name>" → Execute a handler function in admin_menu.py
  - "back" → Return to parent menu
"""

from typing import Any, Dict, List, Optional, Tuple


# ==================== Menu Tree Definition ====================

MENUS: Dict[str, Dict[str, Any]] = {
    "main": {
        "title": "AUTOHUB\nPainel Administrativo",
        "options": [
            (1, "Veículos", "submenu:vehicles"),
            (2, "Consultas Veiculares", "submenu:queries"),
            (3, "Compradores", "submenu:buyers"),
            (4, "Fornecedores", "submenu:suppliers"),
            (5, "Negociações", "submenu:negotiations"),
            (6, "Relatórios", "submenu:reports"),
            (7, "Configurações", "submenu:settings"),
            (8, "Ajuda", "handler:help"),
        ],
        "footer": "Digite apenas o número da opção desejada.",
    },

    # ==================== Veículos ====================
    "vehicles": {
        "title": "VEÍCULOS",
        "parent": "main",
        "options": [
            (1, "Ofertas Pendentes", "handler:vehicles_pending"),
            (2, "Nova Oferta Manual", "handler:vehicles_new_offer"),
            (3, "Enviar Oferta", "submenu:vehicles_send"),
            (4, "Editar Oferta", "submenu:vehicles_edit"),
            (5, "Buscar Veículo", "submenu:vehicles_search"),
            (6, "Marcar como Vendido", "submenu:vehicles_mark_sold"),
            (7, "Histórico do Veículo", "submenu:vehicles_history"),
            (8, "Voltar", "back"),
        ],
    },

    "vehicles_send": {
        "title": "ENVIAR OFERTA",
        "parent": "vehicles",
        "input_prompt": "Informe o código da oferta (ex: 123) ou a placa do veículo.",
        "input_handler": "vehicles_send_select",
    },

    "vehicles_send_confirm": {
        "title": "ENVIAR OFERTA",
        "parent": "vehicles",
        "dynamic_options": "vehicles_send_categories",
        "footer": "Selecione a categoria para enviar a oferta.",
    },

    "vehicles_edit": {
        "title": "EDITAR OFERTA",
        "parent": "vehicles",
        "input_prompt": "Informe o código da oferta que deseja editar.",
        "input_handler": "vehicles_edit_show",
    },

    "vehicles_search": {
        "title": "BUSCAR VEÍCULO",
        "parent": "vehicles",
        "input_prompt": "Informe a placa ou parte do nome do veículo.",
        "input_handler": "vehicles_search_query",
    },

    "vehicles_mark_sold": {
        "title": "MARCAR COMO VENDIDO",
        "parent": "vehicles",
        "input_prompt": "Informe o código da oferta ou a placa.",
        "input_handler": "vehicles_sold_select_buyer",
    },

    "vehicles_sold_select_buyer": {
        "title": "SELECIONE O COMPRADOR",
        "parent": "vehicles",
        "dynamic_options": "vehicles_sold_buyers",
        "footer": "Selecione o comprador.",
    },

    "vehicles_sold_entered": {
        "title": None,
        "parent": "vehicles",
        "options": [
            (1, "Entrou", "handler:vehicles_sold_entered_yes"),
            (2, "Não Entrou", "handler:vehicles_sold_entered_no"),
        ],
    },

    "vehicles_sold_docs": {
        "title": "Selecione a documentação.",
        "parent": "vehicles",
        "options": [
            (1, "Documentação OK", "handler:vehicles_sold_docs_ok"),
            (2, "Documentação Pendente", "handler:vehicles_sold_docs_pending"),
        ],
    },

    "vehicles_sold_status": {
        "title": "Selecione a situação.",
        "parent": "vehicles",
        "options": [
            (1, "Em processo de troca", "handler:vehicles_sold_status_exchange"),
            (2, "Disponível para retirada", "handler:vehicles_sold_status_available"),
            (3, "Veículo retirado", "handler:vehicles_sold_status_withdrawn"),
        ],
    },

    "vehicles_history": {
        "title": "HISTÓRICO DO VEÍCULO",
        "parent": "vehicles",
        "input_prompt": "Informe a placa do veículo.",
        "input_handler": "vehicles_history_query",
    },

    # ==================== Consultas Veiculares ====================
    "queries": {
        "title": "CONSULTAS VEICULARES",
        "parent": "main",
        "options": [
            (1, "Consulta Básica", "submenu:queries_basic"),
            (2, "Consulta Completa", "submenu:queries_complete"),
            (3, "Débitos", "submenu:queries_debts"),
            (4, "Multas", "submenu:queries_fines"),
            (5, "Gravame", "submenu:queries_encumbrance"),
            (6, "Histórico de Leilão", "submenu:queries_auction"),
            (7, "Sinistro", "submenu:queries_accident"),
            (8, "FIPE", "submenu:queries_fipe"),
            (9, "Histórico do Veículo", "submenu:queries_vehicle_history"),
            (10, "Voltar", "back"),
        ],
    },

    "queries_basic": {
        "title": "CONSULTA BÁSICA",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_basic",
    },

    "queries_complete": {
        "title": "CONSULTA COMPLETA",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_complete",
    },

    "queries_debts": {
        "title": "CONSULTA DE DÉBITOS",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_debts",
    },

    "queries_fines": {
        "title": "CONSULTA DE MULTAS",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_fines",
    },

    "queries_encumbrance": {
        "title": "CONSULTA GRAVAME",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_encumbrance",
    },

    "queries_auction": {
        "title": "CONSULTA HISTÓRICO DE LEILÃO",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_auction",
    },

    "queries_accident": {
        "title": "CONSULTA SINISTRO",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_accident",
    },

    "queries_fipe": {
        "title": "CONSULTA FIPE",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_fipe",
    },

    "queries_vehicle_history": {
        "title": "HISTÓRICO DO VEÍCULO",
        "parent": "queries",
        "input_prompt": "Digite a placa do veículo.",
        "input_handler": "query_vehicle_history",
    },

    # ==================== Compradores ====================
    "buyers": {
        "title": "COMPRADORES",
        "parent": "main",
        "options": [
            (1, "Listar Compradores", "handler:buyers_list"),
            (2, "Adicionar Comprador", "submenu:buyers_add"),
            (3, "Remover Comprador", "submenu:buyers_remove"),
            (4, "Vincular Categoria", "submenu:buyers_link"),
            (5, "Desvincular Categoria", "submenu:buyers_unlink"),
            (6, "Voltar", "back"),
        ],
    },

    "buyers_add": {
        "title": "ADICIONAR COMPRADOR",
        "parent": "buyers",
        "input_prompt": "Informe nome e telefone do comprador.\nExemplo: João Silva 5511999999999",
        "input_handler": "buyers_add",
    },

    "buyers_remove": {
        "title": "REMOVER COMPRADOR",
        "parent": "buyers",
        "input_prompt": "Informe o telefone do comprador.",
        "input_handler": "buyers_remove",
    },

    "buyers_link": {
        "title": "VINCULAR CATEGORIA",
        "parent": "buyers",
        "input_prompt": "Informe telefone e categoria.\nExemplo: 5511999999999 SUV Premium",
        "input_handler": "buyers_link",
    },

    "buyers_unlink": {
        "title": "DESVINCULAR CATEGORIA",
        "parent": "buyers",
        "input_prompt": "Informe telefone e categoria.\nExemplo: 5511999999999 SUV Premium",
        "input_handler": "buyers_unlink",
    },

    # ==================== Fornecedores ====================
    "suppliers": {
        "title": "FORNECEDORES",
        "parent": "main",
        "options": [
            (1, "Listar Fornecedores", "handler:suppliers_list"),
            (2, "Adicionar Fornecedor", "submenu:suppliers_add"),
            (3, "Remover Fornecedor", "submenu:suppliers_remove"),
            (4, "Voltar", "back"),
        ],
    },

    "suppliers_add": {
        "title": "ADICIONAR FORNECEDOR",
        "parent": "suppliers",
        "input_prompt": "Informe nome e telefone do fornecedor.\nExemplo: Auto Peças 5511999999999",
        "input_handler": "suppliers_add",
    },

    "suppliers_remove": {
        "title": "REMOVER FORNECEDOR",
        "parent": "suppliers",
        "input_prompt": "Informe o telefone do fornecedor.",
        "input_handler": "suppliers_remove",
    },

    # ==================== Negociações ====================
    "negotiations": {
        "title": "NEGOCIAÇÕES",
        "parent": "main",
        "options": [
            (1, "Em Andamento", "handler:negotiations_active"),
            (2, "Finalizadas", "handler:negotiations_finished"),
            (3, "Pendentes", "handler:negotiations_pending"),
            (4, "Voltar", "back"),
        ],
    },

    # ==================== Relatórios ====================
    "reports": {
        "title": "RELATÓRIOS",
        "parent": "main",
        "options": [
            (1, "Ofertas do Mês", "handler:reports_monthly_offers"),
            (2, "Vendas", "handler:reports_sales"),
            (3, "Compradores Ativos", "handler:reports_active_buyers"),
            (4, "Voltar", "back"),
        ],
    },

    # ==================== Configurações ====================
    "settings": {
        "title": "CONFIGURAÇÕES",
        "parent": "main",
        "options": [
            (1, "Ver Configurações", "handler:settings_show"),
            (2, "Alterar Configuração", "submenu:settings_update"),
            (3, "Números de Negociação", "handler:settings_negotiation_numbers"),
            (4, "Voltar", "back"),
        ],
    },

    "settings_update": {
        "title": "ALTERAR CONFIGURAÇÃO",
        "parent": "settings",
        "options": [
            (1, "Resposta Automática", "handler:settings_toggle_auto_reply"),
            (2, "Análise Automática", "handler:settings_toggle_auto_analysis"),
            (3, "Escalar Preço", "handler:settings_toggle_escalate_price"),
            (4, "Escalar Interesse", "handler:settings_toggle_escalate_interest"),
            (5, "Instruções Personalizadas", "submenu:settings_custom_instructions"),
            (6, "Voltar", "back"),
        ],
    },

    "settings_custom_instructions": {
        "title": "INSTRUÇÕES PERSONALIZADAS",
        "parent": "settings_update",
        "input_prompt": "Digite as novas instruções personalizadas para a IA.\nOu digite LIMPAR para remover.",
        "input_handler": "settings_update_instructions",
    },
}


# ==================== Helper Functions ====================

def get_menu(menu_path: str) -> Optional[Dict[str, Any]]:
    """Get a menu definition by its path."""
    return MENUS.get(menu_path)


def get_parent_menu(menu_path: str) -> Optional[str]:
    """Get the parent menu path for a given menu."""
    menu = MENUS.get(menu_path)
    if menu and menu.get("parent"):
        return menu["parent"]
    return "main"


def format_menu_message(menu_path: str, dynamic_data: Optional[Dict] = None) -> str:
    """Format a menu as a WhatsApp message string."""
    menu = MENUS.get(menu_path)
    if not menu:
        return "❌ Menu não encontrado. Digite *menu* para voltar."

    lines = []

    # Title
    title = menu.get("title")
    if title:
        lines.append(f"*{title}*")
        lines.append("")

    # Options
    options = menu.get("options", [])

    # Handle dynamic options
    if menu.get("dynamic_options") and dynamic_data:
        dyn_opts = dynamic_data.get("dynamic_options", [])
        if dyn_opts:
            options = dyn_opts

    for num, label, _action in options:
        lines.append(f"{num} - {label}")

    # Footer
    footer = menu.get("footer", "Digite apenas o número.")
    if footer:
        lines.append("")
        lines.append(footer)

    return "\n".join(lines)


def is_input_menu(menu_path: str) -> bool:
    """Check if a menu expects free-text input rather than numeric selection."""
    menu = MENUS.get(menu_path)
    return bool(menu and menu.get("input_prompt"))


def get_input_prompt(menu_path: str) -> str:
    """Get the input prompt for a menu that expects free-text input."""
    menu = MENUS.get(menu_path)
    if menu and menu.get("input_prompt"):
        return menu["input_prompt"]
    return "Digite a informação solicitada:"


def get_input_handler(menu_path: str) -> Optional[str]:
    """Get the handler name for a menu's input."""
    menu = MENUS.get(menu_path)
    if menu and menu.get("input_handler"):
        return menu["input_handler"]
    return None


def resolve_option(menu_path: str, option_num: int, dynamic_data: Optional[Dict] = None) -> Optional[str]:
    """Resolve a numeric option selection to its action string.

    Returns the action string (e.g., "submenu:vehicles", "handler:help", "back")
    or None if the option number is not valid.
    """
    menu = MENUS.get(menu_path)
    if not menu:
        return None

    options = menu.get("options", [])

    # Handle dynamic options
    if menu.get("dynamic_options") and dynamic_data:
        dyn_opts = dynamic_data.get("dynamic_options", [])
        if dyn_opts:
            options = dyn_opts

    for num, _label, action in options:
        if num == option_num:
            return action

    return None