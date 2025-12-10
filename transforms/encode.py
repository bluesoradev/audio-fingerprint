"""Audio re-encoding transformations."""
import logging
import subprocess
from pathlib import Path
import soundfile as sf

logger = logging.getLogger(__name__)


def re_encode(
    input_path: Path,
    codec: str,
    bitrate: str,
    out_path: Path,
    **kwargs
) -> Path:
    """
    Re-encode audio through codec (introduces compression artifacts).
    
    Args:
        input_path: Input audio file
        codec: Codec name ("mp3", "aac", "opus", etc.)
        bitrate: Bitrate string (e.g., "128k", "192k", "320k")
        out_path: Output file path
        **kwargs: Additional ffmpeg parameters
        
    Returns:
        Path to output file
    """
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use ffmpeg for encoding
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-acodec", codec,
            "-b:a", bitrate,
            "-y",  # Overwrite output
            str(out_path)
        ]
        
        # Add any extra kwargs as ffmpeg args
        for key, value in kwargs.items():
            cmd.extend([f"-{key}", str(value)])
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.debug(f"Re-encoded {input_path} -> {out_path} ({codec} @ {bitrate})")
        return out_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg encoding failed: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg.")
        raise
    except Exception as e:
        logger.error(f"Re-encoding failed: {e}")
        raise


def re_encode_pydub(
    input_path: Path,
    codec: str,
    bitrate: str,
    out_path: Path
) -> Path:
    """
    Alternative re-encoding using pydub (requires ffmpeg).
    Fallback if direct ffmpeg call fails.
    """
    try:
        from pydub import AudioSegment
        
        # Load audio
        audio = AudioSegment.from_file(str(input_path))
        
        # Determine format and parameters
        format_map = {
            "mp3": "mp3",
            "aac": "aac",
            "opus": "opus"
        }
        
        fmt = format_map.get(codec.lower(), "mp3")
        
        # Export with bitrate
        out_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(str(out_path), format=fmt, bitrate=bitrate)
        
        logger.debug(f"Re-encoded {input_path} -> {out_path} ({codec} @ {bitrate})")
        return out_path
        
    except ImportError:
        logger.error("pydub not available. Install with: pip install pydub")
        raise
    except Exception as e:
        logger.error(f"Pydub re-encoding failed: {e}")
        raise
