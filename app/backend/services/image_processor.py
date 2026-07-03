"""
Image processing service for vehicle photos.
- Detects and blurs license plates
- Detects and removes/blurs company logos in the background
- Preserves vehicle details
"""

import io
import logging
import os
import re
import urllib3
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.aihub import AIHubService
from schemas.aihub import GenTxtRequest, ChatMessage

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = os.environ.get("EVOLUTION_SSL_VERIFY", "false").lower() == "true"

PLATE_DETECTION_PROMPT = """Analise esta imagem de um veículo e identifique:

1. Há uma placa de licença visível? Se sim, descreva a posição aproximada (topo, centro, inferior, esquerda, direita) e se está na frente ou traseira do veículo.
2. Há algum logotipo de empresa/concessionária visível no fundo ou em adesivos no veículo? Se sim, descreva a posição.
3. O veículo está bem visível e preservado?

Responda em formato JSON:
{
  "plates": [{"position": "top-left|top-center|top-right|center-left|center|center-right|bottom-left|bottom-center|bottom-right", "side": "front|back|unknown"}],
  "logos": [{"position": "top-left|top-center|top-right|center-left|center|center-right|bottom-left|bottom-center|bottom-right", "type": "background|sticker|sign"}],
  "vehicle_visible": true/false,
  "notes": "observações adicionais"
}

Retorne APENAS o JSON, sem texto adicional."""


