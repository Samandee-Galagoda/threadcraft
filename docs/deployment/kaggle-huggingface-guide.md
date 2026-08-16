# Running the ML notebooks on Kaggle + Hugging Face

Setup for the six notebooks in [`ml/`](../../ml/). Do steps 1–3 **once** — the same token and
secret work for every notebook.

| Notebook | Accelerator | Internet | Roughly |
|---|---|---|---|
| `ml/classifier/01_data_cleaning.ipynb` | None (CPU) | On | few min |
| `ml/classifier/02_train.ipynb` | **GPU T4 x2** | On | 25–50 min |
| `ml/measurement-predictor/01_data_cleaning.ipynb` | None (CPU) | On | 1–2 min |
| `ml/measurement-predictor/02_train.ipynb` | None (CPU) | On | 5–8 min |
| `ml/fit-recommender/01_data_cleaning.ipynb` | None (CPU) | On | 2–3 min |
| `ml/fit-recommender/02_train.ipynb` | None (CPU) | On | 3–5 min |

Only one of the six needs a GPU. Run the other five on CPU to protect your weekly quota.

## 1. Hugging Face account + token

1. Sign up / log in at https://huggingface.co
2. **Settings → Access Tokens** (https://huggingface.co/settings/tokens)
3. **New token** → name `kaggle-threadcraft`, role **Write** (write access is required to push
   the cleaned datasets and trained models)
4. Copy the `hf_...` value — you can't view it again, but you can always generate a new one

**Never paste this token into a notebook cell.** Kaggle notebooks are frequently public (or
accidentally left public), and a leaked write token lets anyone push to or delete from your HF
account. It goes into a Kaggle Secret instead — step 3.

Also note your **HF username** (https://huggingface.co/settings/profile) — it is not necessarily
the same as your Kaggle username, and every notebook's `HF_USERNAME` config must be set to it.

## 2. Kaggle account + phone verification

1. Sign up / log in at https://kaggle.com
2. **Settings → Phone Verification.** This is required before Kaggle grants GPU access *or*
   internet access inside a notebook — this project needs both. Do it first; it can take a few
   minutes to process.
3. Upload a notebook: **Create → New Notebook**, then **File → Import Notebook**, and pick the
   `.ipynb` from this repo.
4. In the notebook's right sidebar:
   - **Accelerator** — see the table above. For the classifier training notebook choose
     **GPU T4 x2**, not P100: same weekly quota cost, but T4 has fp16 tensor cores and the
     notebook sets `fp16=True`. (T4 does **not** support bf16 — don't switch it.)
   - **Internet** — **On** for all four (needed for `pip install`, HF downloads, and pushes)

## 3. Add the HF token as a Kaggle Secret

1. In the notebook editor: **Add-ons → Secrets**
2. **Add a new secret** — Label `HF_TOKEN`, Value = your `hf_...` token
3. Make sure the toggle next to `HF_TOKEN` is **on/attached for this notebook**

Secrets are **per notebook**, so you must attach it again in each of the four. The notebooks read
it with:

```python
from kaggle_secrets import UserSecretsClient
HF_TOKEN = UserSecretsClient().get_secret("HF_TOKEN")
```

(They fall back to an `HF_TOKEN` environment variable if you run them outside Kaggle.)

## 4. Set your username

At the top of each notebook:

```python
HF_USERNAME = "your-hf-username"  # <-- CHANGE THIS
```

## 5. Run headlessly — do not click through cells

Interactive sessions die when you close the tab or go idle, and you lose the GPU hours with
nothing to show for them. Instead:

1. **Save Version** (top right)
2. **Save & Run All (Commit)**
3. Kaggle re-runs the whole notebook top-to-bottom in a fresh container in the background. Close
   the browser if you like.
4. Check **Your Work → Notebooks → [notebook] → Output** for status and any written files

`/kaggle/working` persists across a commit, so if a late cell fails (e.g. the Hub push) the
earlier outputs survive — every push cell in these notebooks is wrapped in `try/except` with a
local fallback for exactly that reason. Re-run just the push cell rather than the whole notebook.

## 6. Run order and what you should see

```
classifier/01  ->  pushes  <user>/threadcraft-garments-cleaned   (dataset)
classifier/02  ->  pushes  <user>/threadcraft-garment-classifier (model)

measurement-predictor/01  ->  <user>/threadcraft-measurements-cleaned   (dataset)
measurement-predictor/02  ->  <user>/threadcraft-measurement-predictor  (model)

fit-recommender/01  ->  pushes  <user>/threadcraft-fit-cleaned      (dataset)
fit-recommender/02  ->  pushes  <user>/threadcraft-fit-recommender  (model)
```

Each `02` notebook finishes by **downloading back what it just pushed** and running a prediction,
so a successful final cell means the artefact is genuinely usable — not merely uploaded.

## 7. Weekly GPU quota

Kaggle gives roughly **30 GPU-hours per week**, sessions capped at 12 hours. Only
`classifier/02_train.ipynb` needs a GPU (25–50 min), so a full end-to-end run costs well under an
hour of quota. Running the other five on GPU by mistake is the main way to waste it.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `Secret HF_TOKEN not found` | Secret not attached to *this* notebook | Add-ons → Secrets → toggle it on |
| `401 Unauthorized` on push | Token is read-only, or expired | New token with **Write** role, update the secret |
| GPU option greyed out | Phone not verified | Settings → Phone Verification, wait, refresh |
| `pip install` / download fails | Internet toggle off | Sidebar → Internet → On |
| Notebook stops when you close the tab | Ran cells manually | Use **Save & Run All (Commit)** |
| `CUDA out of memory` | Batch too large for the T4 | Drop `BATCH_SIZE` from 64 to 32 in `classifier/02` |
| `RepositoryNotFoundError` on the cleaned dataset | `01` hasn't been run, or `HF_USERNAME` differs between the two notebooks | Run `01` first; check the username matches exactly |
| `AssertionError: expected 4082 male rows` | ANSUR II URL fetched over `http://` instead of `https://` — it silently returns an HTML page | Use the `https://` URLs already in the notebook |
| `UnicodeDecodeError` reading ANSUR II | The CSVs are `latin-1`, not UTF-8 | Already handled in the notebook — don't remove `encoding="latin-1"` |
