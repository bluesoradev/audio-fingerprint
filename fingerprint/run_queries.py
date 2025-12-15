"""Run queries on transformed audio files."""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
import time
import pandas as pd
from tqdm import tqdm

from .load_model import load_fingerprint_model
from .embed import segment_audio, extract_embeddings, normalize_embeddings
from .query_index import load_index, query_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_query_on_file(
    file_path: Path,
    index: any,
    model_config: Dict,
    topk: int = 10,
    index_metadata: Dict = None
) -> Dict:
    """
    Run fingerprint query on a single file.
    
    Returns:
        Dictionary with query results and metadata
    """
    start_time = time.time()
    
    try:
        # Segment audio
        segments = segment_audio(
            file_path,
            segment_length=model_config["segment_length"],
            sample_rate=model_config["sample_rate"]
        )
        
        # Extract embeddings
        embeddings = extract_embeddings(
            segments,
            model_config,
            save_embeddings=False
        )
        
        # Normalize embeddings
        embeddings = normalize_embeddings(embeddings, method="l2")
        
        # Query index for each segment
        segment_results = []
        for seg, emb in zip(segments, embeddings):
            results = query_index(
                index,
                emb,
                topk=topk,
                ids=index_metadata.get("ids") if index_metadata else None,
                normalize=True
            )
            
            segment_results.append({
                "segment_id": seg["segment_id"],
                "start": seg["start"],
                "end": seg["end"],
                "results": results
            })
        
        # Aggregate segment results (simple mean fusion)
        all_candidates = {}
        for seg_result in segment_results:
            for result in seg_result["results"]:
                candidate_id = result.get("id", f"index_{result['index']}")
                if candidate_id not in all_candidates:
                    all_candidates[candidate_id] = {
                        "id": candidate_id,
                        "similarities": [],
                        "ranks": [],
                        "count": 0
                    }
                all_candidates[candidate_id]["similarities"].append(result["similarity"])
                all_candidates[candidate_id]["ranks"].append(result["rank"])
                all_candidates[candidate_id]["count"] += 1
        
        # Compute aggregate scores
        aggregated = []
        for candidate_id, data in all_candidates.items():
            avg_similarity = sum(data["similarities"]) / len(data["similarities"])
            avg_rank = sum(data["ranks"]) / len(data["ranks"])
            min_rank = min(data["ranks"])
            
            aggregated.append({
                "id": candidate_id,
                "mean_similarity": avg_similarity,
                "mean_rank": avg_rank,
                "min_rank": min_rank,
                "match_count": data["count"],
                "rank": len(aggregated) + 1
            })
        
        # Sort by similarity
        aggregated.sort(key=lambda x: x["mean_similarity"], reverse=True)
        for i, item in enumerate(aggregated):
            item["rank"] = i + 1
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "file_path": str(file_path),
            "file_id": file_path.stem,
            "num_segments": len(segments),
            "latency_ms": latency_ms,
            "segment_results": segment_results,
            "aggregated_results": aggregated[:topk],
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Query failed for {file_path}: {e}")
        return {
            "file_path": str(file_path),
            "file_id": file_path.stem,
            "error": str(e),
            "latency_ms": (time.time() - start_time) * 1000,
            "timestamp": time.time()
        }


def run_queries(
    transform_manifest_path: Path,
    index_path: Path,
    fingerprint_config_path: Path,
    output_dir: Path,
    topk: int = 10
) -> pd.DataFrame:
    """
    Run queries on all transformed files.
    
    Returns:
        DataFrame with query results
    """
    # Load transform manifest
    transform_df = pd.read_csv(transform_manifest_path)
    logger.info(f"Loaded {len(transform_df)} transformed files")
    
    # Load fingerprint model
    model_config = load_fingerprint_model(fingerprint_config_path)
    logger.info(f"Loaded fingerprint model: {model_config['embedding_dim']}D")
    
    # Load index
    index, index_metadata = load_index(index_path)
    logger.info(f"Loaded index with {index.ntotal} vectors")
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir = output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    query_records = []
    
    # Process each transformed file
    for _, row in tqdm(transform_df.iterrows(), total=len(transform_df), desc="Running queries"):
        file_path = Path(row["output_path"])
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Run query
        result = run_query_on_file(
            file_path,
            index,
            model_config,
            topk=topk,
            index_metadata=index_metadata
        )
        
        # Save individual result JSON
        # Sanitize transformed_id to remove filesystem-invalid characters (/, \, :, *, ?, ", <, >, |)
        safe_id = str(row['transformed_id']).replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        result_path = results_dir / f"{safe_id}_query.json"
        # Ensure parent directory exists
        result_path.parent.mkdir(parents=True, exist_ok=True)
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Extract top match info
        top_match = result.get("aggregated_results", [{}])[0] if result.get("aggregated_results") else {}
        
        query_records.append({
            "transformed_id": row["transformed_id"],
            "orig_id": row["orig_id"],
            "transform_type": row["transform_type"],
            "severity": row["severity"],
            "file_path": str(file_path),
            "latency_ms": result.get("latency_ms", 0),
            "num_segments": result.get("num_segments", 0),
            "top_match_id": top_match.get("id", ""),
            "top_match_similarity": top_match.get("mean_similarity", 0.0),
            "top_match_rank": top_match.get("rank", -1),
            "result_path": str(result_path),
            "error": result.get("error", ""),
        })
    
    # Save summary CSV
    results_df = pd.DataFrame(query_records)
    summary_path = output_dir / "query_summary.csv"
    results_df.to_csv(summary_path, index=False)
    
    logger.info(f"Saved query results to {output_dir}")
    
    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fingerprint queries")
    parser.add_argument("--manifest", type=Path, required=True, help="Transform manifest CSV")
    parser.add_argument("--index", type=Path, required=True, help="FAISS index path")
    parser.add_argument("--config", type=Path, required=True, help="Fingerprint config YAML")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--topk", type=int, default=10, help="Top-K results")
    
    args = parser.parse_args()
    
    run_queries(
        args.manifest,
        args.index,
        args.config,
        args.output,
        topk=args.topk
    )
