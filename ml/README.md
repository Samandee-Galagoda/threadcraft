# ThreadCraft — Machine Learning

Three models, each in its own folder, each with a **data cleaning** notebook and a **training**
notebook. Run them in numeric order.

```
ml/
├── classifier/                 Model 1 — garment type from a reference image
│   ├── 01_data_cleaning.ipynb  CPU · cleans + splits + pushes dataset to HF
│   └── 02_train.ipynb          GPU T4 x2 · fine-tunes ViT, pushes model to HF
├── measurement-predictor/      Model 2 — predict + validate body measurements
│   ├── 01_data_cleaning.ipynb  CPU · ANSUR II, unit conversion, pushes to HF
│   └── 02_train.ipynb          CPU · 13 regressors, pushes model to HF
├── fit-recommender/            Model 3 — will this size run small / fit / large?
│   ├── 01_data_cleaning.ipynb  CPU · downloads, parses, cleans, pushes to HF
│   └── 02_train.ipynb          CPU · gradient boosting, pushes model to HF
└── data/                       (no data committed — see data/README.md)
```

**Only `classifier/02_train.ipynb` needs a GPU.** The other five run on CPU in minutes — run them
with the accelerator set to None to protect your weekly quota.

### If you only have time for two

Run **Model 1** and **Model 2**. Model 2 is the stronger result (R² 0.82, MAE ~1.2 cm) and
addresses a limitation the proposal itself names. Model 3 is honest but modest (macro F1 0.41)
and is best presented as a supporting experiment — see its README for why.

Setup steps for Kaggle + the Hugging Face token:
**[`docs/deployment/kaggle-huggingface-guide.md`](../docs/deployment/kaggle-huggingface-guide.md)**

## Before you run anything

1. Kaggle account with **phone verification completed** (required for GPU *and* internet)
2. Hugging Face account + a **Write** token
3. The token added as a Kaggle Secret named **`HF_TOKEN`**, attached to each notebook
4. In every notebook, set `HF_USERNAME` to your Hugging Face username

> Always run with **Save & Run All (Commit)**, never interactively — an interactive Kaggle
> session dies when you close the tab, and you lose the GPU hours with nothing to show.

## Model 1 — Garment classifier