async def analyze_image_for_plates_and_logos(
    image_url: str,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Use AI vision to detect license plates and logos in a vehicle image.
    
    Returns dict with plates and logos positions for blurring.
    """
    try:
        service = AIHubService()
        
        # Use a vision-capable model for image analysis
        from services.whatsapp_ai import _get_model_setting
        model = await _get_model_setting(db, "AI_IMAGE_ANALYSIS_MODEL", "gemini-2.5-pro")
        
        request = GenTxtRequest(
            messages=[
                ChatMessage(
                    role="user",
                    content=PLATE_DETECTION_PROMPT,
                    image_url=image_url,
                ),
            ],
            model=model,
            temperature=0.1,
            max_tokens=1024,
        )
        
        response = await service.gentxt(request)
        raw = response.content.strip()
        
        # Extract JSON from response
        from services.whatsapp_ai import extract_json_block
        payload_text = extract_json_block(raw)
        
        import json
        try:
            result = json.loads(payload_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse plate detection result: {raw[:200]}")
            result = {"plates": [], "logos": [], "vehicle_visible": True, "notes": "parse_error"}
        
        return result
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return {"plates": [], "logos": [], "vehicle_visible": True, "notes": f"error: {str(e)}"}


async def download_image(image_url: str) -> Optional[bytes]:
    """Download an image from URL."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=SSL_VERIFY) as http:
            response = await http.get(image_url)
            if response.status_code == 200:
                return response.content
            logger.error(f"Failed to download image: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Image download error: {e}")
        return None


def apply_blur_regions(
    image_data: bytes,
    plates: List[Dict[str, str]],
    logos: List[Dict[str, str]],
) -> Optional[bytes]:
    """
    Apply blur to detected plate and logo regions in the image.
    Uses PIL/Pillow for image processing.
    
    Args:
        image_data: Raw image bytes
        plates: List of plate positions detected
        logos: List of logo positions detected
    
    Returns:
        Processed image bytes, or None if processing fails
    """
    try:
        from PIL import Image, ImageFilter
        
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        # Map position strings to approximate pixel regions
        position_map = {
            "top-left": (0, 0, width // 3, height // 3),
            "top-center": (width // 3, 0, 2 * width // 3, height // 3),
            "top-right": (2 * width // 3, 0, width, height // 3),
            "center-left": (0, height // 3, width // 3, 2 * height // 3),
            "center": (width // 3, height // 3, 2 * width // 3, 2 * height // 3),
            "center-right": (2 * width // 3, height // 3, width, 2 * height // 3),
            "bottom-left": (0, 2 * height // 3, width // 3, height),
            "bottom-center": (width // 3, 2 * height // 3, 2 * width // 3, height),
            "bottom-right": (2 * width // 3, 2 * height // 3, width, height),
        }
        
        regions_to_blur = []
        
        # Add plate regions - plates are typically small, use a tighter region
        for plate in plates:
            pos = plate.get("position", "")
            if pos in position_map:
                x1, y1, x2, y2 = position_map[pos]
                # Plates are typically in the lower portion of their region
                # and are relatively small - tighten the blur area
                plate_h = (y2 - y1) // 3
                plate_w = (x2 - x1) // 2
                plate_x1 = x1 + (x2 - x1) // 4
                plate_y1 = y2 - plate_h - plate_h // 2
                regions_to_blur.append((plate_x1, plate_y1, plate_x1 + plate_w, plate_y1 + plate_h))
        
        # Add logo regions - logos can be larger
        for logo in logos:
            pos = logo.get("position", "")
            if pos in position_map:
                regions_to_blur.append(position_map[pos])
        
        if not regions_to_blur:
            # No regions to blur, return original
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
        
        # Apply Gaussian blur to each detected region
        for x1, y1, x2, y2 in regions_to_blur:
            # Clamp coordinates
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(width, int(x2))
            y2 = min(height, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Crop the region, blur it, and paste back
            region = img.crop((x1, y1, x2, y2))
            blurred_region = region.filter(ImageFilter.GaussianBlur(radius=15))
            img.paste(blurred_region, (x1, y1))
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
        
    except ImportError:
        logger.warning("PIL/Pillow not available, skipping image processing")
        return image_data
    except Exception as e:
        logger.error(f"Image blur processing error: {e}")
        return image_data


async def process_vehicle_image(
    image_url: str,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    Full pipeline: download image, detect plates/logos, blur them, upload processed image.
    
    Returns:
        Dict with original_url, processed_url, plates_found, logos_found
    """
    # Step 1: Analyze image for plates and logos
    analysis = await analyze_image_for_plates_and_logos(image_url, db)
    
    plates = analysis.get("plates", [])
    logos = analysis.get("logos", [])
    
    # Step 2: If nothing to blur, return original
    if not plates and not logos:
        return {
            "original_url": image_url,
            "processed_url": image_url,
            "plates_found": 0,
            "logos_found": 0,
            "was_processed": False,
        }
    
    # Step 3: Download image
    image_data = await download_image(image_url)
    if not image_data:
        return {
            "original_url": image_url,
            "processed_url": image_url,
            "plates_found": len(plates),
            "logos_found": len(logos),
            "was_processed": False,
            "error": "download_failed",
        }
    
    # Step 4: Apply blur to detected regions
    processed_data = apply_blur_regions(image_data, plates, logos)
    if not processed_data:
        return {
            "original_url": image_url,
            "processed_url": image_url,
            "plates_found": len(plates),
            "logos_found": len(logos),
            "was_processed": False,
            "error": "processing_failed",
        }
    
    # Step 5: Upload processed image to object storage
    try:
        from services.storage import StorageService
        from schemas.storage import FileUpDownRequest
        import hashlib

        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        filename = f"processed_{url_hash}.jpg"
        object_key = f"vehicle-images/processed/{filename}"

        storage = StorageService()

        upload_req = FileUpDownRequest(bucket_name="vehicle-images", object_key=object_key)
        upload_resp = await storage.create_upload_url(upload_req)
        upload_url = upload_resp.upload_url

        if not upload_url:
            raise ValueError("Failed to get upload URL")

        async with httpx.AsyncClient(timeout=60.0, verify=SSL_VERIFY) as http:
            upload_res = await http.put(
                upload_url,
                content=processed_data,
                headers={"Content-Type": "image/jpeg"},
            )
            upload_res.raise_for_status()

        download_req = FileUpDownRequest(bucket_name="vehicle-images", object_key=object_key)
        download_resp = await storage.create_download_url(download_req)
        processed_url = download_resp.download_url or ""

        return {
            "original_url": image_url,
            "processed_url": processed_url,
            "plates_found": len(plates),
            "logos_found": len(logos),
            "was_processed": True,
        }

    except Exception as e:
        logger.error(f"Failed to upload processed image: {e}")
        return {
            "original_url": image_url,
            "processed_url": image_url,
            "plates_found": len(plates),
            "logos_found": len(logos),
            "was_processed": False,
            "error": f"upload_failed: {str(e)}",
        }