"""Train the certificate forgery CNN locally and export it for the backend.

This is the local, CPU-friendly twin of ``ml/notebooks/train_certificate_cnn.ipynb``
(same seed, splits, augmentations, threshold policy and ONNX contract), so a fresh
checkout can produce the vision artifact without Kaggle:

    .ml-venv/bin/python -m ml.training.train_certificate_cnn

Inputs
    ``ml/data/processed/certificates/{train,val,test}.csv``
        Stratified 70/15/15 split index written by
        ``python -m ml.training.download_certificates`` (raw images are git-ignored).

Outputs (what the backend loads — see ``app/services/certificate_forensics.py``)
    ``ml/artifacts/certificate_cnn.onnx``        model (~2-6 MB)
    ``ml/artifacts/certificate_cnn.json``        sidecar: input size, mean/std,
                                                 normalisation, threshold, fake_index
    ``ml/artifacts/certificate_metrics.json``    honest metrics incl. the residual
                                                 metadata-leakage audit
    ``ml/evaluation/plots/{confusion_matrix,roc_curve}.png``

Honesty note: the dataset's two classes differ in resolution and orientation, so a
logistic regression on width/height/file-size alone reaches a high ROC-AUC.  We
therefore rescale every image to a common short side and rotate landscape scans
upright *before* training, re-measure the residual leakage, and record it in the
metrics file.  The backend treats the CNN as a secondary signal, capped at MEDIUM
severity, regardless of the numbers printed here.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parent.parent                     # ml/
REPO_ROOT = ML_DIR.parent
PROCESSED_DIR = ML_DIR / "data" / "processed" / "certificates"
NORMALISED_DIR = PROCESSED_DIR / "normalised"
ARTIFACTS_DIR = ML_DIR / "artifacts"
PLOTS_DIR = ML_DIR / "evaluation" / "plots"

KAGGLE_SLUG = "godzilla04/internship-certificates"

# ---------------------------------------------------------------------------
# Config (mirrors the notebook)
# ---------------------------------------------------------------------------
SEED = 42
IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
CLASSES = ["real", "fake"]          # index 0 = genuine, index 1 = forged
EPOCHS = 25
BATCH_SIZE = 16
LR = 3e-4
WARMUP_EPOCHS = 3
PATIENCE = 6
TARGET_FPR = 0.05                   # threshold policy: <=5% false positives on genuine

NORMALISE_MAX_SIDE = 384
NORMALISE_ORIENTATION = True

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def log(message: str = "") -> None:
    print(message, flush=True)


# ---------------------------------------------------------------------------
# Data: split index -> size/orientation-normalised images
# ---------------------------------------------------------------------------
def load_split(split: str):
    """Return the split's DataFrame with repo-resolved absolute paths."""
    import pandas as pd

    csv_path = PROCESSED_DIR / f"{split}.csv"
    if not csv_path.exists():
        sys.exit(
            f"Missing {csv_path}.\n"
            "Prepare the dataset first:  python -m ml.training.download_certificates"
        )
    frame = pd.read_csv(csv_path)
    frame["path"] = frame["path"].map(
        lambda p: p if Path(p).is_absolute() else str(REPO_ROOT / p)
    )
    missing = [p for p in frame["path"] if not Path(p).exists()]
    if missing:
        sys.exit(
            f"{len(missing)} indexed images are missing (e.g. {missing[0]}).\n"
            "Re-run:  python -m ml.training.download_certificates"
        )
    return frame


