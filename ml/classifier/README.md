# Model 1 — Garment Classifier

Predicts **garment type** from a clothing image, so ThreadCraft can suggest a cloth type when a
customer uploads a reference photo at design-wizard Step 2.

## Run order

| # | Notebook | Kaggle accelerator | Internet | Roughly |
|---|---|---|---|---|
| 1 | `01_data_cleaning.ipynb` | **None (CPU)** | On | a few minutes |
| 2 | `02_train.ipynb` | **GPU T4 x2** | On | 25–50 minutes |

Both need the `HF_TOKEN` Kaggle Secret attached, and `HF_USERNAME` set in the config cell.

Run each with **Save & Run All (Commit)** so it survives closing the browser.

> Use **T4 x2**, not P100 — same weekly quota cost, but T4 has fp16 tensor cores. The notebook
> sets `fp16=True`; T4 does **not** support bf16, so don't switch it.

## What each notebook does

**`01_data_cleaning.ipynb`**
1. Loads `ashraq/fashion-product-images-small` (44,072 rows, MIT licence, no Kaggle credentials)
2. Filters to `masterCategory == "Apparel"` — drops watches, bags, footwear, fragrance
3. Drops null targets, duplicates, and classes with fewer than 100 examples
4. Builds a **stratified** 80/10/10 split, asserting no overlap between splits
5. Displays sample images with their labels and **asserts** the labels line up — a silent
   off-by-one here would train a model to a meaningless result without any error
6. Pushes `<user>/threadcraft-garments-cleaned` plus `label2id.json` to the Hub

**`02_train.ipynb`**
1. Loads the cleaned dataset in one line
2. Applies preprocessing **lazily** via `set_transform` — eager `.map()` would materialise every
   image as a 224×224×3 float tensor and exhaust Kaggle's RAM
3. Fine-tunes `google/vit-base-patch16-224-in21k`, selecting the best epoch on **validation**
   macro-F1
4. Evaluates once on the untouched **test** split: accuracy, macro F1, weighted F1, per-class
   report, normalised confusion matrix, and the top-15 most-confused class pairs
5. Writes a model card with metrics and limitations, pushes model + **image processor** to the Hub
6. Reloads the pushed model through a `pipeline` and predicts, to prove the upload is usable

## Why `articleType` restricted to Apparel

The raw dataset's 141 `articleType` classes span everything a fashion retailer sells, with a
~7,065:1 imbalance. Training on all of them yields a model that mostly predicts watches —
good-looking accuracy, useless for a tailoring platform.

Restricting to Apparel gives a label set (Tshirts, Shirts, Kurtas, Dresses, Trousers, Skirts,
Sarees, …) that maps onto ThreadCraft's own cloth-type catalogue.

Set `RESTRICT_TO_APPAREL = False` if you want the everything-included variant as a comparison
for the report.

## Reporting the results

Quote **macro F1** as the headline. The class distribution is long-tailed even after filtering,
so accuracy is inflated by the dominant Tshirts/Shirts classes while macro F1 weights every
garment type equally.

The notebook saves `confusion_matrix.png`, `sample_predictions.png` and
`classification_report.txt` — all three are dissertation figures.

## Known limitation to state explicitly

Source images are **60×80 px**, upscaled to 224×224. Fine detail (fabric texture, stitching,
small trims) is simply not in the training data, so the model distinguishes silhouette far better
than detail. It is also trained on clean catalogue product photography, so accuracy on casual
user-taken photos will be lower — which is exactly why the prediction is surfaced as an
overridable suggestion rather than an authoritative answer.
