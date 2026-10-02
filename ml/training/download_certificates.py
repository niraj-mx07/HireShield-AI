"""Download and prepare the Kaggle "Internship Certificates" image dataset.

Usage::

    # Option A -- Kaggle API (requires ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY)
    python -m ml.training.download_certificates

    # Option B -- Manual
    #   1. Download from
    #      https://www.kaggle.com/datasets/godzilla04/internship-certificates
    #   2. Extract so that ml/data/raw/certificates/ contains the class folders
    #      "Real internship certificate" and "fake internship certificate"
    #   3. Re-run this script (it skips the download and just prepares the index)

The script:

    1. Downloads (or validates) the raw images under ``ml/data/raw/certificates``.
    2. Drops unreadable and duplicate images (MD5 over the file bytes).
    3. Writes a stratified 70/15/15 split index plus a summary to
       ``ml/data/processed/certificates/``.

The image dataset is intentionally **not** committed (see ``.gitignore``); only the
tiny index CSVs and the exported ONNX model travel with the repo.

Dataset facts (verified via the Kaggle API): 287 images, ~104 MB, CC0 Public
Domain -- 165 "Real internship certificate", 122 "fake internship certificate".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent          # ml/
DATA_RAW_DIR = ML_DIR / "data" / "raw"
CERT_RAW_DIR = DATA_RAW_DIR / "certificates"
PROCESSED_DIR = ML_DIR / "data" / "processed" / "certificates"

KAGGLE_DATASET = "godzilla04/internship-certificates"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

LABEL_REAL = 0
LABEL_FAKE = 1
LABEL_NAMES = {LABEL_REAL: "real", LABEL_FAKE: "fake"}


def download_via_kaggle() -> bool:
    """Download the certificate dataset with the Kaggle API."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore[import-untyped]
    except ImportError:
        print("[INFO] kaggle package not installed -- run: pip install kaggle")
        return False

    CERT_RAW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        api = KaggleApi()
        api.authenticate()
        print(f"[INFO] Downloading '{KAGGLE_DATASET}' ...")
        api.dataset_download_files(KAGGLE_DATASET, path=str(CERT_RAW_DIR), unzip=True)
        print(f"[OK]   Saved to {CERT_RAW_DIR}")
        return True
    except Exception as exc:  # noqa: BLE001 -- kaggle raises many types
        print(f"[WARN] Kaggle download failed: {exc}")
        return False


def label_from_path(path: Path) -> int | None:
    """Derive the label from the folder names ("real"/"fake" anywhere in the path)."""
    for part in path.parts:
        lowered = part.lower()
        if "fake" in lowered or "forged" in lowered:
            return LABEL_FAKE
        if "real" in lowered or "genuine" in lowered:
            return LABEL_REAL
    return None


def md5_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_images(root: Path) -> list[dict]:
    """Collect readable, de-duplicated images with their labels and dimensions."""
    try:
        from PIL import Image
    except ImportError:
        print("[ERROR] Pillow is required:  pip install -r ml/requirements-vision.txt")
        sys.exit(1)

    records: list[dict] = []
    seen: set[str] = set()
    unreadable = duplicates = unlabelled = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        label = label_from_path(path)
        if label is None:
            unlabelled += 1
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except Exception:  # noqa: BLE001 -- corrupt/truncated files
            unreadable += 1
            continue
        digest = md5_of(path)
        if digest in seen:
            duplicates += 1
            continue
        seen.add(digest)
        records.append(
            {
                "path": path.relative_to(ML_DIR.parent).as_posix(),
                "label": label,
                "label_name": LABEL_NAMES[label],
                "md5": digest,
                "width": width,
                "height": height,
                "bytes": path.stat().st_size,
            }
        )

    print(f"[INFO] unreadable={unreadable}  duplicates={duplicates}  unlabelled={unlabelled}")
    return records


def stratified_split(records: list[dict], seed: int, val_frac: float, test_frac: float) -> list[dict]:
    """Assign a train/val/test split per class so each split keeps the class ratio."""
    rng = random.Random(seed)
    by_label: dict[int, list[dict]] = {}
    for record in records:
        by_label.setdefault(record["label"], []).append(record)

    for label, items in sorted(by_label.items()):
        rng.shuffle(items)
        n_test = max(1, round(len(items) * test_frac))
        n_val = max(1, round(len(items) * val_frac))
        for index, item in enumerate(items):
            if index < n_test:
                split = "test"
            elif index < n_test + n_val:
                split = "val"
            else:
                split = "train"
            item["split"] = split
    return records


def write_splits(records: list[dict]) -> None:
    """Write per-split CSVs plus a summary JSON."""
    import csv

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["path", "label", "label_name", "split", "md5", "width", "height", "bytes"]

    for split in ("train", "val", "test"):
        subset = [r for r in records if r["split"] == split]
        out = PROCESSED_DIR / f"{split}.csv"
        with open(out, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(subset)
        print(f"[OK]   {out.relative_to(ML_DIR.parent).as_posix()}  ({len(subset)} rows)")

    widths = sorted(r["width"] for r in records)
    heights = sorted(r["height"] for r in records)
    summary = {
        "dataset": KAGGLE_DATASET,
        "total": len(records),
        "per_split": {
            split: dict(Counter(r["label_name"] for r in records if r["split"] == split))
            for split in ("train", "val", "test")
        },
        "per_class": dict(Counter(r["label_name"] for r in records)),
        "median_width": int(widths[len(widths) // 2]),
        "median_height": int(heights[len(heights) // 2]),
    }
    with open(PROCESSED_DIR / "summary.json", "w") as handle:
        json.dump(summary, handle, indent=2)

    print(f"\n{'=' * 60}")
    print("Certificate dataset summary")
    print(f"{'=' * 60}")
    print(f"  usable images : {summary['total']}  {summary['per_class']}")
    for split, counts in summary["per_split"].items():
        print(f"  {split:5s}        : {counts}")
    print(f"  median size   : {summary['median_width']}x{summary['median_height']}")
    print(f"{'=' * 60}")
    print("[NOTE] Only a few hundred images -- train the CNN on a GPU (see")
    print("       ml/notebooks/train_certificate_cnn.ipynb) and treat its output")
    print("       as a SECONDARY signal, never as a standalone verdict.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-download", action="store_true", help="Only prepare the index.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--test-frac", type=float, default=0.15)
    args = parser.parse_args()

    if not args.skip_download and not any(CERT_RAW_DIR.rglob("*.jpg")):
        download_via_kaggle()

    if not CERT_RAW_DIR.exists():
        print(f"[ERROR] Raw images not found at {CERT_RAW_DIR}")
        print(f"        Download https://www.kaggle.com/datasets/{KAGGLE_DATASET}")
        sys.exit(1)

    records = collect_images(CERT_RAW_DIR)
    if not records:
        print(f"[ERROR] No labelled images under {CERT_RAW_DIR}")
        print("        Expected the class folders 'Real internship certificate' /")
        print("        'fake internship certificate'.")
        sys.exit(1)

    stratified_split(records, args.seed, args.val_frac, args.test_frac)
    write_splits(records)


if __name__ == "__main__":
    main()