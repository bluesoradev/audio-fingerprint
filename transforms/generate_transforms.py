"""Generate transformed audio files from manifest according to test matrix."""
import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List
import yaml
import pandas as pd
from tqdm import tqdm

from .pitch import pitch_shift
from .speed import time_stretch, speed_change
from .encode import re_encode
from .chop import slice_chop
from .overlay import overlay_vocals
from .noise import add_noise
from .eq import (
    high_pass_filter,
    low_pass_filter,
    boost_highs,
    boost_lows,
    telephone_filter
)
from .dynamics import (
    apply_compression,
    apply_limiting,
    apply_multiband_compression
)
from .chain import combine_chain
from .crop import crop_10_seconds, crop_5_seconds, crop_middle_segment, crop_end_segment
from .reverb import apply_reverb
from .embedded_sample import embedded_sample
from .song_a_in_song_b import song_a_in_song_b

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_transform_id(orig_id: str, transform_type: str, params: Dict, seed: int = None) -> str:
    """Generate deterministic ID for transformed file."""
    # Sanitize parameter values to remove filesystem-invalid characters
    sanitized_params = {}
    for k, v in params.items():
        if v is None:
            safe_value = 'None'
        else:
            # Replace filesystem-invalid characters with underscore
            safe_value = str(v).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        sanitized_params[k] = safe_value
    
    param_str = "_".join(f"{k}_{v}" for k, v in sorted(sanitized_params.items()))
    if seed is not None:
        param_str += f"_seed_{seed}"
    transform_id = f"{orig_id}__{transform_type}__{param_str}"
    
    # Truncate if too long (200 chars leaves room for path prefix and .wav extension)
    MAX_FILENAME_LENGTH = 200
    if len(transform_id) > MAX_FILENAME_LENGTH:
        # Create hash of full transform_id for determinism
        hash_suffix = hashlib.md5(transform_id.encode("utf-8")).hexdigest()[:8]
        # Keep first part + hash
        prefix_length = MAX_FILENAME_LENGTH - len(hash_suffix) - 1  # -1 for underscore
        transform_id = transform_id[:prefix_length] + "_" + hash_suffix
    
    return transform_id


