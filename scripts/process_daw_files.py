"""Script to process DAW project files and extract metadata."""
import argparse
import json
import logging
from pathlib import Path
from typing import List
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daw_parser import AbletonParser, FLStudioParser, LogicParser, DAWParseError
from daw_parser.exceptions import CorruptedFileError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_daw_file(file_path: Path, output_dir: Path) -> dict:
    """
    Process a single DAW file and extract metadata.
    
    Args:
        file_path: Path to DAW project file
        output_dir: Directory to save extracted metadata
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Detect file type and create appropriate parser
        suffix = file_path.suffix.lower()
        if suffix == '.als':
            parser = AbletonParser(file_path)
        elif suffix == '.flp':
            parser = FLStudioParser(file_path)
        elif suffix in ['.logicx', '.logic']:
            parser = LogicParser(file_path)
        else:
            return {
                "file": str(file_path),
                "status": "unsupported",
                "error": f"Unsupported file type: {file_path.suffix}"
            }
        
        # Parse file
        metadata = parser.parse()
        
        # Save metadata to JSON
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{file_path.stem}_metadata.json"
        
        metadata_dict = metadata.to_dict()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, default=str)
        
        logger.info(f"Processed {file_path.name}: {metadata_dict['total_notes']} notes, "
                   f"{metadata_dict['arrangement_clips']} clips")
        
        return {
            "file": str(file_path),
            "status": "success",
            "output": str(output_file),
            "metadata": metadata_dict
        }
        
    except CorruptedFileError as e:
        logger.error(f"Corrupted file {file_path}: {e}")
        return {
            "file": str(file_path),
            "status": "error",
            "error": f"Corrupted file: {e}"
        }
    except DAWParseError as e:
        logger.error(f"Parse error for {file_path}: {e}")
        return {
            "file": str(file_path),
            "status": "error",
            "error": f"Parse error: {e}"
        }
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")
        return {
            "file": str(file_path),
            "status": "error",
            "error": f"Unexpected error: {e}"
        }


def process_directory(directory: Path, output_dir: Path, extensions: List[str] = ['.als']) -> List[dict]:
    """
    Process all DAW files in a directory.
    
    Args:
        directory: Directory containing DAW files
        output_dir: Directory to save extracted metadata
        extensions: List of file extensions to process
        
    Returns:
        List of processing results
    """
    results = []
    
    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            logger.info(f"Processing {file_path}")
            result = process_daw_file(file_path, output_dir)
            results.append(result)
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process DAW project files and extract metadata"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="DAW project file or directory containing DAW files"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("data/daw_metadata"),
        help="Output directory for extracted metadata (default: data/daw_metadata)"
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        default=[".als", ".flp", ".logicx", ".logic"],
        help="File extensions to process (default: .als .flp .logicx .logic)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return 1
    
    results = []
    
    if input_path.is_file():
        # Process single file
        logger.info(f"Processing single file: {input_path}")
        result = process_daw_file(input_path, output_dir)
        results.append(result)
    elif input_path.is_dir():
        # Process directory
        logger.info(f"Processing directory: {input_path}")
        results = process_directory(input_path, output_dir, args.extensions)
    else:
        logger.error(f"Invalid input path: {input_path}")
        return 1
    
    # Print summary
    successful = sum(1 for r in results if r.get("status") == "success")
    failed = len(results) - successful
    
    logger.info(f"\nProcessing complete:")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total: {len(results)}")
    
    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }, f, indent=2, default=str)
    
    logger.info(f"Summary saved to: {summary_file}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
