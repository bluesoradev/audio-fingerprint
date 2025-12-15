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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_transform_id(orig_id: str, transform_type: str, params: Dict, seed: int = None) -> str:
    """Generate deterministic ID for transformed file."""
    param_str = "_".join(f"{k}_{v}" for k, v in sorted(params.items()))
    if seed is not None:
        param_str += f"_seed_{seed}"
    return f"{orig_id}__{transform_type}__{param_str}"


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
    
    # Load files manifest
    files_df = pd.read_csv(manifest_path)
    logger.info(f"Loaded {len(files_df)} original files")
    
    # Load test matrix
    with open(test_matrix_path, 'r') as f:
        test_config = yaml.safe_load(f)
    
    transform_configs = test_config.get("transforms", {})
    global_seed = test_config.get("global", {}).get("random_seed", random_seed)
    
    output_dir = Path(output_dir)
    transformed_dir = output_dir / "transformed"
    transformed_dir.mkdir(parents=True, exist_ok=True)
    
    transform_records = []
    
    # Iterate over original files
    for _, file_row in tqdm(files_df.iterrows(), total=len(files_df), desc="Processing originals"):
        orig_id = file_row["id"]
        orig_path = Path(file_row["file_path"])
        
        if not orig_path.exists():
            logger.warning(f"Original file not found: {orig_path}")
            continue
        
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
                    # Extract severity if present
                    severity = param_set.pop("severity", "moderate")
                    
                    # Generate transform ID
                    transform_id = generate_transform_id(orig_id, transform_type, param_set)
                    out_path = transformed_dir / f"{transform_id}.wav"
                    
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
                        else:
                            logger.warning(f"Unknown transform type: {transform_type}")
                            continue
                        
                        transform_records.append({
                            "orig_id": orig_id,
                            "transformed_id": transform_id,
                            "transform_type": transform_type,
                            "transform_name": transform_type,
                            "severity": severity,
                            "params": json.dumps(param_set),
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
