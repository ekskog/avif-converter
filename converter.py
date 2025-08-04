import subprocess
import tempfile
from pathlib import Path
import psutil
import os
import gc
import logging

def get_memory_usage():
    """Returns current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def convert_jpeg_to_avif(jpeg_data: bytes, original_filename: str = "image.jpg") -> bytes:
    """JPEG to AVIF conversion using avifenc directly"""
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

def convert_heic_to_avif_cli(heic_data: bytes, original_filename: str = "image.heic") -> bytes:
    """HEIC to AVIF conversion using intermediate JPEG"""
    with tempfile.TemporaryDirectory() as tmpdir:
        heic_path = Path(tmpdir) / "input.heic"
        jpeg_path = Path(tmpdir) / "intermediate.jpg"
        avif_path = Path(tmpdir) / "output.avif"

        heic_path.write_bytes(heic_data)

        try:
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", str(heic_path),
                "-q:v", "2", str(jpeg_path)
            ]
            subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
            logging.info(f"[CONVERTER] FFmpeg converted HEIC to JPEG")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] FFmpeg JPEG conversion failed:\n{e.stderr.decode(errors='ignore')}")
            raise RuntimeError("HEIC to JPEG conversion failed") from e

        try:
            avifenc_cmd = [
                "avifenc", "--speed", "6", "--jobs", "1",
                str(jpeg_path), str(avif_path)
            ]
            result = subprocess.run(avifenc_cmd, capture_output=True, text=True, check=True)
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed:\n{e.stderr.decode(errors='ignore')}")
            raise RuntimeError("JPEG to AVIF conversion failed") from e

        return avif_path.read_bytes()

def convert_to_avif(data: bytes, file_type: str, original_filename: str) -> bytes:
    """Unified conversion with detailed memory tracking"""
    logging.info(f"[CONVERTER] Processing file: {original_filename}")
    memory_start = get_memory_usage()
    print(f"[CONVERTER] Starting {file_type.upper()} conversion - Memory: {memory_start}MB")
    logging.info(f"[CONVERTER] Memory before conversion: {memory_start}MB")

    try:
        if file_type.lower() == "jpeg":
            result = convert_jpeg_to_avif(data, original_filename)
        elif file_type.lower() == "heic":
            result = convert_heic_to_avif_cli(data, original_filename)
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
