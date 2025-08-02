from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from converter import convert_to_avif
import psutil
import os
import subprocess
import base64
import logging

app = FastAPI()

# Mute FastAPI's default logging for /health endpoint
class HealthEndpointFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HealthEndpointFilter())

def get_memory_info():
    """Get current memory usage information"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # Resident Set Size
        "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
        "percent": round(process.memory_percent(), 2)
    }

@app.get("/health")
async def health_check():
    logging.info("[HEALTH] Starting health check")
    avifenc_available = False

    try:
        logging.info("[HEALTH] Checking avifenc availability")
        result = subprocess.run(["avifenc", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            avifenc_available = True
        logging.info(f"[HEALTH] avifenc available: {avifenc_available}")
    except subprocess.TimeoutExpired:
        logging.error("[HEALTH] avifenc check timed out")
    except Exception as e:
        logging.error(f"[HEALTH] avifenc check error: {e}")

    try:
        logging.info("[HEALTH] Fetching memory info")
        memory = get_memory_info()
        logging.info(f"[HEALTH] Memory info: {memory}")
    except Exception as e:
        logging.error(f"[HEALTH] Error fetching memory info: {e}")
        memory = {"error": str(e)}

    is_healthy = avifenc_available

    if not is_healthy:
        logging.warning("[HEALTH] Health check FAILED")
        logging.warning(f"[HEALTH] Memory usage: {memory}")
        logging.warning(f"[HEALTH] avifenc available: {avifenc_available}")

    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "avif-converter",
        "memory": memory,
        "capabilities": {
            "avifenc": avifenc_available
        }
    }

    logging.info(f"[HEALTH] Health check response: {response}")
    return response


@app.post("/convert")
async def convert_image(image: UploadFile = File(...)):
    logging.info("[CONVERT] Received request")
    logging.info(f"[CONVERT] Uploaded file details: filename={image.filename}, content_type={image.content_type}")

    memory_before = get_memory_info()
    logging.info(f"[CONVERT] Memory before conversion: {memory_before}")

    mimeType = image.content_type

    if mimeType not in ["image/jpeg", "image/heic"]:
        logging.error(f"[CONVERT] Unsupported mimeType: {mimeType}")
        raise HTTPException(status_code=400, detail="Only JPEG and HEIC images are supported.")

    file_type = "jpeg" if mimeType == "image/jpeg" else "heic"
    image_data = await image.read()

    logging.info(f"[CONVERT] Received file size: {len(image_data)} bytes")
    logging.info(f"[CONVERT] File type determined: {file_type}")

    try:
        avif_data = convert_to_avif(image_data, file_type, image.filename)
        memory_after = get_memory_info()
        logging.info(f"[CONVERT] Conversion completed successfully")
        logging.info(f"[CONVERT] Memory after conversion: {memory_after}")
        base64_content = base64.b64encode(avif_data).decode('utf-8')
        return {
            "success": True,
            "data": {
                "fullSize": {
                    "filename": image.filename,
                    "content": base64_content,
                    "size": len(avif_data),
                    "mimetype": "image/avif",
                    "variant": "full"
                }
            }
        }
    except Exception as e:
        logging.error(f"[CONVERT] Conversion failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Conversion failed.")
