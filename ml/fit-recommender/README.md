# Model 2 — Size/Fit Recommender

Predicts whether a garment size will run **small**, **fit**, or **large** for a given customer's
body measurements.

## Run order

| # | Notebook | Kaggle accelerator | Internet | Roughly |
|---|---|---|---|---|
| 1 | `01_data_cleaning.ipynb` | **None (CPU)** | On | 2–3 minutes |
| 2 | `02_train.ipynb` | **None (CPU)** | On | 3–5 minutes |

**Neither notebook needs a GPU.** Save the quota for the classifier. Both need the `HF_TOKEN`
Kaggle Secret attached and `HF_USERNAME` set in the config cell.

## Data source — no Kaggle dataset needed

Downloaded directly over HTTPS from the UCSD McAuley Lab:

```
https://mcauleylab.ucsd.edu/public_datasets/data/renttherunway/renttherunway_final_data.json.gz
```

192,544 records, 30.7 MB gzipped, JSON **Lines** format, CC BY 4.0. No login, no dataset
attachment, no Kaggle API credentials.

The RentTheRunway split is used rather than ModCloth from the same release because
RentTheRunway's body-measurement fields are 84–92% populated where ModCloth's fall as low as
3.5% (`waist`) and 14.3% (`bust`) — effectively unusable.

## What each notebook does

**`01_data_cleaning.ipynb`**
1. Downloads and parses the gzipped JSON Lines file
2. Parses the human-typed string fields with self-tested parsers:
   `"5' 8\""` → `172.72 cm`, `"137lbs"` → `62.14 kg`, `"34d"` → band `34` + cup `4` (ordinal)
3. Fixes real data-quality problems found by profiling: **129 implausible ages** (the dataset
   contains ages up to 117 and down to 0) and a single `'party: cocktail'` typo variant of `party`
4. Derives BMI; out-of-range numerics become `NaN` rather than dropping the row, so the row's
   other valid features remain usable
5. Builds a stratified 80/10/10 split **here**, and ships it with the dataset — training can
   therefore never accidentally reshuffle and leak
6. Pushes `<user>/threadcraft-fit-cleaned` to the Hub

**`02_train.ipynb`**
1. Runs a **class-weighting comparison** (none / sqrt / fully balanced) and prints the table
2. Trains the chosen configuration with `HistGradientBoostingClassifier`
3. Reports every metric **against the majority-class baseline**, so no number is quoted without
   its floor
4. Permutation feature importance on the test split
5. Implements the size-sweep inversion **and measures it** (exact / ±1 / ±2 size accuracy)
6. Runs a directional sanity check — a materially larger customer must be recommended a larger
   size — and `assert`s on it
7. Writes a model card, pushes to the Hub, then reloads the pushed artefact to verify it

## Expected results — this has actually been run

Measured on the real 192k-row dataset:

| Config | Accuracy | Balanced acc. | Macro F1 |
|---|---|---|---|
| Baseline (always predict `fit`) | 0.7378 | 0.3333 | 0.2830 |
| No class weighting | 0.7373 | 0.3409 | 0.3012 |
| **sqrt-balanced** (default) | **0.7140** | **0.3960** | **0.4051** |
| Fully balanced | 0.4001 | 0.4918 | 0.3684 |

**Do not quote accuracy as the result.** The `fit` class is ~74% of the data, so always
predicting `fit` scores 73.8% while never once warning a customer that a size runs small.
Macro F1 is the honest headline: **0.4051 vs 0.2830, a +43% relative improvement**.

Fully balanced weighting is deliberately *not* the default — it collapses accuracy to 0.40 for a
*worse* macro F1 than sqrt. That trade-off is exactly what the comparison table demonstrates.

Derived features (per-category-and-size historical fit rates, size-versus-typical-for-BMI) were
also tested. They improved macro F1 negligibly (0.4119 vs 0.4051) while **halving** size-sweep
accuracy (±2 dropping from 0.434 to 0.224), so they are not used.

## The limitation to lead with, not bury

The single strongest predictor of fit in this dataset is the **specific garment** (`item_id`) —
two dresses in the same nominal size fit differently. Modelling that with latent item factors was
the central contribution of Misra et al. (2018).

ThreadCraft makes **bespoke** garments, so there is no catalogue item to look up, and `item_id`
is excluded by design. That is the principal reason absolute performance is limited here, and it
is a legitimate, citable finding rather than an implementation failure.

Other limitations: the data is predominantly dresses and gowns (~70%) from a largely US female
rental customer base, so kurtas, salwar kameez and menswear are extrapolation; fit labels and
body measurements are both self-reported.

## Citation

> Misra, R., Wan, M., & McAuley, J. (2018). Decomposing fit semantics for product size
> recommendation in metric spaces. *RecSys 2018*.
