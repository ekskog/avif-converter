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
    """HEIC to AVIF conversion using ffmpeg and avifenc via CLI pipeline"""
    with tempfile.TemporaryDirectory() as tmpdir:
        heic_path = Path(tmpdir) / "input.heic"
        avif_path = Path(tmpdir) / "output.avif"

        heic_path.write_bytes(heic_data)

        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(heic_path),
            "-f", "yuv4mpegpipe", "-pix_fmt", "yuv420p", "-"
        ]

        avifenc_cmd = [
            "avifenc", "--stdin", "--output", str(avif_path), "--speed", "6"
        ]

        try:
            ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            avifenc = subprocess.run(avifenc_cmd, input=ffmpeg.stdout.read(), capture_output=True, check=True)
            ffmpeg.stdout.close()
            ffmpeg.wait()

            logging.info(f"[CONVERTER] avifenc stdout: {avifenc.stdout.decode()}")
            logging.info(f"[CONVERTER] avifenc stderr: {avifenc.stderr.decode()}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] HEIC conversion subprocess failed: {e.stderr}")
            raise
        except Exception as e:
            logging.error(f"[CONVERTER] Exception during HEIC conversion: {str(e)}")
            raise

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