def generate_transforms(
    manifest_path: Path,
    test_matrix_path: Path,
    output_dir: Path,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Generate all transformed audio files according to test matrix.
    
    Returns:
        DataFrame with transform manifest
    """
    import numpy as np
    np.random.seed(random_seed)
    
    # Validate manifest file exists and is not empty
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    # Check if file is empty
    file_size = manifest_path.stat().st_size
    if file_size == 0:
        raise ValueError(
            f"Manifest file is empty: {manifest_path}\n"
            f"The manifest file exists but contains no data.\n"
            f"Cannot generate transforms without source files.\n\n"
            f"Please ensure audio files exist and the manifest is properly populated."
        )
    
    # Load files manifest with exception handling
    try:
        files_df = pd.read_csv(manifest_path)
        if len(files_df) == 0:
            raise ValueError(
                f"Manifest file has no data rows: {manifest_path}\n"
                f"The file exists but contains only headers or is empty.\n"
                f"Cannot generate transforms without source files."
            )
    except pd.errors.EmptyDataError as e:
        raise ValueError(
            f"Manifest file is empty or corrupted: {manifest_path}\n"
            f"Cannot generate transforms without source files.\n"
            f"Please ensure audio files exist and recreate the manifest."
        ) from e
    
    logger.info(f"Loaded {len(files_df)} original files from {manifest_path}")
    logger.info(f"Manifest columns: {list(files_df.columns)}")
    logger.info(f"First few rows:\n{files_df.head()}")
    
    # Load test matrix
    logger.info(f"Loading test matrix from {test_matrix_path}")
    with open(test_matrix_path, 'r') as f:
        test_config = yaml.safe_load(f)
    
    transform_configs = test_config.get("transforms", {})
    global_seed = test_config.get("global", {}).get("random_seed", random_seed)
    
    logger.info(f"Found {len(transform_configs)} transform types in config")
    enabled_transforms = [t for t, cfg in transform_configs.items() if cfg.get("enabled", False)]
    logger.info(f"Enabled transforms: {enabled_transforms}")
    
    output_dir = Path(output_dir)
    transformed_dir = output_dir / "transformed"
    transformed_dir.mkdir(parents=True, exist_ok=True)
    
    transform_records = []
    
    # Iterate over original files
    for _, file_row in tqdm(files_df.iterrows(), total=len(files_df), desc="Processing originals"):
        orig_id = file_row["id"]
        # Handle both "file_path" and "path" column names for compatibility
        orig_path_str = file_row.get("file_path") or file_row.get("path")
        if not orig_path_str:
            logger.error(f"Manifest row {orig_id} missing 'file_path' or 'path' column. Available columns: {list(file_row.index)}")
            continue
        
        orig_path = Path(orig_path_str)
        
        # Resolve relative paths relative to current working directory
        if not orig_path.is_absolute():
            # Try to resolve relative to current directory
            if not orig_path.exists():
                # If still not found, try resolving relative to output_dir parent (project root)
                potential_path = output_dir.parent / orig_path
                if potential_path.exists():
                    orig_path = potential_path
                    logger.info(f"Resolved relative path: {orig_path_str} -> {orig_path}")
        
        if not orig_path.exists():
            logger.warning(f"Original file not found: {orig_path} (resolved from: {orig_path_str})")
            continue
        
        logger.info(f"Processing original file: {orig_id} -> {orig_path}")
        
        # Apply each enabled transform
        for transform_type, transform_config in transform_configs.items():
            if not transform_config.get("enabled", False):
                continue
            
            # Handle different transform structures
            if transform_type == "combine_chain":
                # Handle chains
                chains = transform_config.get("chains", [])
                for chain_def in chains:
                    chain_name = chain_def.get("name", "chain")
                    severity = chain_def.get("severity", "moderate")
                    transforms = chain_def.get("transforms", [])
                    
                    # Generate transform ID
                    transform_id = generate_transform_id(
                        orig_id,
                        f"chain_{chain_name}",
                        {"severity": severity}
                    )
                    out_path = transformed_dir / f"{transform_id}.wav"
                    
                    # Defensive check: ensure path is not too long
                    MAX_PATH_LENGTH = 250
                    if len(str(out_path)) > MAX_PATH_LENGTH:
                        filename = out_path.name
                        if len(filename) > 200:
                            import hashlib
                            hash_suffix = hashlib.md5(filename.encode("utf-8")).hexdigest()[:8]
                            prefix_length = 200 - len(hash_suffix) - 1
                            truncated_filename = filename[:prefix_length] + "_" + hash_suffix
                            out_path = out_path.parent / truncated_filename
                            transform_id = truncated_filename.replace(".wav", "")
                    
                    # Check if transformed file already exists
                    if out_path.exists():
                        logger.info(f"✓ Skipping {transform_id} - file already exists: {out_path}")
                        transform_records.append({
                            "orig_id": orig_id,
                            "transformed_id": transform_id,
                            "transform_type": transform_type,
                            "transform_name": chain_name,
                            "severity": severity,
                            "params": json.dumps({"transforms": transforms}),
                            "output_path": str(out_path),
                            "seed": global_seed,
                        })
                        continue  # Skip generation, file already exists
                    
                    # Generate only if file doesn't exist
                    try:
                        combine_chain(orig_path, transforms, out_path)
                        
                        transform_records.append({
                            "orig_id": orig_id,
                            "transformed_id": transform_id,
                            "transform_type": transform_type,
                            "transform_name": chain_name,
                            "severity": severity,
                            "params": json.dumps({"transforms": transforms}),
                            "output_path": str(out_path),
                            "seed": global_seed,
                        })
                    except Exception as e:
                        logger.error(f"Failed to apply chain {chain_name} to {orig_id}: {e}")
                
            else:
                # Handle single-parameter transforms
                parameters = transform_config.get("parameters", [])
                
                for param_set in parameters:
                    # Create a copy to avoid modifying the original dict
                    param_set = param_set.copy()
                    
                    # Extract severity if present (metadata, not a function parameter)
                    severity = param_set.pop("severity", "moderate")
                    
                    # Remove description (metadata only, not a function parameter)
                    description = param_set.pop("description", None)
                    
                    # Handle parameter name mappings for specific transforms
                    # Store original overlay_path value for ID generation before mapping
                    original_overlay_path = None
                    had_overlay_path = False
                    if transform_type == "overlay_vocals" or transform_type.startswith("overlay_vocals"):
                        # Map overlay_path to vocal_file (function expects vocal_file)
                        if "overlay_path" in param_set:
                            overlay_path_val = param_set.pop("overlay_path")
                            original_overlay_path = overlay_path_val
                            had_overlay_path = True
                            # Convert None to None, or string path to Path object
                            if overlay_path_val is not None and overlay_path_val != "null":
                                param_set["vocal_file"] = Path(overlay_path_val) if isinstance(overlay_path_val, str) else overlay_path_val
                            # If overlay_path is None/null, vocal_file defaults to None in function signature
                            # Don't add vocal_file=None to param_set, let function use default
                    
                    # Generate transform ID (use param_set with description restored for ID generation)
                    # For overlay_vocals, use original overlay_path name in ID for consistency with config
                    param_set_for_id = param_set.copy()
                    if description:
                        param_set_for_id["description"] = description
                    # Restore overlay_path for ID generation if it was mapped (even if None)
                    if transform_type == "overlay_vocals" or transform_type.startswith("overlay_vocals"):
                        if had_overlay_path:
                            # Remove vocal_file if it was added, restore overlay_path
                            param_set_for_id.pop("vocal_file", None)
                            param_set_for_id["overlay_path"] = original_overlay_path
                    transform_id = generate_transform_id(orig_id, transform_type, param_set_for_id)
                    out_path = transformed_dir / f"{transform_id}.wav"
                    
                    # Defensive check: ensure path is not too long
                    MAX_PATH_LENGTH = 250
                    if len(str(out_path)) > MAX_PATH_LENGTH:
                        filename = out_path.name
                        if len(filename) > 200:
                            import hashlib
                            hash_suffix = hashlib.md5(filename.encode("utf-8")).hexdigest()[:8]
                            prefix_length = 200 - len(hash_suffix) - 1
                            truncated_filename = filename[:prefix_length] + "_" + hash_suffix
                            out_path = out_path.parent / truncated_filename
                            transform_id = truncated_filename.replace(".wav", "")
                    
                    # Check if transformed file already exists
                    if out_path.exists():
                        logger.info(f"✓ Skipping {transform_id} - file already exists: {out_path}")
                        transform_records.append({
                            "orig_id": orig_id,
                            "transformed_id": transform_id,
                            "transform_type": transform_type,
                            "transform_name": description or transform_type,
                            "severity": severity,
                            "params": json.dumps(param_set_for_id),
                            "output_path": str(out_path),
                            "seed": global_seed,
                        })
                        continue  # Skip generation, file already exists
                    
                    # Generate only if file doesn't exist
                    try:
                        # Apply transform based on type
                        if transform_type == "pitch_shift":
                            pitch_shift(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "time_stretch":
                            time_stretch(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "re_encode":
                            re_encode(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "slice_chop":
                            slice_chop(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "add_noise":
                            add_noise(orig_path, random_seed=global_seed, **param_set, out_path=out_path)
                        elif transform_type == "overlay_vocals" or transform_type.startswith("overlay_vocals"):
                            overlay_vocals(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "high_pass_filter":
                            high_pass_filter(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "low_pass_filter":
                            low_pass_filter(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "boost_highs":
                            boost_highs(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "boost_lows":
                            boost_lows(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "telephone_filter":
                            telephone_filter(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "apply_compression":
                            apply_compression(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "apply_limiting":
                            apply_limiting(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "apply_multiband_compression":
                            apply_multiband_compression(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "speed_change":
                            speed_change(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "apply_reverb":
                            apply_reverb(orig_path, **param_set, out_path=out_path)
                        elif transform_type == "crop_10_seconds":
                            crop_10_seconds(orig_path, out_path=out_path)
                        elif transform_type == "crop_5_seconds":
                            crop_5_seconds(orig_path, out_path=out_path)
                        elif transform_type == "crop_middle_segment":
                            duration = param_set.pop("duration", 10.0)
                            crop_middle_segment(orig_path, duration=duration, out_path=out_path)
                        elif transform_type == "crop_end_segment":
                            duration = param_set.pop("duration", 10.0)
                            crop_end_segment(orig_path, duration=duration, out_path=out_path)
                        elif transform_type == "embedded_sample":
                            # Requires sample_path and background_path
                            sample_path_str = param_set.pop("sample_path", None)
                            background_path_str = param_set.pop("background_path", None)
                            if not sample_path_str or not background_path_str:
                                logger.warning(f"embedded_sample requires sample_path and background_path, skipping {orig_id}")
                                continue
                            sample_path = Path(sample_path_str) if not Path(sample_path_str).is_absolute() else Path(sample_path_str)
                            background_path = Path(background_path_str) if not Path(background_path_str).is_absolute() else Path(background_path_str)
                            # Resolve relative paths
                            if not sample_path.is_absolute():
                                sample_path = output_dir.parent / sample_path
                            if not background_path.is_absolute():
                                background_path = output_dir.parent / background_path
                            if not sample_path.exists() or not background_path.exists():
                                logger.warning(f"Sample or background file not found for embedded_sample, skipping {orig_id}")
                                continue
                            embedded_sample(
                                sample_path=sample_path,
                                background_path=background_path,
                                out_path=out_path,
                                **param_set
                            )
                        elif transform_type == "song_a_in_song_b":
                            # Song A is orig_path, Song B base is optional
                            song_b_base_path_str = param_set.pop("song_b_base_path", None)
                            song_b_base_path = None
                            if song_b_base_path_str:
                                song_b_base_path = Path(song_b_base_path_str) if not Path(song_b_base_path_str).is_absolute() else Path(song_b_base_path_str)
                                if not song_b_base_path.is_absolute():
                                    song_b_base_path = output_dir.parent / song_b_base_path
                                if not song_b_base_path.exists():
                                    logger.warning(f"Song B base file not found, will generate synthetic background for {orig_id}")
                                    song_b_base_path = None
                            song_a_in_song_b(
                                song_a_path=orig_path,
                                song_b_base_path=song_b_base_path,
                                out_path=out_path,
                                **param_set
                            )
                        else:
                            logger.warning(f"Unknown transform type: {transform_type}")
                            continue
                        
                        # Store params with description for record keeping
                        params_for_record = param_set.copy()
                        if description:
                            params_for_record["description"] = description
                        
                        transform_records.append({
                            "orig_id": orig_id,
                            "transformed_id": transform_id,
                            "transform_type": transform_type,
                            "transform_name": transform_type,
                            "severity": severity,
                            "params": json.dumps(params_for_record),
                            "output_path": str(out_path),
                            "seed": global_seed,
                        })
                    except Exception as e:
                        logger.error(f"Failed to apply {transform_type} to {orig_id}: {e}")
    
    # Create transform manifest DataFrame
    transform_df = pd.DataFrame(transform_records)
    
    # Save manifest
    manifest_dir = output_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path_out = manifest_dir / "transform_manifest.csv"
    transform_df.to_csv(manifest_path_out, index=False)
    
    logger.info(f"Generated {len(transform_df)} transformed files")
    logger.info(f"Saved transform manifest to {manifest_path_out}")
    
    if len(transform_df) == 0:
        logger.warning("WARNING: No transformed files were generated! Check that:")
        logger.warning("  1. Original files exist and are readable")
        logger.warning("  2. Transform configs have 'enabled: true'")
        logger.warning("  3. File paths in manifest are correct")
    else:
        logger.info(f"Successfully generated transformations. Sample outputs:")
        for i, row in transform_df.head(5).iterrows():
            logger.info(f"  - {row['transformed_id']}: {row['transform_type']} -> {row['output_path']}")
    
    return transform_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate transformed audio files")
    parser.add_argument("--manifest", type=Path, required=True, help="Files manifest CSV")
    parser.add_argument("--test-matrix", type=Path, required=True, help="Test matrix YAML")
    parser.add_argument("--output", type=Path, default=Path("data"), help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    generate_transforms(
        args.manifest,
        args.test_matrix,
        args.output,
        random_seed=args.seed
    )
