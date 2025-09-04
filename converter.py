import subprocess
import tempfile
from pathlib import Path
import psutil
import os
import gc
import logging
import traceback
import resource

def get_memory_usage():
    """Returns current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def get_system_memory():
    """Returns system memory info"""
    mem = psutil.virtual_memory()
    return {
        'total': round(mem.total / 1024 / 1024, 2),
        'available': round(mem.available / 1024 / 1024, 2),
        'percent': mem.percent,
        'used': round(mem.used / 1024 / 1024, 2)
    }

def get_memory_limit():
    """Get memory limit for current process"""
    try:
        # Get soft and hard limits
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        soft_mb = soft / 1024 / 1024 if soft != resource.RLIM_INFINITY else "unlimited"
        hard_mb = hard / 1024 / 1024 if hard != resource.RLIM_INFINITY else "unlimited"
        return {'soft': soft_mb, 'hard': hard_mb}
    except:
        return {'soft': 'unknown', 'hard': 'unknown'}

def log_memory_state(context: str):
    """Log comprehensive memory state"""
    process_mem = get_memory_usage()
    system_mem = get_system_memory()
    limits = get_memory_limit()
    
    logging.info(f"[MEMORY-{context}] Process: {process_mem}MB")
    logging.info(f"[MEMORY-{context}] System: {system_mem['used']}/{system_mem['total']}MB ({system_mem['percent']:.1f}% used, {system_mem['available']}MB available)")
    logging.info(f"[MEMORY-{context}] Limits: soft={limits['soft']}, hard={limits['hard']}")
    
    # Also print to stdout for immediate visibility
    print(f"[MEMORY-{context}] Process: {process_mem}MB | System: {system_mem['percent']:.1f}% used ({system_mem['available']}MB available)")

def get_file_size_mb(data: bytes) -> float:
    """Get file size in MB"""
    return round(len(data) / 1024 / 1024, 2)

def monitor_subprocess_memory(process_name: str, cmd: list, **kwargs):
    """Run subprocess with memory monitoring"""
    logging.info(f"[SUBPROCESS] Starting {process_name}: {' '.join(cmd)}")
    log_memory_state(f"PRE-{process_name}")
    
    try:
        # Start the process
        process = subprocess.Popen(cmd, **kwargs)
        
        # Monitor memory during execution
        max_memory = get_memory_usage()
        while process.poll() is None:
            current_memory = get_memory_usage()
            if current_memory > max_memory:
                max_memory = current_memory
            # Brief sleep to avoid overwhelming the system
            import time
            time.sleep(0.1)
        
        # Wait for completion and get result
        stdout, stderr = process.communicate()
        returncode = process.returncode
        
        log_memory_state(f"POST-{process_name}")
        logging.info(f"[SUBPROCESS] {process_name} peak memory: {max_memory}MB")
        logging.info(f"[SUBPROCESS] {process_name} return code: {returncode}")
        
        if returncode != 0:
            error_msg = stderr.decode(errors='ignore') if stderr else "Unknown error"
            logging.error(f"[SUBPROCESS] {process_name} failed: {error_msg}")
            raise subprocess.CalledProcessError(returncode, cmd, output=stdout, stderr=stderr)
        
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)
        
    except Exception as e:
        log_memory_state(f"ERROR-{process_name}")
        logging.error(f"[SUBPROCESS] {process_name} exception: {str(e)}")
        raise

def convert_jpeg_to_avif(jpeg_data: bytes, original_filename: str = "image.jpg") -> bytes:
    """JPEG to AVIF conversion using avifenc directly"""
    input_size = get_file_size_mb(jpeg_data)
    logging.info(f"[CONVERTER] JPEG input size: {input_size}MB")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.jpg"
        output_path = Path(tmpdir) / "output.avif"
        
        # Write input file and log memory impact
        log_memory_state("PRE-JPEG-WRITE")
        input_path.write_bytes(jpeg_data)
        log_memory_state("POST-JPEG-WRITE")
        
        # Clear the input data from memory to reduce peak usage
        del jpeg_data
        gc.collect()
        log_memory_state("POST-JPEG-GC")

        try:
            result = monitor_subprocess_memory("avifenc", [
                "avifenc", "--speed", "6", "--jobs", "1",
                str(input_path), str(output_path)
            ], capture_output=True, text=True, check=True)
            
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            if result.stderr:
                logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"[CONVERTER] avifenc failed: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                logging.error(f"[CONVERTER] avifenc stderr: {e.stderr}")
            raise

        # Read output and log memory impact
        log_memory_state("PRE-AVIF-READ")
        output_data = output_path.read_bytes()
        output_size = get_file_size_mb(output_data)
        logging.info(f"[CONVERTER] AVIF output size: {output_size}MB (compression: {(1-output_size/input_size)*100:.1f}%)")
        log_memory_state("POST-AVIF-READ")

        return output_data

def convert_heic_to_avif_cli(heic_data: bytes, original_filename: str = "image.heic") -> bytes:
    """HEIC to AVIF conversion using ImageMagick and avifenc"""
    input_size = get_file_size_mb(heic_data)
    logging.info(f"[CONVERTER] HEIC input size: {input_size}MB")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        heic_path = Path(tmpdir) / "input.heic"
        jpeg_path = Path(tmpdir) / "intermediate.jpg"
        avif_path = Path(tmpdir) / "output.avif"

        # Write HEIC file
        log_memory_state("PRE-HEIC-WRITE")
        heic_path.write_bytes(heic_data)
        log_memory_state("POST-HEIC-WRITE")
        
        # Clear input data early
        del heic_data
        gc.collect()
        log_memory_state("POST-HEIC-GC")

        try:
            # ImageMagick conversion
            result = monitor_subprocess_memory("ImageMagick", [
                "convert", str(heic_path), str(jpeg_path)
            ], capture_output=True, check=True)
            
            logging.info(f"[CONVERTER] ImageMagick converted HEIC to JPEG")
            
            # Check intermediate JPEG size
            if jpeg_path.exists():
                jpeg_size = get_file_size_mb(jpeg_path.read_bytes())
                logging.info(f"[CONVERTER] Intermediate JPEG size: {jpeg_size}MB")
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode(errors='ignore') if e.stderr else "Unknown error"
            logging.error(f"[CONVERTER] ImageMagick conversion failed: {error_msg}")
            raise RuntimeError("HEIC to JPEG conversion failed") from e

        try:
            # AVIF conversion
            result = run_with_memory_monitoring("avifenc", [
                "avifenc", "--speed", "6", "--jobs", "1",
                str(jpeg_path), str(avif_path)
            ], capture_output=True, text=True, check=True)
            
            logging.info(f"[CONVERTER] avifenc stdout: {result.stdout}")
            if result.stderr:
                logging.info(f"[CONVERTER] avifenc stderr: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if isinstance(e.stderr, str) else e.stderr.decode(errors='ignore') if e.stderr else "Unknown error"
            logging.error(f"[CONVERTER] avifenc failed: {error_msg}")
            raise RuntimeError("JPEG to AVIF conversion failed") from e

        # Read final output
        log_memory_state("PRE-FINAL-AVIF-READ")
        output_data = avif_path.read_bytes()
        output_size = get_file_size_mb(output_data)
        logging.info(f"[CONVERTER] Final AVIF size: {output_size}MB (compression: {(1-output_size/input_size)*100:.1f}%)")
        log_memory_state("POST-FINAL-AVIF-READ")

        return output_data

def convert_to_avif(data: bytes, file_type: str, original_filename: str) -> bytes:
    """Unified conversion with detailed memory tracking"""
    input_size = get_file_size_mb(data)
    logging.info(f"[CONVERTER] ===== Starting conversion =====")
    logging.info(f"[CONVERTER] File: {original_filename}")
    logging.info(f"[CONVERTER] Type: {file_type.upper()}")
    logging.info(f"[CONVERTER] Input size: {input_size}MB")
    
    # Log initial memory state
    log_memory_state("START")
    
    # Log memory limits and system state
    limits = get_memory_limit()
    system_mem = get_system_memory()
    logging.info(f"[CONVERTER] Memory limits: {limits}")
    logging.info(f"[CONVERTER] System memory: {system_mem}")
    
    try:
        if file_type.lower() == "jpeg":
            result = convert_jpeg_to_avif(data, original_filename)
        elif file_type.lower() == "heic":
            result = convert_heic_to_avif_cli(data, original_filename)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Final cleanup and reporting
        del data  # Explicit cleanup
        gc.collect()
        log_memory_state("SUCCESS")
        
        output_size = get_file_size_mb(result)
        logging.info(f"[CONVERTER] ===== Conversion successful =====")
        logging.info(f"[CONVERTER] Output size: {output_size}MB")
        logging.info(f"[CONVERTER] Overall compression: {(1-output_size/input_size)*100:.1f}%")

        return result
        
    except Exception as e:
        # Cleanup on error
        try:
            del data
        except:
            pass
        gc.collect()
        log_memory_state("FAILURE")
        
        # Log detailed error information
        logging.error(f"[CONVERTER] ===== Conversion failed =====")
        logging.error(f"[CONVERTER] Error: {str(e)}")
        logging.error(f"[CONVERTER] Error type: {type(e).__name__}")
        logging.error(f"[CONVERTER] Traceback: {traceback.format_exc()}")
        
        # Log system state at failure
        system_mem = get_system_memory()
        if system_mem['available'] < 100:  # Less than 100MB available
            logging.error(f"[CONVERTER] LOW MEMORY WARNING: Only {system_mem['available']}MB available")
        
        raise