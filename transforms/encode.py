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
        Path to output file (with correct extension based on codec)
    """
    try:
        # Map codec names to file extensions
        extension_map = {
            "mp3": ".mp3",
            "aac": ".m4a",  # AAC typically uses .m4a container
            "ogg": ".ogg",
            "opus": ".opus",
            "flac": ".flac",
            "wav": ".wav"
        }
        
        # Get correct extension for the codec
        codec_lower = codec.lower()
        correct_ext = extension_map.get(codec_lower, ".mp3")  # Default to .mp3 if unknown
        
        # Update output path extension if it doesn't match the codec
        if out_path.suffix.lower() != correct_ext:
            out_path = out_path.with_suffix(correct_ext)
            logger.info(f"[Re-encode] Adjusted output extension to {correct_ext} for codec {codec}")
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Map codec names to ffmpeg codec names
        codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "ogg": "libvorbis",  # OGG container uses Vorbis codec
            "opus": "libopus",
            "flac": "flac"
        }
        
        ffmpeg_codec = codec_map.get(codec_lower, codec_lower)
        
        logger.info(f"[Re-encode] Encoding {input_path} -> {out_path} using codec={codec} (ffmpeg: {ffmpeg_codec}) @ {bitrate}")
        
        # Use ffmpeg for encoding
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-acodec", ffmpeg_codec,
            "-b:a", bitrate,
            "-y",  # Overwrite output
            str(out_path)
        ]
        
        # Add any extra kwargs as ffmpeg args
        for key, value in kwargs.items():
            cmd.extend([f"-{key}", str(value)])
        
        logger.info(f"[Re-encode] Running command: {' '.join(cmd)}")
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not out_path.exists():
            raise Exception(f"Output file was not created: {out_path}")
        
        file_size = out_path.stat().st_size
        logger.info(f"[Re-encode] Success! Output: {out_path} ({file_size} bytes)")
        
        logger.debug(f"Re-encoded {input_path} -> {out_path} ({codec} @ {bitrate})")
        return out_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"[Re-encode] ffmpeg encoding failed: {e.stderr}")
        logger.error(f"[Re-encode] Command: {' '.join(cmd) if 'cmd' in locals() else 'N/A'}")
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
