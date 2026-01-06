"""Music Foundation Model embedding generation (MERT/MuQ) with OpenL3 fallback."""
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Default MERT model name
MERT_MODEL_NAME = "m-a-p/MERT-v1-330M"

# Lazy imports for torch to avoid DLL errors on Windows
HAS_TORCH = False
HAS_TORCHAUDIO = False
HAS_TRANSFORMERS = False

try:
    import torch
    HAS_TORCH = True
except (ImportError, OSError) as e:
    logger.warning(f"torch not available: {e}. MERT/MuQ models will not be available.")
    HAS_TORCH = False

# Try to import MERT (Music Foundation Model) - only if torch is available
HAS_AMP = False
autocast = None  # Initialize to None, will be set if import succeeds
if HAS_TORCH:
    try:
        from transformers import AutoModel, AutoProcessor
        import torchaudio
        HAS_TORCHAUDIO = True
        HAS_TRANSFORMERS = True
        # Try to import AMP (may not be available in all PyTorch versions)
        try:
            from torch.amp import autocast  # PyTorch AMP for safe FP16 inference
            HAS_AMP = True
        except (ImportError, AttributeError):
            HAS_AMP = False
            autocast = None
            logger.warning("torch.cuda.amp.autocast not available - AMP disabled (will use FP32)")
    except (ImportError, OSError):
        HAS_TRANSFORMERS = False
        HAS_TORCHAUDIO = False

# Try to import openl3, with fallback if not available
try:
    import openl3
    HAS_OPENL3 = True
except ImportError:
    HAS_OPENL3 = False

if not HAS_TRANSFORMERS and not HAS_OPENL3:
    logger.warning("Neither transformers (for MERT) nor openl3 installed. Using fallback embedding method.")


