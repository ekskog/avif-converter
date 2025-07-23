from fastapi import FastAPI, UploadFile, File, HTTPException
from converter import convert_to_avif
import psutil
import os

app = FastAPI()

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
    memory = get_memory_info()

    # Check for avifenc availability
    avifenc_available = False
    try:
        result = subprocess.run(["avifenc", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            avifenc_available = True
    except:
        pass

    is_healthy = avifenc_available

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "avif-converter",
        "memory": memory,
        "capabilities": {
            "avifenc": avifenc_available
        }
    }

@app.post("/convert")
async def convert_image(image: UploadFile = File(...)):
    memory_before = get_memory_info()
    print(f"[CONVERT] Starting conversion - Memory before: {memory_before}")

    if image.content_type not in ["image/jpeg", "image/heic"]:
        raise HTTPException(status_code=400, detail="Only JPEG and HEIC images are supported.")

    file_type = "jpeg" if image.content_type == "image/jpeg" else "heic"
    image_data = await image.read()

    try:
        avif_data = convert_to_avif(image_data, file_type, image.filename)
        memory_after = get_memory_info()
        print(f"[CONVERT] Conversion completed - Memory after: {memory_after}")
        return {
            "filename": image.filename,
            "file_type": file_type,
            "memory_before": memory_before,
            "memory_after": memory_after,
            "avif_data": avif_data
        }
    except Exception as e:
        print(f"[CONVERT] Conversion failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Conversion failed.")
