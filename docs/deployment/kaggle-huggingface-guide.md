# Running the ML notebooks on Kaggle + Hugging Face

Step-by-step for `ml/notebooks/01_dataset_prep_and_clean.ipynb` (and any training notebook after it). Do this once — the same token and secret work for every notebook you add.

## 1. Create your Hugging Face account + token

1. Sign up / log in at https://huggingface.co
2. Go to **Settings → Access Tokens** (https://huggingface.co/settings/tokens)
3. Click **New token**
   - Name: `kaggle-threadcraft`
   - Type/role: **Write** (you need write access to push the cleaned dataset and later the trained model)
4. Copy the token (starts with `hf_...`) — you won't be able to see it again, but you can always generate a new one.

**Never paste this token directly into a notebook cell.** Kaggle notebooks are commonly made public (or accidentally left public), and a leaked write token lets anyone push/delete under your HF account. It goes into a Kaggle **Secret** instead (next step).

## 2. Set up Kaggle

1. Sign up / log in at https://kaggle.com
2. **Verify your phone number**: Settings → Phone Verification. This is required before Kaggle will give you GPU access *or* internet access inside a notebook — both of which this project needs. Do this first; it can take a few minutes to process.
3. Create a new notebook: **Create → New Notebook**, or upload the provided one: **File → Import Notebook** → upload `ml/notebooks/01_dataset_prep_and_clean.ipynb` from this repo.
4. In the notebook's right sidebar:
   - **Accelerator**: set to **GPU T4 x2** (not P100 — same weekly quota cost, but T4 supports fp16 mixed-precision training, which is meaningfully faster)
   - **Internet**: toggle **ON** (needed to `pip install`, download from the HF Hub, and push back to it)

## 3. Add your HF token as a Kaggle Secret

1. In the notebook editor: **Add-ons → Secrets**
2. Click **Add a new secret**
   - Label: `HF_TOKEN`
   - Value: paste the `hf_...` token from step 1
3. Make sure the toggle next to `HF_TOKEN` is **on** ("Attached") for this notebook — secrets are per-notebook, you must attach it every time you create a new one.

The notebook reads it with:
```python
from kaggle_secrets import UserSecretsClient
HF_TOKEN = UserSecretsClient().get_secret("HF_TOKEN")
```

## 4. Fill in your HF username

At the top of the notebook, change:
```python
HF_USERNAME = "your-hf-username"  # <-- CHANGE THIS
```
to your actual Hugging Face username (find it at https://huggingface.co/settings/profile — it's *not* necessarily the same as your Kaggle username).

## 5. Run it properly (headless, survives closing the browser)

Don't just click through cells interactively — **interactive sessions die if you close the tab or go idle**, and you'll lose GPU-hours without a finished result. Instead:

1. Click **Save Version** (top right)
2. Choose **Save & Run All (Commit)**
3. Kaggle re-runs the entire notebook top-to-bottom in a fresh, isolated container in the background. You can close the browser — it keeps running.
4. Check back under **Your Work → Notebooks → [this notebook] → Output** for the commit status (success/failure) and any files written to `/kaggle/working/`.

If it fails partway through (e.g. the push step, due to a network blip), **you keep the outputs from every cell that succeeded before the failure** — `/kaggle/working` persists across a commit. Re-run just the failed portion rather than the whole notebook if that happens.

## 6. Verify the result

Once it succeeds, check:
- https://huggingface.co/datasets/`<your-username>`/threadcraft-fashion-cleaned — the cleaned dataset should be there with `train`/`validation`/`test` splits
- The `label2id.json` file should be listed in the repo's Files tab

## 7. Weekly GPU quota — budget it

Kaggle gives **~30 GPU-hours/week** (resets weekly), sessions capped at **12 hours**. The dataset-cleaning notebook above needs no GPU at all (it's pure data wrangling) — only run it with the **CPU** accelerator to save your GPU quota for the actual model training notebook that comes next.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `Secret HF_TOKEN not found` | Secret not attached to this specific notebook | Add-ons → Secrets → toggle it on for this notebook |
| `401 Unauthorized` pushing to HF | Token has read-only role, or expired | Generate a new token with **Write** role, update the Kaggle secret |
| GPU option greyed out | Phone not verified yet | Settings → Phone Verification, wait a few minutes, refresh |
| `No internet access` / pip install fails | Internet toggle is off | Notebook sidebar → Internet → ON |
| Notebook stops when you close the tab | You ran cells interactively instead of committing | Use **Save & Run All (Commit)**, not manual cell execution, for anything you want to survive |
