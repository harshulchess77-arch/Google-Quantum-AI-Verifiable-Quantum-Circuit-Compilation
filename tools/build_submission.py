"""tools/build_submission.py - Deterministic Kaggle submission.zip builder.

Constructs a submission.zip from the best verified circuits in bench*/best/,
validates the structure, and can optionally verify the submission before packaging.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import tempfile
import zipfile
from typing import Dict, Any

from tools.verify import run_official_verifier
from tools.score import BASELINE_COSTS, compute_competition_score


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def compute_file_hash(file_path: pathlib.Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def build_submission(
    output_path: pathlib.Path | None = None,
    verify_before_build: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Build submission.zip from bench*/best/ artifacts.
    
    Args:
        output_path: Path for output submission.zip (default: submission.zip in repo root)
        verify_before_build: If True, verify all circuits before building
        dry_run: If True, skip actual file operations and return structure only
    
    Returns:
        Dict with submission structure, hashes, and verification results
    """
    if output_path is None:
        output_path = REPO_ROOT / "submission.zip"
    
    submission_structure = {
        "invsqrt": REPO_ROOT / "bench1" / "best" / "invsqrt.kmb",
        "dqi": REPO_ROOT / "bench2" / "best" / "dqi.kmb",
        "dfthcsos_dir": REPO_ROOT / "bench3" / "best" / "dfthcsos",
    }
    
    # Verify all required files exist
    missing = []
    if not submission_structure["invsqrt"].exists():
        missing.append("bench1/best/invsqrt.kmb")
    if not submission_structure["dqi"].exists():
        missing.append("bench2/best/dqi.kmb")
    if not submission_structure["dfthcsos_dir"].exists():
        missing.append("bench3/best/dfthcsos/")
    
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")
    
    # Verify dfthcsos structure
    dfthcsos_npz = submission_structure["dfthcsos_dir"] / "submission.npz"
    angle_files = sorted(submission_structure["dfthcsos_dir"].glob("angle_k_*.kmb"))
    if not dfthcsos_npz.exists():
        missing.append("bench3/best/dfthcsos/submission.npz")
    if not angle_files:
        missing.append("bench3/best/dfthcsos/angle_k_*.kmb")
    
    if missing:
        raise FileNotFoundError(f"Missing dfthcsos files: {missing}")
    
    # Optional pre-build verification
    verification_results = {}
    if verify_before_build and not dry_run:
        print("Pre-build verification: bench1...")
        verification_results["bench1"] = run_official_verifier("bench1", submission_structure["invsqrt"])
        
        print("Pre-build verification: bench2...")
        verification_results["bench2"] = run_official_verifier("bench2", submission_structure["dqi"])
        
        print("Pre-build verification: bench3...")
        verification_results["bench3"] = run_official_verifier("bench3", submission_structure["dfthcsos_dir"])
        
        # Check all passed
        failed = [b for b, r in verification_results.items() if not r["pass"]]
        if failed:
            raise RuntimeError(f"Verification failed for: {failed}")
    
    if dry_run:
        return {
            "status": "DRY_RUN",
            "structure": {k: str(v) for k, v in submission_structure.items()},
            "verification": verification_results if verify_before_build else None,
            "output_path": str(output_path)
        }
    
    # Build the zip file
    print(f"Building submission.zip -> {output_path}")
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add invsqrt.kmb
        zf.write(submission_structure["invsqrt"], "invsqrt.kmb")
        invsqrt_hash = compute_file_hash(submission_structure["invsqrt"])
        
        # Add dqi.kmb
        zf.write(submission_structure["dqi"], "dqi.kmb")
        dqi_hash = compute_file_hash(submission_structure["dqi"])
        
        # Add dfthcsos directory contents
        zf.write(dfthcsos_npz, "dfthcsos/submission.npz")
        npz_hash = compute_file_hash(dfthcsos_npz)
        
        angle_hashes = {}
        for angle_file in angle_files:
            arcname = f"dfthcsos/{angle_file.name}"
            zf.write(angle_file, arcname)
            angle_hashes[angle_file.name] = compute_file_hash(angle_file)
    
    result = {
        "status": "SUCCESS",
        "output_path": str(output_path),
        "hashes": {
            "invsqrt.kmb": invsqrt_hash,
            "dqi.kmb": dqi_hash,
            "dfthcsos/submission.npz": npz_hash,
            "angle_files": angle_hashes,
        },
        "verification": verification_results if verify_before_build else None,
    }
    
    print(f"Submission built successfully: {output_path}")
    print(f"  invsqrt.kmb: {invsqrt_hash[:16]}...")
    print(f"  dqi.kmb: {dqi_hash[:16]}...")
    print(f"  dfthcsos/submission.npz: {npz_hash[:16]}...")
    print(f"  angle_files: {len(angle_hashes)} circuits")
    
    return result


def validate_submission_structure(submission_path: pathlib.Path) -> Dict[str, Any]:
    """Validate that a submission.zip has the correct structure.
    
    Returns validation report with file listing and structure check.
    """
    if not submission_path.exists():
        raise FileNotFoundError(f"Submission not found: {submission_path}")
    
    with zipfile.ZipFile(submission_path, "r") as zf:
        namelist = zf.namelist()
    
    required = {
        "invsqrt.kmb": False,
        "dqi.kmb": False,
        "dfthcsos/submission.npz": False,
    }
    
    angle_files = []
    for name in namelist:
        if name in required:
            required[name] = True
        elif name.startswith("dfthcsos/angle_k_") and (name.endswith(".kmb") or name.endswith(".kmx")):
            angle_files.append(name)
    
    missing = [k for k, v in required.items() if not v]
    
    result = {
        "valid": len(missing) == 0 and len(angle_files) > 0,
        "missing": missing,
        "angle_count": len(angle_files),
        "angle_files": sorted(angle_files),
        "all_files": sorted(namelist),
    }
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Build and validate Kaggle submission.zip")
    parser.add_argument("--output", "-o", type=pathlib.Path, default=None, help="Output path for submission.zip")
    parser.add_argument("--verify", action="store_true", help="Verify circuits before building")
    parser.add_argument("--validate", type=pathlib.Path, help="Validate existing submission.zip structure")
    parser.add_argument("--dry-run", action="store_true", help="Show structure without building")
    args = parser.parse_args()
    
    if args.validate:
        result = validate_submission_structure(args.validate)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    
    try:
        result = build_submission(args.output, args.verify, args.dry_run)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
