# Kaggle runbook — certificate forgery CNN

Exact steps to produce `ml/artifacts/certificate_cnn.onnx` on a free Kaggle GPU.

## 0. Prerequisites

- A free [Kaggle](https://www.kaggle.com) account (phone-verified, so GPU is enabled).
- `ml/notebooks/train_certificate_cnn.ipynb` from this repo.
- ~10 minutes of wall-clock time.

## 1. Create the notebook

1. Kaggle → **Create → Notebook**.
2. **File → Import Notebook → Upload** → select `train_certificate_cnn.ipynb`.

## 2. Attach the dataset (step 2 is critical)

1. Right sidebar → **Input → Add Input → Datasets**.
2. Search `internship-certificates`, owner **godzilla04** → **+** / **Add**.
3. Confirm the mount appears at `/kaggle/input/internship-certificates` and that it
   contains the two folders:
   - `Real internship certificate/`
   - `fake internship certificate/`

The notebook's `find_dataset_root()` looks for a folder whose name contains
`real`/`fake`, so this layout is required. If Kaggle nests it one level deeper the
function still finds it by walking subdirectories.

## 3. Set the accelerator **and Internet**

1. **Settings → Accelerator → GPU T4 x2** (a single T4 or a P100 is also fine).
2. **Settings → Internet → On.**

> **Internet must be On.** Cell 9 downloads the ImageNet weights used for transfer
> learning. With Internet off, the notebook catches the failure and trains from
> scratch — it will still finish, but on ~200 training images the accuracy is far
> worse. Check the cell output for `ImageNet weights loaded -- transfer learning
> enabled.` If you see the `WARNING: could not load ImageNet weights` lines, fix the
> setting and re-run from that cell.

## 4. Run

**Run All**. Expect roughly 5–10 minutes total. What each cell proves:

| Cell | What to check in the output |
|---|---|
| 5. Shortcut check | `metadata-only ROC-AUC (5-fold)` — about **0.97** on the raw files |
| 6. Mitigation | `rotated N landscape scans upright`, then `metadata ROC-AUC after` — about **0.63** |
| 9. Model | `ImageNet weights loaded -- transfer learning enabled.` |
| 10. Training loop | `--- epoch 4: unfroze backbone ---`, then `restored best epoch:` |
| 11. Test evaluation | `accuracy`, `fake precision/recall/f1`, `roc auc` |
| 12. Threshold tuning | `CHOSEN threshold` — must be **≥ 0.50** |
| 13. Export | `max \|torch - onnx\| p` — should be tiny (≈ 1e-6 or less) |

If `metadata ROC-AUC after` is still above ~0.80, the classes remain partly
separable without reading image content — report the model as a weak signal only.

## 5. Copy the artifacts into the repo

Open the right-hand **Output** panel (or **Output → Download**) and copy these five
files into the repo:

```
certificate_cnn.onnx                    ->  ml/artifacts/certificate_cnn.onnx
certificate_cnn.json                    ->  ml/artifacts/certificate_cnn.json
certificate_metrics.json                ->  ml/evaluation/certificate_metrics.json
confusion_matrix.png                    ->  ml/evaluation/plots/certificate_confusion_matrix.png
roc_curve.png                           ->  ml/evaluation/plots/certificate_roc_curve.png
```

Then verify locally:

```bash
ls -lh ml/artifacts/certificate_cnn.onnx
python3 -c "import json;print(json.load(open('ml/artifacts/certificate_cnn.json')))"
```

The sidecar must contain `input_size` (224), `mean`, `std`, `classes`,
`fake_index` (1) and `threshold`. The backend reads all of these at runtime, so
re-tuning the threshold never requires a code change.

## 6. Save the notebook version

Kaggle → **Save Version → Save & Run All (Commit)**. That keeps a reproducible
record even before the artifacts are committed to git.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Could not locate the dataset` | Step 2 was skipped, or the folders were renamed. Check `/kaggle/input/`. |
| `WARNING: could not load ImageNet weights` | Internet is off → enable it, re-run cell 9. |
| `insufficient memory` | Lower `BATCH_SIZE` from 16 to 8 in cell 2, or pick a P100. |
| `metadata ROC-AUC after` ≈ 0.97 | `NORMALISE_IMAGES` was set to `False`; set it back to `True` in cell 2. |
| ONNX mismatch is not tiny | `model.eval()` was skipped — re-run cell 13 as-is. |
| Downloads to `/kaggle/working` missing | You ran interactively; use **Save Version → Save & Run All (Commit)** so outputs persist. |