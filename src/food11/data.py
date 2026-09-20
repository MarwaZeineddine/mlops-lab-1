"""Preprocess the raw Food-11 image dataset into an ImageFolder-style layout.

Reads the three raw splits (training, evaluation, validation), resizes every
image to 128x128, and writes them into category-named folders so the output can
be consumed directly by torchvision's ImageFolder / ResNet training pipelines.

Two output trees are produced:
  - data/food11_processed        : the full dataset
  - data/food11_processed_mini   : capped at 100 images per category per split,
                                   for fast local iteration.

The script is idempotent: each processed output tree is removed and rebuilt on
every run, so re-running never leaves stale files behind.
"""

from __future__ import annotations

import shutil
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

# category_index (parsed from "<index>_<anything>.jpg") -> human-readable name.
CATEGORIES = {
    0: "Bread",
    1: "Dairy product",
    2: "Dessert",
    3: "Egg",
    4: "Fried food",
    5: "Meat",
    6: "Noodles-Pasta",
    7: "Rice",
    8: "Seafood",
    9: "Soup",
    10: "Vegetable-Fruit",
}

SPLITS = ("training", "evaluation", "validation")
IMAGE_SIZE = (128, 128)
MINI_CAP = 100  # max images per category per split in the mini dataset

# Resolve paths relative to the project root (two levels up from src/food11/).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "food11_raw"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "food11_processed"
MINI_ROOT = PROJECT_ROOT / "data" / "food11_processed_mini"


def parse_category_index(filename: str) -> int | None:
    """Extract the leading category index from a "<index>_<anything>.jpg" name.

    Returns None if the filename does not follow the expected pattern.
    """
    stem = filename.split("_", 1)[0]
    try:
        index = int(stem)
    except ValueError:
        return None
    return index if index in CATEGORIES else None


def reset_output_dir(path: Path) -> None:
    """Remove any existing output tree and recreate it empty (idempotency)."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def process() -> None:
    if not RAW_ROOT.exists():
        sys.exit(f"Raw data directory not found: {RAW_ROOT}")

    # Wipe both output trees up front so a re-run is always clean.
    reset_output_dir(PROCESSED_ROOT)
    reset_output_dir(MINI_ROOT)

    # counts[dataset][split][category_name] -> number written
    counts: dict[str, dict[str, dict[str, int]]] = {
        "full": defaultdict(lambda: defaultdict(int)),
        "mini": defaultdict(lambda: defaultdict(int)),
    }
    skipped: list[str] = []

    for split in SPLITS:
        raw_split = RAW_ROOT / split
        if not raw_split.is_dir():
            print(f"  [warn] missing split directory, skipping: {raw_split}")
            continue

        # Per-split counter used to enforce the mini dataset cap per category.
        mini_written: dict[int, int] = defaultdict(int)

        for img_path in sorted(raw_split.glob("*.jpg")):
            category_index = parse_category_index(img_path.name)
            if category_index is None:
                skipped.append(str(img_path))
                continue
            category_name = CATEGORIES[category_index]

            try:
                with Image.open(img_path) as img:
                    # Convert to RGB so grayscale/CMYK/palette images normalize
                    # to a consistent 3-channel format for ResNet-style models.
                    resized = img.convert("RGB").resize(IMAGE_SIZE)

                    # --- full dataset ---
                    full_dir = PROCESSED_ROOT / split / category_name
                    full_dir.mkdir(parents=True, exist_ok=True)
                    resized.save(full_dir / img_path.name)
                    counts["full"][split][category_name] += 1

                    # --- mini dataset (capped) ---
                    if mini_written[category_index] < MINI_CAP:
                        mini_dir = MINI_ROOT / split / category_name
                        mini_dir.mkdir(parents=True, exist_ok=True)
                        resized.save(mini_dir / img_path.name)
                        mini_written[category_index] += 1
                        counts["mini"][split][category_name] += 1
            except OSError as exc:
                skipped.append(f"{img_path} ({exc})")

        print(f"  processed split: {split}")

    _report(counts, skipped)


def _report(
    counts: dict[str, dict[str, dict[str, int]]],
    skipped: list[str],
) -> None:
    """Print per-category file counts for both datasets."""
    for dataset, root in (("full", PROCESSED_ROOT), ("mini", MINI_ROOT)):
        print(f"\n=== {dataset} dataset: {root} ===")
        grand_total = 0
        for split in SPLITS:
            split_counts = counts[dataset].get(split, {})
            split_total = sum(split_counts.values())
            grand_total += split_total
            print(f"\n  {split} (total: {split_total})")
            for name in CATEGORIES.values():
                print(f"    {name:<16} {split_counts.get(name, 0)}")
        print(f"\n  {dataset} grand total: {grand_total}")

    if skipped:
        print(f"\n[warn] skipped {len(skipped)} file(s):")
        for item in skipped[:20]:
            print(f"    {item}")
        if len(skipped) > 20:
            print(f"    ... and {len(skipped) - 20} more")


if __name__ == "__main__":
    print(f"Preprocessing Food-11 from {RAW_ROOT}")
    process()
    print("\nDone.")
