"""Integrate Google ISLR (Kaggle) hand landmarks into 3D hand model poses.

Downloads and processes the ASL Signs dataset from Kaggle, extracting
MediaPipe hand landmarks (21 joints per hand, x/y/z) and converting them
into pose JSON files compatible with src/hand_model_3d.py.

Dataset: https://www.kaggle.com/competitions/asl-signs
License: CC BY 4.0

Prerequisites:
    pip install kaggle pyarrow pandas
    # Then set up ~/.kaggle/kaggle.json with your API credentials
    # See: https://www.kaggle.com/docs/api

Usage:
    # Download dataset and generate poses (first run)
    python scripts/integrate_kaggle_islr.py --download

    # Process already-downloaded data (skip download)
    python scripts/integrate_kaggle_islr.py --data-dir /path/to/asl-signs

    # Only process a subset of signs
    python scripts/integrate_kaggle_islr.py --data-dir /path/to/asl-signs --max-signs 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
POSES_DIR = PROJECT_ROOT / "models" / "hand" / "poses"
LANDMARKS_CACHE = PROJECT_ROOT / "data" / "islr_landmarks"

# MediaPipe hand landmark joint names (matches hand_model_3d.py)
JOINT_NAMES = [
    "wrist",
    "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]


def download_dataset(output_dir: Path) -> Path:
    """Download the Kaggle ASL Signs dataset."""
    try:
        import kaggle  # noqa: F401
    except ImportError:
        logger.error("kaggle package not installed. Run: pip install kaggle")
        sys.exit(1)

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        logger.error(
            "Kaggle API credentials not found at %s\n"
            "1. Go to https://www.kaggle.com/settings → API → Create New Token\n"
            "2. Save kaggle.json to ~/.kaggle/kaggle.json\n"
            "3. chmod 600 ~/.kaggle/kaggle.json",
            kaggle_json,
        )
        sys.exit(1)

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading ASL Signs dataset to %s (this may take a while, ~40GB)...", output_dir)

    api.competition_download_files("asl-signs", path=str(output_dir), quiet=False)
    logger.info("Download complete.")

    # Check for zip and extract
    zip_path = output_dir / "asl-signs.zip"
    if zip_path.exists():
        import zipfile
        logger.info("Extracting dataset...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(output_dir)
        logger.info("Extraction complete.")

    return output_dir


def load_sign_labels(data_dir: Path) -> dict[int, str]:
    """Load the sign label mapping from the dataset."""
    map_path = data_dir / "sign_to_prediction_index_map.json"
    if not map_path.exists():
        logger.error("sign_to_prediction_index_map.json not found in %s", data_dir)
        sys.exit(1)

    with open(map_path) as f:
        sign_to_idx = json.load(f)

    # Invert: index -> sign name
    return {int(v): k for k, v in sign_to_idx.items()}


def load_train_metadata(data_dir: Path) -> dict[str, dict]:
    """Load train.csv mapping sequence IDs to labels."""
    import pandas as pd

    train_path = data_dir / "train.csv"
    if not train_path.exists():
        logger.error("train.csv not found in %s", data_dir)
        sys.exit(1)

    df = pd.read_csv(train_path)
    metadata = {}
    for _, row in df.iterrows():
        metadata[row["path"]] = {
            "participant_id": row["participant_id"],
            "sequence_id": row["sequence_id"],
            "sign": row["sign"],
        }
    return metadata


def extract_hand_landmarks(parquet_path: Path) -> dict[str, list[tuple[float, float, float]]] | None:
    """Extract hand joint positions from a parquet landmark file.

    Returns a dict mapping joint names to (x, y, z) tuples,
    averaged across all frames in the sequence (representative pose).
    Returns None if hand data is missing.
    """
    import numpy as np
    import pandas as pd

    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        logger.warning("Failed to read %s: %s", parquet_path, e)
        return None

    # Filter to hand landmarks only
    hand_df = df[df["type"].isin(["left_hand", "right_hand"])]
    if hand_df.empty:
        return None

    # Prefer right hand (dominant for most signers), fall back to left
    right = hand_df[hand_df["type"] == "right_hand"]
    if not right.empty and not right[["x", "y", "z"]].isna().all().all():
        hand_df = right
    else:
        left = hand_df[hand_df["type"] == "left_hand"]
        if left.empty or left[["x", "y", "z"]].isna().all().all():
            return None
        hand_df = left

    # Get the middle frame (most representative) instead of averaging
    frames = sorted(hand_df["frame"].unique())
    if not frames:
        return None
    mid_frame = frames[len(frames) // 2]
    frame_df = hand_df[hand_df["frame"] == mid_frame].sort_values("landmark_index")

    if len(frame_df) != 21:
        # Fall back to averaging across all frames
        joints = {}
        for idx in range(21):
            if idx >= len(JOINT_NAMES):
                break
            jdf = hand_df[hand_df["landmark_index"] == idx][["x", "y", "z"]].dropna()
            if jdf.empty:
                return None
            joints[JOINT_NAMES[idx]] = (
                float(np.nanmean(jdf["x"])),
                float(np.nanmean(jdf["y"])),
                float(np.nanmean(jdf["z"])),
            )
        return joints

    joints = {}
    for _, row in frame_df.iterrows():
        idx = int(row["landmark_index"])
        if idx < len(JOINT_NAMES):
            x, y, z = row["x"], row["y"], row["z"]
            if any(np.isnan(v) for v in (x, y, z)):
                continue
            joints[JOINT_NAMES[idx]] = (float(x), float(y), float(z))

    return joints if len(joints) == 21 else None


def save_pose(sign_name: str, joints: dict, output_dir: Path) -> Path:
    """Save a hand pose as a JSON file compatible with HandModel3D."""
    pose_data = {
        "name": sign_name,
        "sign_id": f"word:{sign_name}",
        "joints": joints,
        "source": "kaggle-islr",
        "image_file": None,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{sign_name}.json"

    with open(output_path, "w") as f:
        json.dump(pose_data, f, indent=2)

    return output_path


def process_dataset(
    data_dir: Path,
    max_signs: int | None = None,
    max_samples_per_sign: int = 5,
) -> None:
    """Process the ISLR dataset and generate pose files."""

    logger.info("Loading metadata...")
    load_sign_labels(data_dir)
    metadata = load_train_metadata(data_dir)

    # Group sequences by sign
    sign_sequences: dict[str, list[str]] = {}
    for path, meta in metadata.items():
        sign = meta["sign"]
        if sign not in sign_sequences:
            sign_sequences[sign] = []
        sign_sequences[sign].append(path)

    signs_to_process = list(sign_sequences.keys())
    if max_signs:
        signs_to_process = signs_to_process[:max_signs]

    logger.info("Processing %d signs from dataset...", len(signs_to_process))

    processed = 0
    failed = 0

    for sign in signs_to_process:
        sequences = sign_sequences[sign][:max_samples_per_sign]

        # Try each sample until we get valid landmarks
        best_joints = None
        for seq_path in sequences:
            parquet_path = data_dir / "train_landmark_files" / seq_path
            if not parquet_path.exists():
                # Try with .parquet extension
                parquet_path = data_dir / "train_landmark_files" / (seq_path + ".parquet")
                if not parquet_path.exists():
                    continue

            joints = extract_hand_landmarks(parquet_path)
            if joints and len(joints) == 21:
                best_joints = joints
                break

        if best_joints:
            save_pose(sign, best_joints, POSES_DIR)
            processed += 1
        else:
            failed += 1

        if (processed + failed) % 25 == 0:
            logger.info("  Progress: %d/%d (failed: %d)", processed + failed, len(signs_to_process), failed)

    logger.info("Done! Generated %d pose files, %d failed.", processed, failed)
    logger.info("Poses saved to: %s", POSES_DIR)
    logger.info("Use with: python main.py -s subtitles.srt --use-3d --use-word-signs")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Integrate Kaggle ISLR hand landmarks into 3D hand model",
    )
    parser.add_argument("--download", action="store_true", help="Download dataset from Kaggle first")
    parser.add_argument("--data-dir", type=str, help="Path to extracted asl-signs dataset")
    parser.add_argument("--max-signs", type=int, default=None, help="Limit number of signs to process")
    parser.add_argument("--max-samples", type=int, default=5, help="Max samples per sign to try")
    args = parser.parse_args()

    if args.download:
        download_dir = LANDMARKS_CACHE
        data_dir = download_dataset(download_dir)
    elif args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        parser.error("Provide --download or --data-dir")
        return

    process_dataset(data_dir, max_signs=args.max_signs, max_samples_per_sign=args.max_samples)


if __name__ == "__main__":
    main()
