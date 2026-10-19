"""Prepare the legacy VoTT labels and train a self-contained YOLO11 bobber model.

The generated dataset and ``models/bobber/best.pt`` live inside this project.
Training and runtime do not depend on the removed legacy YOLOv3 repository.
"""

import argparse
import csv
import hashlib
import random
import shutil
from collections import OrderedDict, defaultdict
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "bobber"
RAW_DATA_DIR = DATA_ROOT / "raw"
DEFAULT_ANNOTATIONS = RAW_DATA_DIR / "annotations.csv"
DEFAULT_IMAGES_DIR = RAW_DATA_DIR / "images"
DEFAULT_DATASET_DIR = DATA_ROOT / "yolo11"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "bobber" / "best.pt"
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=DEFAULT_IMAGES_DIR,
        help="Directory containing the images named by the VoTT CSV (searched recursively).",
    )
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--model", default="yolo11s.pt", help="Ultralytics base checkpoint.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--batch", type=int, default=-1, help="-1 enables automatic batch sizing.")
    parser.add_argument("--device", default=None, help="CUDA device, 'cpu', or omit for automatic selection.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def find_images(images_dir):
    """Index images by filename so labels can reference legacy nested directories."""
    image_index = {}
    for candidate in images_dir.rglob("*"):
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES:
            image_index.setdefault(candidate.name, candidate)
    return image_index


def read_annotations(csv_path):
    """Read VoTT's pixel-coordinate CSV and retain its label ordering."""
    annotations = defaultdict(list)
    classes = OrderedDict()
    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        expected_fields = {"image", "xmin", "ymin", "xmax", "ymax", "label"}
        if not reader.fieldnames or not expected_fields.issubset(reader.fieldnames):
            raise ValueError("Annotations CSV must contain image, xmin, ymin, xmax, ymax, and label columns.")
        for row in reader:
            label = row["label"].strip()
            classes.setdefault(label, len(classes))
            annotations[row["image"].strip()].append(
                (float(row["xmin"]), float(row["ymin"]), float(row["xmax"]), float(row["ymax"]), label)
            )
    return annotations, classes


def write_dataset_yaml(dataset_dir, classes):
    """Write a portable Ultralytics data configuration without a YAML dependency."""
    yaml_path = dataset_dir / "data.yaml"
    class_lines = ", ".join(f"{index}: {name!r}" for name, index in classes.items())
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {dataset_dir.as_posix()}",
                "train: images/train",
                "val: images/val",
                f"names: {{{class_lines}}}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path


def prepare_dataset(annotations_path, images_dir, dataset_dir, val_ratio, seed):
    """Copy images and convert each VoTT rectangle to a normalized YOLO label."""
    if not annotations_path.is_file():
        raise FileNotFoundError(f"Annotations CSV not found: {annotations_path}")
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not 0 < val_ratio < 1:
        raise ValueError("--val-ratio must be between 0 and 1.")

    annotations, classes = read_annotations(annotations_path)
    image_index = find_images(images_dir)
    missing_images = sorted(name for name in annotations if name not in image_index)
    if missing_images:
        preview = ", ".join(missing_images[:5])
        raise FileNotFoundError(
            f"{len(missing_images)} labeled images are missing (for example: {preview}). "
            "Restore the original screenshots before training."
        )

    # IMPROVEMENT: Recreate only the generated dataset directory, never the source annotations/images.
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    for split in ("train", "val"):
        (dataset_dir / "images" / split).mkdir(parents=True)
        (dataset_dir / "labels" / split).mkdir(parents=True)

    image_names = list(annotations)
    random.Random(seed).shuffle(image_names)
    val_count = max(1, round(len(image_names) * val_ratio))
    validation_names = set(image_names[:val_count])

    for image_name in image_names:
        split = "val" if image_name in validation_names else "train"
        source_image = image_index[image_name]
        # Prefixing removes collisions when similarly named images came from nested folders.
        source_id = hashlib.sha1(str(source_image.resolve()).encode("utf-8")).hexdigest()[:10]
        destination_stem = f"{source_id}_{source_image.stem}"
        destination_image = dataset_dir / "images" / split / f"{destination_stem}{source_image.suffix.lower()}"
        destination_label = dataset_dir / "labels" / split / f"{destination_stem}.txt"
        shutil.copy2(source_image, destination_image)

        with Image.open(source_image) as image:
            image_width, image_height = image.size
        lines = []
        for xmin, ymin, xmax, ymax, label in annotations[image_name]:
            xmin, xmax = sorted((max(0.0, xmin), min(float(image_width), xmax)))
            ymin, ymax = sorted((max(0.0, ymin), min(float(image_height), ymax)))
            box_width, box_height = xmax - xmin, ymax - ymin
            if box_width <= 0 or box_height <= 0:
                continue
            center_x = (xmin + xmax) / 2 / image_width
            center_y = (ymin + ymax) / 2 / image_height
            lines.append(
                f"{classes[label]} {center_x:.8f} {center_y:.8f} "
                f"{box_width / image_width:.8f} {box_height / image_height:.8f}"
            )
        destination_label.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return write_dataset_yaml(dataset_dir, classes), len(image_names), classes


def train_model(arguments, data_yaml):
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from error

    model = YOLO(arguments.model)
    model.train(
        data=str(data_yaml),
        epochs=arguments.epochs,
        imgsz=arguments.imgsz,
        batch=arguments.batch,
        device=arguments.device,
        workers=arguments.workers,
        project=str(PROJECT_ROOT / "runs" / "yolo11"),
        name="bobber",
        exist_ok=True,
    )
    best_checkpoint = Path(model.trainer.save_dir) / "weights" / "best.pt"
    if not best_checkpoint.is_file():
        raise FileNotFoundError(f"Training finished without best.pt: {best_checkpoint}")
    DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_checkpoint, DEFAULT_MODEL_PATH)
    print(f"Saved runtime checkpoint: {DEFAULT_MODEL_PATH}")


def main():
    arguments = parse_arguments()
    data_yaml, image_count, classes = prepare_dataset(
        arguments.annotations,
        arguments.images_dir,
        arguments.dataset_dir,
        arguments.val_ratio,
        arguments.seed,
    )
    print(f"Prepared {image_count} images with classes: {', '.join(classes)}")
    print(f"Dataset configuration: {data_yaml}")
    if not arguments.prepare_only:
        train_model(arguments, data_yaml)


if __name__ == "__main__":
    main()