def normalise_split(frame, split: str):
    """Rescale to a common short side and rotate landscape scans upright.

    Removes the resolution/orientation shortcut the raw dataset leaks; mirrors the
    notebook's ``normalise_dataset`` exactly (JPEG q92, same naming scheme).
    """
    from PIL import Image

    out_dir = NORMALISED_DIR / split
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, rotated = [], 0
    for row in frame.to_dict("records"):
        source = Path(row["path"])
        destination = out_dir / f"{int(row['label'])}_{row['md5'][:8]}_{source.stem}.jpg"
        if not destination.exists():
            with Image.open(source) as handle:
                image = handle.convert("RGB")
                if NORMALISE_ORIENTATION and image.width > image.height:
                    image = image.transpose(Image.ROTATE_90)
                    rotated += 1
                scale = NORMALISE_MAX_SIDE / max(1, min(image.size))
                new_size = (
                    max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)),
                )
                image = image.resize(new_size, Image.LANCZOS)
                image.save(destination, format="JPEG", quality=92)
        with Image.open(destination) as check:
            width, height = check.size
        rows.append(
            {
                "path": str(destination),
                "label": int(row["label"]),
                "width": width,
                "height": height,
                "bytes": destination.stat().st_size,
            }
        )
    if rotated:
        log(f"[data] rotated {rotated} landscape scans upright ({split})")
    import pandas as pd

    return pd.DataFrame(rows)


