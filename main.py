# rebuild image on 11.08.2025 / 13.34
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from converter import convert_to_avif
import psutil
import os
import subprocess
import base64
import logging
import tracemalloc
import time
import gc

app = FastAPI()

# force rebuild image
# 🔧 Enable logging with visible formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# 🚫 Filter access logs from /health
class HealthEndpointFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HealthEndpointFilter())

def get_memory_info():
    """Get current memory usage information"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
        "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
        "percent": round(process.memory_percent(), 2)
    }

@app.get("/health")
async def health_check():
    logging.info("[HEALTH] Running health check")
    avifenc_available = False

    try:
        result = subprocess.run(["avifenc", "--version"], capture_output=True, text=True, timeout=5)
        avifenc_available = result.returncode == 0
        logging.info(f"[HEALTH] avifenc available: {avifenc_available}")
    except subprocess.TimeoutExpired:
        logging.error("[HEALTH] avifenc check timed out")
    except Exception as e:
        logging.error(f"[HEALTH] avifenc check error: {e}")

    try:
        memory = get_memory_info()
        logging.info(f"[HEALTH] Memory info: {memory}")
    except Exception as e:
        logging.error(f"[HEALTH] Error fetching memory info: {e}")
        memory = {"error": str(e)}

    return {
        "status": "healthy" if avifenc_available else "unhealthy",
        "service": "avif-converter",
        "memory": memory,
        "capabilities": {
            "avifenc": avifenc_available
        }
    }

@app.post("/convert")
async def convert_image(image: UploadFile = File(...)):
    logging.info("[CONVERT] Request received")
    logging.info(f"[CONVERT] Uploaded file: {image.filename}, type={image.content_type}")

    memory_before = get_memory_info()
    logging.info(f"[CONVERT] Memory before conversion: {memory_before}")

    mime_type = image.content_type
    if mime_type not in ["image/jpeg", "image/heic"]:
        logging.error(f"[CONVERT] Unsupported mime type: {mime_type}")
        raise HTTPException(status_code=400, detail="Only JPEG and HEIC images are supported.")

    file_type = "jpeg" if mime_type == "image/jpeg" else "heic"
    image_data = await image.read()
    logging.info(f"[CONVERT] File size: {len(image_data)} bytes")

    tracemalloc.start()
    gc.collect()
    start_time = time.time()

    try:
        avif_data = convert_to_avif(image_data, file_type, image.filename)
    except Exception as e:
        logging.error(f"[CONVERT] Conversion failed: {str(e)}")
        tracemalloc.stop()
        raise HTTPException(status_code=500, detail="Conversion failed.")

    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_after = get_memory_info()
    logging.info(f"[CONVERT] Memory after conversion: {memory_after}")
    logging.info(f"[CONVERT] Peak memory during conversion: {peak / 1024 / 1024:.2f}MB")
    logging.info(f"[CONVERT] Conversion time: {end_time - start_time:.2f}s")

    base64_content = base64.b64encode(avif_data).decode('utf-8')

    return {
        "success": True,
        "metrics": {
            "memoryBeforeMB": memory_before,
            "memoryAfterMB": memory_after,
            "peakMemoryMB": round(peak / 1024 / 1024, 2),
            "conversionTimeSec": round(end_time - start_time, 2)
        },
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
