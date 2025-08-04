import subprocess
import tempfile
from pathlib import Path
import psutil
import os
import gc
from PIL import Image
import pillow_heif
import logging

# 🔧 Make logging print to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# 🚫 Disable thumbnails to reduce memory usage
pillow_heif.register_heif_opener(thumbnails=False)

def get_memory_usage():
    """Returns current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def convert_heic_to_avif(heic_data: bytes, original_filename: str = "image.heic") -> bytes:
    """Convert HEIC to AVIF using Pillow and avifenc"""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.heic"
        jpeg_path = Path(tmpdir) / "intermediate.jpg"
        output_path = Path(tmpdir) / "output.avif"

        input_path.write_bytes(heic_data)

        image = Image.open(input_path)
        width, height = image.size
        logging.info(f"[CONVERTER] Image dimensions: {width}x{height}")
        image.save(jpeg_path, format="JPEG")
        image.close()

        try:
            result = subprocess.run([
                "avifenc", "--speed", "6", "--jobs", "1",
                str(jpeg_path), str(output_path)
            ], capture_output=True, text=True, check=True)
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed: {e.stderr}")
            raise

        return output_path.read_bytes()

def convert_jpeg_to_avif(jpeg_data: bytes, original_filename: str = "image.jpg") -> bytes:
    """JPEG to AVIF conversion using avifenc"""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.jpg"
        output_path = Path(tmpdir) / "output.avif"
        input_path.write_bytes(jpeg_data)

        try:
            result = subprocess.run([
                "avifenc", "--speed", "6", "--jobs", "1",
                str(input_path), str(output_path)
            ], capture_output=True, text=True, check=True)
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed: {e.stderr}")
            raise

        return output_path.read_bytes()

def convert_to_avif(data: bytes, file_type: str, original_filename: str) -> bytes:
    """Unified conversion with detailed memory tracking"""
    logging.info(f"[CONVERTER] Processing file: {original_filename}")
    memory_start = get_memory_usage()
    print(f"[CONVERTER] Starting {file_type.upper()} conversion - Memory: {memory_start}MB")
    logging.info(f"[CONVERTER] Memory before conversion: {memory_start}MB")

    try:
        if file_type.lower() == "heic":
            result = convert_heic_to_avif(data, original_filename)
        elif file_type.lower() == "jpeg":
            result = convert_jpeg_to_avif(data, original_filename)
        else:
            raise ValueError("Unsupported file type")

        gc.collect()
        memory_end = get_memory_usage()
        print(f"[CONVERTER] Memory after conversion: {memory_end}MB | Δ {memory_end - memory_start:+.2f}MB")
        logging.info(f"[CONVERTER] Memory after conversion: {memory_end}MB")
        logging.info(f"[CONVERTER] Memory delta: {memory_end - memory_start:+.2f}MB")

        return result
    except Exception as e:
        gc.collect()
        memory_error = get_memory_usage()
        logging.error(f"[CONVERTER] Conversion failed: {str(e)}")
        logging.error(f"[CONVERTER] Memory after failure: {memory_error}MB")
        raise
