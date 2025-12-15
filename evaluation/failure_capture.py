"""Capture failure cases with artifacts."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import librosa
import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Optional imports for spectrogram generation
HAS_DISPLAY = False
try:
    import librosa.display
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_DISPLAY = True
except ImportError as e:
    logger.warning(f"Could not import display libraries (matplotlib/librosa.display): {e}. Spectrogram generation will be disabled.")
    plt = None


def save_spectrogram(audio_path: Path, out_path: Path, sample_rate: int = 44100):
    """Generate and save spectrogram image."""
    if not HAS_DISPLAY:
        logger.debug(f"Skipping spectrogram generation (display libraries not available): {audio_path}")
        return
    
    try:
        y, sr = librosa.load(str(audio_path), sr=sample_rate, mono=True)
        
        # Compute spectrogram
        D = librosa.stft(y)
        S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 4))
        img = librosa.display.specshow(
            S_db,
            x_axis='time',
            y_axis='hz',
            sr=sr,
            ax=ax
        )
        ax.set_title(f'Spectrogram: {audio_path.name}')
        plt.colorbar(img, ax=ax, format='%+2.0f dB')
        
        # Save
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        logger.error(f"Failed to generate spectrogram for {audio_path}: {e}")


def capture_failure_case(
    transformed_id: str,
    transformed_path: Path,
    original_id: str,
    original_path: Path,
    query_results: Dict,
    top_matches: List[Dict],
    reason: str,
    output_dir: Path,
    index_metadata: Dict = None
):
    """
    Capture a failure case with all artifacts.
    
    Args:
        transformed_id: ID of transformed file
        transformed_path: Path to transformed audio
        original_id: Expected original ID
        original_path: Path to original audio
        query_results: Full query result dictionary
        top_matches: Top-K match results
        reason: Reason for failure
        output_dir: Directory to save artifacts
        index_metadata: Index metadata (for finding matched audio paths)
    """
    case_dir = output_dir / transformed_id
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Save transformed audio
    if transformed_path.exists():
        copy_path = case_dir / "transformed.wav"
        import shutil
        shutil.copy2(transformed_path, copy_path)
    
    # Save original audio
    if original_path.exists():
        copy_path = case_dir / "original.wav"
        import shutil
        shutil.copy2(original_path, copy_path)
    
    # Save top match audio (if we can find it)
    if top_matches and len(top_matches) > 0:
        top_match_id = top_matches[0].get("id", "")
        # Try to find match audio file (would need mapping from IDs to paths)
        # For now, just save the match ID
    
    # Generate spectrograms
    if transformed_path.exists():
        save_spectrogram(transformed_path, case_dir / "spectrogram_transformed.png")
    if original_path.exists():
        save_spectrogram(original_path, case_dir / "spectrogram_original.png")
    
    # Save query results JSON snippet
    query_snippet = {
        "transformed_id": transformed_id,
        "expected_original_id": original_id,
        "top_matches": top_matches[:5],  # Top 5
        "query_results": query_results,
        "failure_reason": reason,
    }
    
    with open(case_dir / "failure_details.json", 'w') as f:
        json.dump(query_snippet, f, indent=2, default=str)
    
    logger.debug(f"Captured failure case: {case_dir}")


def capture_failures(
    query_summary_path: Path,
    transform_manifest_path: Path,
    files_manifest_path: Path,
    query_results_dir: Path,
    output_dir: Path,
    max_failures_per_transform: int = 10,
    index_metadata: Dict = None
):
    """
    Capture failure cases from query results.
    
    Args:
        query_summary_path: Path to query summary CSV
        transform_manifest_path: Path to transform manifest
        files_manifest_path: Path to original files manifest
        query_results_dir: Directory with individual query JSON files
        output_dir: Directory to save failure artifacts
        max_failures_per_transform: Max failures to capture per transform type
        index_metadata: Index metadata
    """
    # Load data
    query_df = pd.read_csv(query_summary_path)
    transform_df = pd.read_csv(transform_manifest_path)
    files_df = pd.read_csv(files_manifest_path)
    
    # Build mappings
    transform_to_orig = dict(zip(transform_df["transformed_id"], transform_df["orig_id"]))
    transform_to_path = dict(zip(transform_df["transformed_id"], transform_df["output_path"]))
    orig_to_path = dict(zip(files_df["id"], files_df["file_path"]))
    
    # Identify failures (where top_match_id != expected orig_id)
    query_df = query_df.copy()
    query_df["expected_orig_id"] = query_df["transformed_id"].map(transform_to_orig)
    failures = query_df[query_df["top_match_id"] != query_df["expected_orig_id"]].copy()
    
    logger.info(f"Found {len(failures)} failure cases")
    
    # Group by transform type
    failures_by_transform = failures.groupby("transform_type")
    
    captured_count = 0
    
    for transform_type, group in failures_by_transform:
        transform_failures = group.head(max_failures_per_transform)
        
        for _, row in tqdm(transform_failures.iterrows(), total=len(transform_failures), desc=f"Capturing {transform_type}"):
            transformed_id = row["transformed_id"]
            original_id = row["expected_orig_id"]
            
            transformed_path = Path(transform_to_path.get(transformed_id, ""))
            original_path = Path(orig_to_path.get(original_id, ""))
            
            # Load full query results
            query_result_path = query_results_dir / f"{transformed_id}_query.json"
            if query_result_path.exists():
                with open(query_result_path, 'r') as f:
                    query_results = json.load(f)
            else:
                query_results = {}
            
            top_matches = query_results.get("aggregated_results", [])[:10]
            
            # Determine failure reason
            if row["top_match_rank"] == -1:
                reason = "No matches found"
            elif row["top_match_similarity"] < 0.5:
                reason = f"Low similarity: {row['top_match_similarity']:.3f}"
            else:
                reason = f"Wrong match: {row['top_match_id']} (expected {original_id})"
            
            # Capture failure
            capture_failure_case(
                transformed_id=transformed_id,
                transformed_path=transformed_path,
                original_id=original_id,
                original_path=original_path,
                query_results=query_results,
                top_matches=top_matches,
                reason=reason,
                output_dir=output_dir,
                index_metadata=index_metadata
            )
            
            captured_count += 1
    
    logger.info(f"Captured {captured_count} failure cases to {output_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture failure cases")
    parser.add_argument("--query-summary", type=Path, required=True)
    parser.add_argument("--transform-manifest", type=Path, required=True)
    parser.add_argument("--files-manifest", type=Path, required=True)
    parser.add_argument("--query-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-per-transform", type=int, default=10)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    capture_failures(
        args.query_summary,
        args.transform_manifest,
        args.files_manifest,
        args.query_results,
        args.output,
        max_failures_per_transform=args.max_per_transform
    )
