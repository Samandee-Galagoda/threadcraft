# ml/data/

Raw and intermediate datasets are **not** committed to this repo (see `.gitignore`) — they're pulled directly from the Hugging Face Hub inside the notebooks in `ml/notebooks/`.

| Dataset | Source | Role |
|---|---|---|
| `ashraq/fashion-product-images-small` | HF Hub (mirror of Kaggle `paramaggarwal/fashion-product-images-small`) | Raw input to the garment category classifier |
| `<your-hf-username>/threadcraft-fashion-cleaned` | Pushed by `01_dataset_prep_and_clean.ipynb` | Cleaned, stratified-split version consumed by the training notebook |
| RentTheRunway split of `rmisra/clothing-fit-dataset-for-size-recommendation` | McAuley Lab direct download (bypasses Kaggle) | Size/fit recommender training data |

See `docs/deployment/kaggle-huggingface-guide.md` for how to run the notebooks that produce these.
