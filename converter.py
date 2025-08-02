import subprocess
import tempfile
from pathlib import Path
import psutil
import os
import gc
from PIL import Image
import pillow_heif
import logging

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def convert_heic_to_avif(heic_data: bytes, original_filename: str = "image.heic") -> bytes:
    """Convert HEIC to AVIF using Pillow and avifenc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.heic"
        output_path = Path(tmpdir) / "output.avif"

        # Write HEIC data to a temporary file
        input_path.write_bytes(heic_data)

        # Convert HEIC to JPEG using Pillow
        image = Image.open(input_path)
        jpeg_path = Path(tmpdir) / "intermediate.jpg"
        image.save(jpeg_path, format="JPEG")

        # Convert JPEG to AVIF using avifenc
        try:
            result = subprocess.run([
                "avifenc", str(jpeg_path), str(output_path)
            ], capture_output=True, text=True, check=True)
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed with error: {e.stderr}")
            raise

        return output_path.read_bytes()

def convert_jpeg_to_avif(jpeg_data: bytes, original_filename: str = "image.jpg") -> bytes:
    """Convert JPEG to AVIF using avifenc."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.jpg"
        output_path = Path(tmpdir) / "output.avif"

        # Write JPEG data to a temporary file
        input_path.write_bytes(jpeg_data)

        # Convert JPEG to AVIF using avifenc
        try:
            result = subprocess.run([
                "avifenc", str(input_path), str(output_path)
            ], capture_output=True, text=True, check=True)
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed with error: {e.stderr}")
            raise

        return output_path.read_bytes()

def convert_to_avif(data: bytes, file_type: str, original_filename: str) -> bytes:
    """Unified function to convert HEIC or JPEG to AVIF."""
    memory_start = get_memory_usage()
    logging.info(f"[CONVERTER] Starting {file_type.upper()} to AVIF conversion - Memory: {memory_start}MB")
    logging.info(f"[CONVERTER] Input data size: {len(data)} bytes")
    logging.info(f"[CONVERTER] Original filename: {original_filename}")

    try:
        if file_type.lower() == "heic":
            result = convert_heic_to_avif(data, original_filename)
        elif file_type.lower() == "jpeg":
            result = convert_jpeg_to_avif(data, original_filename)
        else:
            raise ValueError("Unsupported file type")

        gc.collect()
        memory_end = get_memory_usage()
        logging.info(f"[CONVERTER] Conversion completed - Memory: {memory_end}MB (delta: {memory_end - memory_start:+.2f}MB)")

        return result
    except Exception as e:
        gc.collect()
        memory_error = get_memory_usage()
        logging.error(f"[CONVERTER] Conversion failed - Memory after cleanup: {memory_error}MB")
        raise e