def metadata_leakage_auc(frame) -> float:
    """5-fold ROC-AUC of logistic regression on width/height/bytes alone.

    High values mean the *file properties* separate the classes — the honest
    'shortcut risk' the report must disclose.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )
    return float(
        cross_val_score(
            pipe,
            frame[["width", "height", "bytes"]].values,
            frame["label"].values,
            cv=5,
            scoring="roc_auc",
        ).mean()
    )


# ---------------------------------------------------------------------------
# Transforms / loaders (mirrors the notebook)
# ---------------------------------------------------------------------------
def build_loaders(train_df, val_df, test_df):
    import torch
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms
    from torchvision.transforms import InterpolationMode

    class JPEGRecompress:
        """Randomly re-save through JPEG so 'clean PNG' is not a class shortcut."""

        def __init__(self, qualities=(55, 95), p=0.5):
            self.qualities = qualities
            self.p = p

        def __call__(self, image):
            if random.random() > self.p:
                return image
            buffer = io.BytesIO()
            image.convert("RGB").save(
                buffer, format="JPEG", quality=random.randint(*self.qualities)
            )
            buffer.seek(0)
            return Image.open(buffer).convert("RGB")

    train_tf = transforms.Compose(
        [
            JPEGRecompress(p=0.5),
            transforms.Resize((IMG_SIZE, IMG_SIZE), interpolation=InterpolationMode.BICUBIC),
            transforms.RandomApply([transforms.RandomRotation(degrees=7, fill=255)], p=0.5),
            transforms.RandomAffine(
                degrees=0, translate=(0.03, 0.03), scale=(0.95, 1.05), fill=255
            ),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.15),
            transforms.RandomApply([transforms.GaussianBlur(3, sigma=(0.1, 1.5))], p=0.25),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )

    eval_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE), interpolation=InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ]
    )

    class CertificateDataset(Dataset):
        def __init__(self, frame, transform):
            self.paths = frame["path"].tolist()
            self.labels = frame["label"].astype(int).tolist()
            self.transform = transform

        def __len__(self):
            return len(self.paths)

        def __getitem__(self, index):
            with Image.open(self.paths[index]) as image:
                image = image.convert("RGB")
            return self.transform(image), self.labels[index]

    workers = min(2, os.cpu_count() or 1)
    return {
        "train": DataLoader(
            CertificateDataset(train_df, train_tf),
            batch_size=BATCH_SIZE, shuffle=True, num_workers=workers,
        ),
        "val": DataLoader(
            CertificateDataset(val_df, eval_tf),
            batch_size=BATCH_SIZE, shuffle=False, num_workers=workers,
        ),
        "test": DataLoader(
            CertificateDataset(test_df, eval_tf),
            batch_size=BATCH_SIZE, shuffle=False, num_workers=workers,
        ),
    }


# ---------------------------------------------------------------------------
# Model + training
# ---------------------------------------------------------------------------
def build_model(device):
    import torch.nn as nn
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    pretrained = False
    try:
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        pretrained = True
        log("[model] ImageNet weights loaded — transfer learning enabled.")
    except Exception as error:  # noqa: BLE001 - any download/network failure
        model = mobilenet_v3_small(weights=None)
        log(f"[model] WARNING: could not load ImageNet weights ({type(error).__name__}: {error})")
        log("[model] WARNING: training from scratch — expect much weaker accuracy.")

    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(CLASSES))
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    return model.to(device), pretrained


def train(model, loaders, train_df, device, log_every: int = 1):
    import torch
    import torch.nn as nn
    from sklearn.metrics import f1_score, roc_auc_score

    counts = train_df["label"].value_counts().to_dict()
    class_weights = torch.tensor(
        [len(train_df) / (2 * counts[0]), len(train_df) / (2 * counts[1])],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=LR, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    history: list[dict] = []
    best = {"val_loss": float("inf"), "epoch": -1, "state": None}

    def run_epoch(loader, training):
        model.train(training)
        losses, probs, targets = [], [], []
        with torch.set_grad_enabled(training):
            for images, labels in loader:
                images, labels = images.to(device), labels.to(device)
                logits = model(images)
                loss = criterion(logits, labels)
                if training:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                losses.append(loss.item() * labels.size(0))
                probs.append(torch.softmax(logits, dim=1)[:, 1].detach().cpu())
                targets.append(labels.detach().cpu())
        probs = torch.cat(probs).numpy()
        targets = torch.cat(targets).numpy()
        return sum(losses) / len(targets), probs, targets

    for epoch in range(1, EPOCHS + 1):
        if epoch == WARMUP_EPOCHS + 1:
            for parameter in model.features.parameters():
                parameter.requires_grad = True
            optimizer = torch.optim.AdamW(model.parameters(), lr=LR / 5, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=EPOCHS - epoch
            )
            log(f"[train] --- epoch {epoch}: unfroze backbone, lr={LR / 5} ---")

        train_loss, _, _ = run_epoch(loaders["train"], True)
        val_loss, val_probs, val_targets = run_epoch(loaders["val"], False)
        val_f1 = f1_score(val_targets, (val_probs >= 0.5).astype(int), zero_division=0)
        val_auc = (
            roc_auc_score(val_targets, val_probs)
            if len(set(val_targets.tolist())) > 1
            else float("nan")
        )
        scheduler.step()

        history.append(
            {
                "epoch": epoch,
                "train_loss": round(float(train_loss), 4),
                "val_loss": round(float(val_loss), 4),
                "val_f1": round(float(val_f1), 4),
                "val_auc": round(float(val_auc), 4),
            }
        )
        if epoch % log_every == 0 or epoch == 1:
            log(
                f"[train] ep {epoch:02d} | train {train_loss:.4f} | val {val_loss:.4f} | "
                f"f1 {val_f1:.3f} | auc {val_auc:.3f}"
            )

        if val_loss < best["val_loss"]:
            best = {
                "val_loss": float(val_loss),
                "epoch": epoch,
                "state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            }
        elif epoch - best["epoch"] >= PATIENCE:
            log(f"[train] early stop at epoch {epoch} (best epoch {best['epoch']})")
            break

    model.load_state_dict(best["state"])
    log(
        f"[train] restored best epoch {best['epoch']} | val_loss {best['val_loss']:.4f}"
    )
    return run_epoch, history, best


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_onnx(model, loaders, device, threshold: float, pretrained: bool,
                n_train: int, metrics: dict) -> None:
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = ARTIFACTS_DIR / "certificate_cnn.onnx"

    model.eval()
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=device)
    torch.onnx.export(
        model,
        dummy,
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
    )
    onnx.checker.check_model(onnx.load(str(onnx_path)))

    # Cross-check ONNX against PyTorch on a real test batch.
    sample_images = next(iter(loaders["test"]))[0].to(device)
    with torch.no_grad():
        torch_probs = torch.softmax(model(sample_images), dim=1).cpu().numpy()

    session = ort.InferenceSession(
        str(onnx_path), providers=["CPUExecutionProvider"]
    )
    input_name = session.get_inputs()[0].name
    raw_logits = session.run(None, {input_name: sample_images.cpu().numpy()})[0]
    exp = np.exp(raw_logits - raw_logits.max(axis=1, keepdims=True))
    onnx_probs = exp / exp.sum(axis=1, keepdims=True)
    parity = float(np.abs(torch_probs - onnx_probs).max())
    log(f"[export] max |torch - onnx| p: {parity:.6f}")
    metrics["onnx_parity_max_abs_diff"] = parity

    sidecar = {
        "model_file": onnx_path.name,
        "input_size": IMG_SIZE,
        "mean": MEAN,
        "std": STD,
        "normalise_max_side": NORMALISE_MAX_SIDE,
        "normalise_orientation": NORMALISE_ORIENTATION,
        "classes": CLASSES,
        "fake_index": 1,
        "threshold": threshold,
        "trained_on": KAGGLE_SLUG,
        "pretrained": pretrained,
        "n_train": int(n_train),
        "framework": f"torch {torch.__version__} / onnxruntime {ort.__version__}",
    }
    with open(ARTIFACTS_DIR / "certificate_cnn.json", "w", encoding="utf-8") as handle:
        json.dump(sidecar, handle, indent=2)
    with open(ARTIFACTS_DIR / "certificate_metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)

    log(f"[export] wrote {onnx_path} ({onnx_path.stat().st_size // 1024} KB)")
    log("[export] wrote certificate_cnn.json, certificate_metrics.json")


def save_plots(test_targets, test_probs, threshold: float) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns
    from sklearn.metrics import confusion_matrix, roc_curve

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    predictions = (test_probs >= threshold).astype(int)

    confusion = confusion_matrix(test_targets, predictions)
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    sns.heatmap(
        confusion, annot=True, fmt="d", cmap="Greens",
        xticklabels=CLASSES, yticklabels=CLASSES, ax=ax,
    )
    ax.set_xlabel("predicted")
    ax.set_ylabel("actual")
    ax.set_title("Certificate CNN - test set")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "confusion_matrix.png", dpi=150)
    plt.close(fig)

    if len(set(np.asarray(test_targets).tolist())) > 1:
        fpr, tpr, _ = roc_curve(test_targets, test_probs)
        fig, ax = plt.subplots(figsize=(4.2, 3.6))
        auc = metrics_roc_auc(test_targets, test_probs)
        ax.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
        ax.plot([0, 1], [0, 1], "--", color="grey")
        ax.set_xlabel("false positive rate")
        ax.set_ylabel("true positive rate")
        ax.legend()
        ax.set_title("ROC - test set")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "roc_curve.png", dpi=150)
        plt.close(fig)
    log(f"[export] wrote plots to {PLOTS_DIR}")


def metrics_roc_auc(targets, probs) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(targets, probs))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-audit", action="store_true",
        help="Skip the (slow) metadata-leakage audit before training.",
    )
    args = parser.parse_args()

    import numpy as np
    import pandas as pd
    import torch
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_recall_fscore_support,
    )
    from sklearn.model_selection import train_test_split

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"[env] torch {torch.__version__} | device={device}")

    # 1. Split index (from download_certificates) -> normalised images.
    train_raw, val_raw, test_raw = (load_split(s) for s in ("train", "val", "test"))
    all_raw = pd.concat([train_raw, val_raw, test_raw], ignore_index=True)
    log(
        f"[data] {len(all_raw)} images "
        f"(real={int((all_raw['label'] == 0).sum())}, fake={int((all_raw['label'] == 1).sum())})"
    )

    raw_auc = None if args.skip_audit else metadata_leakage_auc(all_raw)
    train_df = normalise_split(train_raw, "train")
    val_df = normalise_split(val_raw, "val")
    test_df = normalise_split(test_raw, "test")
    normalised_auc = None if args.skip_audit else metadata_leakage_auc(
        pd.concat([train_df, val_df, test_df], ignore_index=True)
    )
    if raw_auc is not None:
        log(f"[audit] metadata ROC-AUC raw       : {raw_auc:.3f}  (shortcut risk)")
        log(f"[audit] metadata ROC-AUC normalised: {normalised_auc:.3f}  (residual)")
        log(f"[audit] leakage removed            : {raw_auc - normalised_auc:+.3f}")
        if normalised_auc > 0.80:
            log("[audit] >>> residual leakage still high — CNN stays a WEAK signal.")

    for name, part in [("train", train_df), ("val", val_df), ("test", test_df)]:
        counts = part["label"].value_counts().to_dict()
        log(f"[data] {name:5s} n={len(part):4d}  real={counts.get(0, 0):3d}  fake={counts.get(1, 0):3d}")

    # 2. Loaders + model.
    loaders = build_loaders(train_df, val_df, test_df)
    model, pretrained = build_model(device)

    # 3. Train (warm-up head, then fine-tune; early stop on val loss).
    run_epoch, history, best = train(model, loaders, train_df, device)

    # 4. Test evaluation.
    _, val_probs, val_targets = run_epoch(loaders["val"], False)
    _, test_probs, test_targets = run_epoch(loaders["test"], False)
    test_pred = (test_probs >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        test_targets, test_pred, average="binary", zero_division=0
    )
    has_both_classes = len(set(test_targets.tolist())) > 1

    # 5. Threshold policy (validation only): keep FPR on genuine <= 5%, min 0.5.
    genuine_val_probs = val_probs[val_targets == 0]
    real_safe = (
        float(np.quantile(genuine_val_probs, 1.0 - TARGET_FPR))
        if len(genuine_val_probs)
        else 0.5
    )
    chosen_threshold = float(round(max(real_safe, 0.5), 2))
    safe_pred = (test_probs >= chosen_threshold).astype(int)
    genuine_mask = test_targets == 0
    log(f"[threshold] chosen={chosen_threshold:.2f} (target FPR<={TARGET_FPR:.0%} on genuine val)")

    metrics = {
        "dataset": KAGGLE_SLUG,
        "n_train": int(len(train_df)),
        "n_val": int(len(val_df)),
        "n_test": int(len(test_df)),
        "accuracy": float(accuracy_score(test_targets, test_pred)),
        "precision_fake": float(precision),
        "recall_fake": float(recall),
        "f1_fake": float(f1),
        "roc_auc": float(metrics_roc_auc(test_targets, test_probs)) if has_both_classes else None,
        "confusion_matrix": confusion_matrix_list(test_targets, test_pred),
        "metadata_only_roc_auc": raw_auc,
        "metadata_only_roc_auc_normalised": normalised_auc,
        "pretrained": pretrained,
        "normalise_images": True,
        "normalise_max_side": NORMALISE_MAX_SIDE,
        "normalise_orientation": NORMALISE_ORIENTATION,
        "threshold_used": chosen_threshold,
        "genuine_flagged_as_forged": int(((safe_pred == 1) & genuine_mask).sum()),
        "n_genuine_test": int(genuine_mask.sum()),
        "history": history,
        "best_epoch": int(best["epoch"]),
        "trained_locally_on": str(device),
    }
    log(f"[eval] accuracy={metrics['accuracy']:.3f}  fake-f1={f1:.3f}  "
        f"roc_auc={metrics['roc_auc']}  metadata-leak={normalised_auc and round(normalised_auc, 3)}")

    # 6. Export ONNX + sidecar + metrics + plots.
    export_onnx(
        model, loaders, device, chosen_threshold, pretrained, len(train_df), metrics
    )
    save_plots(test_targets, test_probs, chosen_threshold)
    log("[done] Backend can now load the vision signal (restart FastAPI to pick it up).")


def confusion_matrix_list(targets, predictions):
    from sklearn.metrics import confusion_matrix

    return confusion_matrix(targets, predictions).tolist()


if __name__ == "__main__":
    main()