| | |
|---|---|
| **Question** | Given a customer's uploaded reference photo, which garment is this? |
| **Dataset** | [`ashraq/fashion-product-images-small`](https://huggingface.co/datasets/ashraq/fashion-product-images-small) — 44,072 rows, MIT, no Kaggle credentials needed |
| **Filtered to** | `masterCategory == "Apparel"`, target `articleType` |
| **Base model** | `google/vit-base-patch16-224-in21k` |
| **Accelerator** | `01` CPU · `02` **GPU T4 x2** |
| **Runtime** | `01` a few minutes · `02` roughly 25–50 min |
| **Headline metric** | macro F1 (the class distribution is long-tailed) |

Restricting to Apparel and predicting `articleType` is deliberate: the raw dataset includes
watches, handbags and deodorant, and a model trained on all 141 classes mostly predicts watches.
The Apparel-only label set maps directly onto ThreadCraft's own cloth types.

## Model 2 — Measurement predictor & validator

| | |
|---|---|
| **Question** | From the measurements this customer *has* taken, what are the rest? And is any entry a typo? |
| **Dataset** | **ANSUR II** — 6,068 people × 93 measurements, US Army anthropometric survey |
| **Licence** | **US Government work, unlimited public release** — cleanest licence in the project |
| **Source** | Direct HTTPS from Penn State OPEN Design Lab — no login, no gating |
| **Algorithm** | 13 × `HistGradientBoostingRegressor`, one per measurement |
| **Accelerator** | **CPU for both notebooks** |
| **Headline metric** | R² and MAE in cm |

Measured results, run end-to-end on the real data:

| Scenario | Mean R² | Mean MAE |
|---|---|---|
| height + weight + age + sex only | 0.818 | 1.62 cm |
| + chest & waist | 0.819 | 1.33 cm |
| + chest, waist, hip, shoulder | 0.826 | 1.21 cm |

Validator at the 99th-percentile threshold: **2.1% false positives**, catching **98.6%** of 20%
errors and **100%** of 2× errors (e.g. inches entered instead of centimetres).

**This is the strongest of the three models**, and it addresses a limitation the proposal
explicitly names ("the platform relies on self-reported customer measurements"). Two design
choices are backed by measurement rather than assertion: masked-input training beat the simpler
alternative on **13/13** targets, and the flagging threshold was tuned across five percentiles.

Its key caveat belongs up front in the write-up: ANSUR II is **US Army personnel**, and body
proportions vary between populations. ThreadCraft serves a Sri Lankan market, so predictions are
an editable starting point, never a replacement for measuring.

## Model 3 — Size/fit recommender

| | |
|---|---|
| **Question** | For this body and this size, will the garment run small, fit, or large? |
| **Dataset** | Clothing Fit (Misra, Wan & McAuley, RecSys 2018), RentTheRunway split — 192,544 rows, CC BY 4.0 |
| **Source** | Downloaded straight from the UCSD McAuley Lab — **no Kaggle dataset attachment, no login** |
| **Algorithm** | `HistGradientBoostingClassifier` (scikit-learn) |
| **Accelerator** | **CPU for both notebooks** — do not spend GPU quota here |
| **Runtime** | a few minutes each |
| **Headline metric** | macro F1 |

### Expect a modest result, and report it honestly

This has been run end-to-end on the real data. Measured results:

| Config | Accuracy | Balanced acc. | Macro F1 |
|---|---|---|---|
| Baseline (always predict `fit`) | 0.7378 | 0.3333 | 0.2830 |
| No class weighting | 0.7373 | 0.3409 | 0.3012 |
| **sqrt-balanced** (the default) | **0.7140** | **0.3960** | **0.4051** |
| Fully balanced | 0.4001 | 0.4918 | 0.3684 |

Two things follow from this, and both belong in the dissertation:

1. **Accuracy is a trap on this dataset.** The `fit` class is ~74% of the data, so always
   predicting `fit` scores 73.8% accuracy while never once warning a customer that a size runs
   small. Quote **macro F1** (+43% relative over baseline) and balanced accuracy.
2. **The strongest predictor of fit is the specific garment**, and it is excluded by design.
   Two dresses in the same nominal size fit differently — that is precisely what Misra et al.
   modelled with latent item factors. ThreadCraft makes bespoke garments, so there is no
   catalogue item to look up. That limitation is a legitimate, citable finding, not a bug.

The training notebook runs the weighting comparison itself and writes the table to
`weighting_comparison.csv`, so the configuration choice is evidenced rather than asserted.

### The size-sweep inversion

The model scores *(body, size) → fit outcome*. ThreadCraft wants *(body) → size*, obtained by
sweeping candidate sizes and taking the highest `P(fit)`. The notebook implements this **and
measures it** (exact / ±1 / ±2 size accuracy). The numbers are modest enough that the UI must
present the output as an advisory starting point, never an authoritative size.

## What gets published to Hugging Face

Running all six notebooks produces six HF repos under your account:

| Repo | Type |
|---|---|
| `<user>/threadcraft-garments-cleaned` | dataset |
| `<user>/threadcraft-garment-classifier` | model |
| `<user>/threadcraft-measurements-cleaned` | dataset |
| `<user>/threadcraft-measurement-predictor` | model |
| `<user>/threadcraft-fit-cleaned` | dataset |
| `<user>/threadcraft-fit-recommender` | model |

Every training notebook writes a **model card** with metrics, training configuration, and an
explicit limitations section — an unlabelled weights file is not a research artefact.

## Design decisions worth defending in the viva

- **Cleaning is separated from training.** The cleaning notebook pushes a versioned, split
  dataset to the Hub; training loads it in one line. Re-running training never re-shuffles the
  split, so results are reproducible and there is no risk of accidental leakage between runs.
- **No imputation of body measurements.** ~16% of `weight_kg` is missing. Gradient boosting
  handles missing values natively; imputing a median weight would fabricate a measurement the
  customer never gave.
- **Leakage columns dropped explicitly.** `rating`, `review_text` and `review_summary` are all
  written *after* wearing the garment and are unavailable at prediction time. Including them
  would inflate the metrics with information the deployed system can never have.
- **Every push is wrapped in `try/except`** with a local fallback, because a network blip on the
  final cell should not discard a completed training run.
- **Both training notebooks verify their own upload** by downloading the pushed artefact and
  predicting with it — this catches the classic failure of pushing the model but forgetting the
  image processor or the encoder.
