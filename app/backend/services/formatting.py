"""
Shared formatting utilities for the AutoHub system.

Centralizes price formatting, vehicle description building,
and other common formatting operations used across services.
"""

from typing import Any, Dict, Optional


def format_brl_price(value: Any) -> str:
    """Format a numeric value as a Brazilian Real price string.

    Examples:
        format_brl_price(118900) → "R$ 118.900,00"
        format_brl_price(118900.50) → "R$ 118.900,50"
        format_brl_price("118900") → "R$ 118.900,00"
    """
    if value is None:
        return ""
    try:
        if isinstance(value, str):
            # Try to parse string like "R$ 118.900" or "118900"
            cleaned = value.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            num = float(cleaned)
        else:
            num = float(value)
        return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value) if value else ""


def build_vehicle_description(brand: str = "", model: str = "", version: str = "", year: str = "") -> str:
    """Build a vehicle description string from components.

    Example: "Toyota Corolla XEi 2023"
    """
    parts = [p for p in [brand, model, version, year] if p]
    return " ".join(parts).strip()


def build_offer_title(analysis: Dict[str, Any]) -> str:
    """Build a title for an offer from AI analysis data (English field names)."""
    vehicle = build_vehicle_description(
        analysis.get("brand", ""),
        analysis.get("model", ""),
        analysis.get("version", ""),
    )
    year = analysis.get("year", "")
    parts = [p for p in [vehicle, str(year)] if p]
    return " ".join(parts) if parts else "Veículo a identificar"


def build_offer_description(analysis: Dict[str, Any]) -> str:
    """Build a description for an offer using the company template format.

    Uses English field names from AI parser output.
    """
    lines = []
    vehicle = build_vehicle_description(
        analysis.get("brand", ""),
        analysis.get("model", ""),
        analysis.get("version", ""),
    )
    if vehicle:
        lines.append(f"MODELO: {vehicle}")
    if analysis.get("year"):
        lines.append(f"ANO: {analysis['year']}")
    if analysis.get("fipe_value"):
        lines.append(f"FIPE: {analysis['fipe_value']}")
    if analysis.get("fuel"):
        lines.append(f"COMBUSTIVEL: {analysis['fuel']}")
    if analysis.get("mileage"):
        lines.append(f"KM: {analysis['mileage']}")
    if analysis.get("transmission"):
        lines.append(f"CAMBIO: {analysis['transmission']}")
    manual_val = "sim" if analysis.get("has_manual") else "não informado"
    lines.append(f"MANUAL: {manual_val}")
    chave_val = "sim" if analysis.get("has_spare_key") else "não informado"
    lines.append(f"CHAVE RESERVA: {chave_val}")
    if analysis.get("description"):
        lines.append(f"DESCRICAO: {analysis['description']}")
    if analysis.get("supplier_price"):
        lines.append(f"VALOR: {analysis['supplier_price']}")
    if analysis.get("is_auction"):
        lines.append("⚠️ Veículo de leilão")
    if analysis.get("color"):
        lines.append(f"Cor: {analysis['color']}")
    if analysis.get("city"):
        lines.append(f"Cidade: {analysis['city']}")
    if analysis.get("suggested_category"):
        lines.append(f"Categoria sugerida: {analysis['suggested_category']}")
    return "\n".join(lines)


def parse_price(price_str: Optional[str]) -> Optional[float]:
    """Parse a price string like 'R$ 118.900' into a float.

    Handles Brazilian format: R$ 118.900,00 → 118900.00
    """
    if not price_str:
        return None
    cleaned = price_str.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def format_fipe_reference(ref: str) -> str:
    """Convert ConsultarPlaca reference format '2025_04' to 'Abril/2025'."""
    if not ref:
        return ""
    try:
        year_str, month_str = ref.split("_")
        month_names = {
            "01": "Janeiro", "02": "Fevereiro", "03": "Março",
            "04": "Abril", "05": "Maio", "06": "Junho",
            "07": "Julho", "08": "Agosto", "09": "Setembro",
            "10": "Outubro", "11": "Novembro", "12": "Dezembro",
        }
        return f"{month_names.get(month_str, month_str)}/{year_str}"
    except (ValueError, AttributeError):
        return ref


def extract_consultarplaca_vehicle(data: dict) -> Dict[str, Any]:
    """Extract vehicle data from ConsultarPlaca API response.

    Parses the nested response structure and returns a flat dict
    with standardized field names.
    """
    dados = data.get("dados", {})
    info_veiculo = dados.get("informacoes_veiculo", {})
    dados_veiculo = info_veiculo.get("dados_veiculo", {})
    dados_tecnicos = info_veiculo.get("dados_tecnicos", {})

    return {
        "plate": dados_veiculo.get("placa", ""),
        "brand": dados_veiculo.get("marca", ""),
        "model": dados_veiculo.get("modelo", ""),
        "year": dados_veiculo.get("ano_modelo", "") or dados_veiculo.get("ano_frabricacao", ""),
        "color": dados_veiculo.get("cor", ""),
        "fuel": dados_veiculo.get("combustivel", ""),
        "chassi": dados_veiculo.get("chassi", ""),
        "segment": dados_veiculo.get("segmento", ""),
        "procedence": dados_veiculo.get("procedencia", ""),
        "municipality": dados_veiculo.get("municipio", ""),
        "uf": dados_veiculo.get("uf_municipio", ""),
        "ano_fabricacao": dados_veiculo.get("ano_frabricacao", ""),
        "ano_modelo": dados_veiculo.get("ano_modelo", ""),
        "vehicle_type": dados_tecnicos.get("tipo_veiculo", ""),
        "sub_segment": dados_tecnicos.get("sub_segmento", ""),
        "power": dados_tecnicos.get("potencia", ""),
        "displacement": dados_tecnicos.get("cilindradas", ""),
    }


def extract_consultarplaca_fipe(data: dict) -> Dict[str, Any]:
    """Extract FIPE data from ConsultarPlaca API response.

    Returns a dict with fipe_code, fipe_price, fipe_reference, fipe_versions.
    """
    dados = data.get("dados", {})
    informacoes_fipe = dados.get("informacoes_fipe", [])

    fipe_versions = []
    fipe_code = ""
    fipe_price = ""
    fipe_reference = ""

    if isinstance(informacoes_fipe, list) and len(informacoes_fipe) > 0:
        for entry in informacoes_fipe:
            fipe_versions.append({
                "codigo_fipe": entry.get("codigo_fipe", ""),
                "modelo_versao": entry.get("modelo_versao", ""),
                "preco": entry.get("preco", ""),
                "mes_referencia": entry.get("mes_referencia", ""),
            })

        first_fipe = informacoes_fipe[0]
        fipe_code = first_fipe.get("codigo_fipe", "")
        raw_price = first_fipe.get("preco", "")
        if raw_price:
            fipe_price = format_brl_price(raw_price)

        ref = first_fipe.get("mes_referencia", "")
        fipe_reference = format_fipe_reference(ref)

    return {
        "fipe_code": fipe_code,
        "fipe_price": fipe_price,
        "fipe_reference": fipe_reference,
        "fipe_versions": fipe_versions,
    }