class EmbeddingGenerator:
    """
    Generates embeddings using Music Foundation Models (MERT/MuQ) with OpenL3 fallback.
    
    Priority: MERT > MuQ > OpenL3 > librosa fallback
    """
    
    def __init__(
        self,
        embedding_dim: int = 512,
        sample_rate: int = 44100,
        model_type: str = "mert",  # "mert", "muq", "openl3", "auto"
        content_type: str = "music",
        input_repr: str = "mel256",
        device: Optional[str] = None,
        dtype: str = "float32",
        model_name: Optional[str] = None
    ):
        """
        Initialize embedding generator.
        
        Args:
            embedding_dim: Dimension of output embedding (default: 512)
            sample_rate: Target sample rate (default: 44100)
            model_type: Model to use ("mert", "muq", "openl3", "auto")
            content_type: Content type for OpenL3 ('music' or 'env')
            input_repr: Input representation for OpenL3 ('mel256' or 'linear')
            device: torch device ("cuda", "cpu", or None for auto)
            model_name: Optional MERT model name override
        """
        self.embedding_dim = embedding_dim
        self.sample_rate = sample_rate
        self.content_type = content_type
        self.input_repr = input_repr
        self.model_type = model_type
        self.model_name = model_name or MERT_MODEL_NAME
        
        if not HAS_TORCH:
            self.device = "cpu"
            logger.warning("PyTorch not available. Using CPU fallback and librosa embeddings.")
        elif device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Store dtype preference (float16 for speed, float32 for accuracy)
        self.dtype = dtype
        
        # Log device information for debugging
        if HAS_TORCH:
            logger.info(f"Device configuration: requested='{device}', actual='{self.device}'")
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                logger.info(f"CUDA device count: {torch.cuda.device_count()}")
                logger.info(f"CUDA device name: {torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else 'N/A'}")
        else:
            logger.warning("CUDA not available - using CPU (will be slow). Install PyTorch with CUDA support for GPU acceleration.")
        
        # Initialize models
        self.mert_model = None
        self.mert_processor = None
        self.muq_model = None
        self.muq_processor = None
        self.active_model = None
        self.active_model_name = None
        
        # Try to load models based on priority
        if model_type == "auto" or model_type == "mert":
            if self._load_mert():
                self.active_model_name = "mert"
                logger.info("Using MERT (Music Foundation Model) for embeddings")
            elif model_type == "mert":
                logger.warning("MERT requested but not available, falling back to next option")
        
        if (model_type == "auto" or model_type == "muq") and self.active_model is None:
            if self._load_muq():
                self.active_model_name = "muq"
                logger.info("Using MuQ (Music Foundation Model) for embeddings")
            elif model_type == "muq":
                logger.warning("MuQ requested but not available, falling back to next option")
        
        if (model_type == "auto" or model_type == "openl3") and self.active_model is None:
            if HAS_OPENL3:
                self.active_model_name = "openl3"
                logger.info("Using OpenL3 for embeddings")
            else:
                logger.warning("OpenL3 not available, using librosa fallback")
                self.active_model_name = "librosa"
        elif model_type == "openl3" and not HAS_OPENL3:
            logger.warning("OpenL3 requested but not available, using librosa fallback")
            self.active_model_name = "librosa"
        
        if self.active_model_name is None:
            self.active_model_name = "librosa"
            logger.warning("No embedding models available, using librosa fallback")
    
    def _load_mert(self) -> bool:
        """Load MERT model from Hugging Face."""
        if not HAS_TRANSFORMERS:
            return False
        
        try:
            # MERT model on Hugging Face
            # Try configured model first, then fallback variants
            model_names = [
                self.model_name,  # Use configured model name
                "m-a-p/MERT-v1-330M",  # MERT v1 330M parameters (fallback)
                "m-a-p/MERT-v1-95M",   # MERT v1 95M parameters (fallback)
            ]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_model_names = []
            for name in model_names:
                if name not in seen:
                    seen.add(name)
                    unique_model_names.append(name)
            
            for model_name in unique_model_names:
                try:
                    logger.info(f"Attempting to load MERT model: {model_name}")
                    self.mert_model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
                    self.mert_processor = AutoProcessor.from_pretrained(
                        model_name, 
                        trust_remote_code=True,
                        use_fast=False  # Maintain current slow processor behavior for consistency
                    )
                    logger.info("Using slow image processor (use_fast=False) to maintain consistent outputs")
                    self.mert_model.to(self.device)
                    self.mert_model.eval()
                    self.active_model = "mert"
                    
                    # Log MERT's required sampling rate
                    mert_sr = getattr(self.mert_processor, 'sampling_rate', None)
                    if hasattr(self.mert_processor, 'feature_extractor'):
                        mert_sr = getattr(self.mert_processor.feature_extractor, 'sampling_rate', None)
                    if mert_sr:
                        logger.info(f"MERT model requires sampling rate: {mert_sr} Hz")
                    
                    logger.info(f"✅ Successfully loaded MERT model: {model_name}")
                    return True
                except Exception as e:
                    logger.debug(f"Failed to load {model_name}: {e}")
                    continue
            
            logger.error("❌ Failed to load any MERT model variant")
            return False
        except Exception as e:
            logger.warning(f"Error loading MERT: {e}")
            return False
    
    def _load_muq(self) -> bool:
        """Load MuQ model from Hugging Face."""
        if not HAS_TRANSFORMERS:
            return False
        
        try:
            # MuQ model on Hugging Face (if available)
            # Note: MuQ may have different model names
            model_names = [
                "musicgen/musicgen-small",  # Example - adjust based on actual MuQ model
            ]
            
            for model_name in model_names:
                try:
                    logger.info(f"Attempting to load MuQ model: {model_name}")
                    # MuQ loading logic would go here
                    # This is a placeholder - adjust based on actual MuQ implementation
                    logger.warning("MuQ model loading not fully implemented yet")
                    return False
                except Exception as e:
                    logger.debug(f"Failed to load {model_name}: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.warning(f"Error loading MuQ: {e}")
            return False
    
    def _generate_mert_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Generate embedding using MERT model."""
        if not HAS_TORCH:
            raise ValueError("PyTorch not available. Cannot use MERT model.")
        if self.mert_model is None or self.mert_processor is None:
            raise ValueError("MERT model not loaded")
        
        import torch
        import torchaudio
        
        try:
            # Get MERT processor's required sampling rate (usually 24000)
            mert_sr = getattr(self.mert_processor, 'sampling_rate', 24000)
            if hasattr(self.mert_processor, 'feature_extractor'):
                mert_sr = getattr(self.mert_processor.feature_extractor, 'sampling_rate', 24000)
            
            logger.debug(f"MERT requires sampling rate: {mert_sr} Hz (input: {sr} Hz)")
            
            # Convert to tensor
            if isinstance(audio, np.ndarray):
                audio_tensor = torch.from_numpy(audio).float()
            else:
                audio_tensor = audio
            
            # Ensure 1D
            if len(audio_tensor.shape) > 1:
                audio_tensor = audio_tensor.squeeze()
            
            # Resample to MERT's required sampling rate (24000 Hz)
            if sr != mert_sr:
                resampler = torchaudio.transforms.Resample(sr, mert_sr)
                audio_tensor = resampler(audio_tensor)
                logger.debug(f"Resampled from {sr} Hz to {mert_sr} Hz (internal MERT processing only)")
            
            # Convert to numpy array (1D)
            audio_numpy = audio_tensor.numpy()
            
            # Process with MERT - use MERT's sampling rate
            inputs = self.mert_processor(
                raw_speech=audio_numpy,
                sampling_rate=mert_sr,  # Use MERT's required sampling rate
                return_tensors="pt"
            )
            
            inputs = {k: v.to(self.device).float() for k, v in inputs.items()}  # Ensure FP32 inputs
            
            # Generate embeddings with CUDA error handling and AMP (Automatic Mixed Precision)
            with torch.no_grad():
                try:
                    # Clear CUDA cache to prevent memory issues
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                    
                    # Use Automatic Mixed Precision (AMP) for safe FP16 inference on GPU
                    if self.device == "cuda" and HAS_AMP:
                        with autocast(device_type='cuda'):  # AMP automatically uses FP16 where safe, FP32 where needed
                            outputs = self.mert_model(**inputs)
                    else:
                        # CPU or AMP not available: use FP32
                        outputs = self.mert_model(**inputs)
                    
                    # Synchronize CUDA operations to catch errors early
                    if self.device == "cuda":
                        torch.cuda.synchronize()
                except RuntimeError as e:
                    if "CUDA" in str(e) or "device-side" in str(e).lower():
                        logger.error(f"CUDA error during inference: {e}")
                        # Clear cache and retry once (without AMP as fallback)
                        if self.device == "cuda":
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                            # Retry without AMP as fallback
                            try:
                                logger.warning("Retrying inference without AMP as fallback")
                                outputs = self.mert_model(**inputs)
                            except Exception as retry_e:
                                logger.error(f"Retry without AMP also failed: {retry_e}")
                                raise
                        else:
                            raise
                    else:
                        raise
                # Extract embeddings (adjust based on MERT output structure)
                if hasattr(outputs, 'last_hidden_state'):
                    embeddings = outputs.last_hidden_state
                elif hasattr(outputs, 'pooler_output'):
                    embeddings = outputs.pooler_output
                else:
                    embeddings = outputs[0]
                
                # Average over time dimension if needed
                if len(embeddings.shape) > 2:
                    embeddings = embeddings.mean(dim=1)
                
                # Get first (and only) batch item
                if len(embeddings.shape) > 1:
                    embeddings = embeddings[0]
                
                emb = embeddings.cpu().numpy()
            
            # Ensure correct dimension
            if len(emb) != self.embedding_dim:
                if len(emb) > self.embedding_dim:
                    emb = emb[:self.embedding_dim]
                else:
                    emb = np.pad(emb, (0, self.embedding_dim - len(emb)), mode='constant')
            
            # L2 normalize
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            
            # Always use FP32 for output embeddings (FAISS requires FP32)
            # FP16 is only used internally during model inference via AMP
            return emb.astype(np.float32)
        
        except Exception as e:
            logger.error(f"Error generating MERT embedding: {e}")
            raise
    
    def generate_embedding(self, audio_path: Path) -> np.ndarray:
        """
        Generate embedding for a single audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Normalized embedding vector (embedding_dim,)
        """
        try:
            # Load and preprocess audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            
            # Generate embedding based on active model
            if self.active_model_name == "mert" and self.mert_model is not None:
                emb = self._generate_mert_embedding(y, sr)
            elif self.active_model_name == "muq" and self.muq_model is not None:
                # MuQ embedding generation (to be implemented)
                logger.warning("MuQ embedding not fully implemented, using fallback")
                emb = self._generate_openl3_embedding(y, sr) if HAS_OPENL3 else self._generate_librosa_embedding(y, sr)
            elif self.active_model_name == "openl3" and HAS_OPENL3:
                emb = self._generate_openl3_embedding(y, sr)
            else:
                # Fallback to librosa features
                emb = self._generate_librosa_embedding(y, sr)
            
            return emb
            
        except Exception as e:
            logger.error(f"Error generating embedding for {audio_path}: {e}")
            raise
    
    def _generate_openl3_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Generate embedding using OpenL3."""
        if not HAS_OPENL3:
            raise ValueError("OpenL3 not available")
        
        emb, _ = openl3.get_audio_embedding(
            audio,
            sr=sr,
            model=self.content_type,
            input_repr=self.input_repr,
            embedding_size=self.embedding_dim,
            center=True,
            hop_size=0.1,
            verbose=False
        )
        
        # Average over time frames to get single vector
        if len(emb.shape) > 1:
            emb = np.mean(emb, axis=0)
        
        # Ensure correct dimension
        if len(emb) != self.embedding_dim:
            if len(emb) > self.embedding_dim:
                emb = emb[:self.embedding_dim]
            else:
                emb = np.pad(emb, (0, self.embedding_dim - len(emb)), mode='constant')
        
        # L2 normalize
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        
        # Always use FP32 for output embeddings (FAISS requires FP32)
        # FP16 is only used internally during model inference via AMP
        return emb.astype(np.float32)
    
    def _generate_librosa_embedding(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Generate embedding using librosa features (fallback)."""
        # Extract mel spectrogram features
        mel_spec = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_mels=128, fmax=8000
        )
        # Flatten and take mean
        emb = np.mean(mel_spec, axis=1)
        # Pad or truncate to target dimension
        if len(emb) > self.embedding_dim:
            emb = emb[:self.embedding_dim]
        else:
            emb = np.pad(emb, (0, self.embedding_dim - len(emb)), mode='constant')
        
        # L2 normalize
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        
        # Always use FP32 for output embeddings (FAISS requires FP32)
        # FP16 is only used internally during model inference via AMP
        return emb.astype(np.float32)
    
    def generate_embeddings_batch(
        self,
        audio_paths: List[Path],
        batch_size: int = 32
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple audio files.
        
        Args:
            audio_paths: List of paths to audio files
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # For MERT, we can do actual batching
        if self.active_model_name == "mert" and self.mert_model is not None:
            # Batch processing for MERT
            for i in range(0, len(audio_paths), batch_size):
                batch_paths = audio_paths[i:i+batch_size]
                batch_embeddings = self._generate_mert_batch(batch_paths)
                embeddings.extend(batch_embeddings)
        else:
            # Sequential processing for other models
            for path in audio_paths:
                try:
                    emb = self.generate_embedding(path)
                    embeddings.append(emb)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for {path}: {e}")
                    embeddings.append(np.zeros(self.embedding_dim, dtype=np.float32))
        
        return embeddings
    
    def _generate_mert_batch(self, audio_paths: List[Path]) -> List[np.ndarray]:
        """Generate MERT embeddings in batch."""
        # Get MERT processor's required sampling rate (usually 24000)
        mert_sr = getattr(self.mert_processor, 'sampling_rate', 24000)
        if hasattr(self.mert_processor, 'feature_extractor'):
            mert_sr = getattr(self.mert_processor.feature_extractor, 'sampling_rate', 24000)
        
        logger.debug(f"MERT batch processing with sampling rate: {mert_sr} Hz")
        
        # Load all audio files and resample to MERT's required rate
        audio_list = []
        for path in audio_paths:
            y, sr = librosa.load(path, sr=None, mono=True)  # Load at original rate first
            
            # Resample to MERT's required sampling rate
            if sr != mert_sr:
                y = librosa.resample(y, orig_sr=sr, target_sr=mert_sr)
            
            audio_list.append(y)
        
        # Process batch
        try:
            # Convert to list of numpy arrays for MERT processor
            audio_numpy_list = [audio for audio in audio_list]
            
            # Process with MERT - use MERT's sampling rate
            inputs = self.mert_processor(
                raw_speech=audio_numpy_list,
                sampling_rate=mert_sr,  # Use MERT's required sampling rate
                return_tensors="pt"
            )
            
            inputs = {k: v.to(self.device).float() for k, v in inputs.items()}  # Ensure FP32 inputs
            
            import torch
            with torch.no_grad():
                try:
                    # Clear CUDA cache to prevent memory issues
                    if self.device == "cuda":
                        torch.cuda.empty_cache()
                    
                    # Use Automatic Mixed Precision (AMP) for safe FP16 batch inference on GPU
                    if self.device == "cuda" and HAS_AMP:
                        with autocast(device_type='cuda'):  # AMP automatically uses FP16 where safe, FP32 where needed
                            outputs = self.mert_model(**inputs)
                    else:
                        # CPU or AMP not available: use FP32
                        outputs = self.mert_model(**inputs)
                    
                    # Synchronize CUDA operations to catch errors early
                    if self.device == "cuda":
                        torch.cuda.synchronize()
                except RuntimeError as e:
                    if "CUDA" in str(e) or "device-side" in str(e).lower():
                        logger.error(f"CUDA error during batch inference: {e}")
                        # Clear cache and retry once (without AMP as fallback)
                        if self.device == "cuda":
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                            # Retry without AMP as fallback
                            try:
                                logger.warning("Retrying batch inference without AMP as fallback")
                                outputs = self.mert_model(**inputs)
                            except Exception as retry_e:
                                logger.error(f"Retry without AMP also failed: {retry_e}")
                                raise
                        else:
                            raise
                    else:
                        raise
                if hasattr(outputs, 'last_hidden_state'):
                    embeddings = outputs.last_hidden_state
                elif hasattr(outputs, 'pooler_output'):
                    embeddings = outputs.pooler_output
                else:
                    embeddings = outputs[0]
                
                # Average over time dimension
                if len(embeddings.shape) > 2:
                    embeddings = embeddings.mean(dim=1)
                
                embeddings = embeddings.cpu().numpy()
            
            # Process each embedding
            results = []
            for emb in embeddings:
                if len(emb) != self.embedding_dim:
                    if len(emb) > self.embedding_dim:
                        emb = emb[:self.embedding_dim]
                    else:
                        emb = np.pad(emb, (0, self.embedding_dim - len(emb)), mode='constant')
                
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                
                # Always use FP32 for output embeddings (FAISS requires FP32)
                # FP16 is only used internally during model inference via AMP
                results.append(emb.astype(np.float32))
            
            return results
        except Exception as e:
            logger.error(f"Error in MERT batch processing: {e}")
            # Fallback to individual processing
            return [self.generate_embedding(path) for path in audio_paths]
    
    def save_embedding(self, embedding: np.ndarray, output_path: Path):
        """Save embedding to disk as .npy file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(output_path, embedding)
    
    def load_embedding(self, embedding_path: Path) -> np.ndarray:
        """Load embedding from disk."""
        return np.load(embedding_path)
    
    def get_model_info(self) -> Dict:
        """Get information about the active model."""
        return {
            "active_model": self.active_model_name,
            "embedding_dim": self.embedding_dim,
            "sample_rate": self.sample_rate,
            "device": self.device,
            "has_mert": self.mert_model is not None,
            "has_muq": self.muq_model is not None,
            "has_openl3": HAS_OPENL3
        }

