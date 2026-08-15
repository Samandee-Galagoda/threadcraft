# ml/data/

**No datasets are committed to this repo** (see the root `.gitignore`). Everything is pulled at
runtime by the notebooks in `ml/classifier/` and `ml/fit-recommender/`.

| Dataset | Where it comes from | Used by |
|---|---|---|
| `ashraq/fashion-product-images-small` | Hugging Face Hub — 44,072 rows, MIT, no credentials needed | classifier · `01_data_cleaning` |
| `<your-user>/threadcraft-garments-cleaned` | Produced by classifier `01`, consumed by classifier `02` | classifier · `02_train` |
| RentTheRunway (Clothing Fit, Misra et al. 2018) | Direct HTTPS from the UCSD McAuley Lab — 192,544 rows, CC BY 4.0, no login | fit-recommender · `01_data_cleaning` |
| `<your-user>/threadcraft-fit-cleaned` | Produced by fit-recommender `01`, consumed by fit-recommender `02` | fit-recommender · `02_train` |

Setup: [`docs/deployment/kaggle-huggingface-guide.md`](../../docs/deployment/kaggle-huggingface-guide.md)

If you do download data here for local experimentation, it stays untracked — the `.gitignore`
rule is `ml/data/*` with an exception for this README.
