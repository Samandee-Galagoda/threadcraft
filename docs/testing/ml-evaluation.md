# ML evaluation — what shipped, what didn't, and why

Four models are integrated into ThreadCraft. Three are surfaced to customers.
The fourth — the size/fit recommender — was trained, published, evaluated in two
different framings, and **deliberately not surfaced**. This document records that
decision and the evidence behind it.

| Model | Trained here? | Surfaced to customers? |
|---|---|---|
| FLUX.1-schnell (Cloudflare Workers AI) | No — pretrained | Yes, Step 6 mockups |
| `threadcraft-measurement-predictor` | Yes | Yes, Step 4 estimate + validate |
| `threadcraft-garment-classifier` | Yes | Local/self-hosted only — see §3 |
| `threadcraft-fit-recommender` | Yes | **No** — see §2 |

---

## 1. Method

Every claim below was measured against the **deployed artefact**, loaded from the
Hugging Face Hub exactly as production loads it, not against a notebook copy.
Sweeps hold one variable fixed and vary another, because a model that gives a
plausible answer for one body can still be incoherent as a function of body size,
and single-point checks cannot detect that.

That distinction is the reason the problem in §2 survived training. The training
notebook's own sanity check (`02_train.ipynb`, cell 21) compares exactly **two**
bodies and asserts the predicted size is non-decreasing. Two points cannot
distinguish a monotonic function from a non-monotonic one, and it passed.

---

## 2. The fit recommender: two framings, both rejected

### 2.1 Model card baseline

The published card is already candid: on a 3,000-order held-out evaluation,
sweeping candidate sizes and taking the highest `P(fit)` gives

| Metric | Value |
|---|---|
| Exact size match | **0.036** |
| Within ±1 size | 0.186 |
| Within ±2 sizes | 0.434 |
| Macro F1 (small/fit/large) | 0.4051 vs 0.2830 majority baseline |
| Balanced accuracy | 0.3960 vs 0.3333 chance |

The macro-F1 lift is real (+43% relative). The size-sweep numbers are not.

### 2.2 Framing A — size recommendation. Rejected: non-monotonic.

`POST /api/ml/recommend-size` swept `candidate_sizes` and returned the top three
by `P(fit)`. Holding height at 170 cm and varying weight:

| Body | Top "recommended" size |
|---|---|
| 170 cm / 45 kg | 27 |
| 170 cm / 55 kg | 0 |
| 170 cm / 65 kg | 15 |
| 170 cm / 75 kg | 17 |
| 170 cm / 85 kg | 7 |
| 170 cm / 95 kg | 7 |
| 170 cm / 105 kg | 7 |

The recommendation is not a monotonic function of body size, and the extremes are
reversed: the smallest body is given the largest size. Two structural causes:

1. **`size` is the raw RentTheRunway numeric field**, carried through cleaning by
   `parse_numeric` with no rescaling or binning. It is a rental-platform size code
   that mixes garment systems, not a consistent dress size. The model card defers
   the mapping to "the application layer"; that mapping does not exist because no
   defensible one does.
2. **Two of the seven numeric features were unreachable from the API.**
   `bust_band` and `bust_cup` had no field on the request schema, so every
   production prediction ran with them missing and the sweep rode on the learned
   NaN split directions.

The endpoint was withdrawn. `tests/test_api_ml.py::test_the_size_sweep_is_no_longer_reachable`
pins it at 404 so it cannot return by accident.

### 2.3 Framing B — fit-risk advisory. Also rejected: inverted direction.

Cause (2) above is fixable, and the model card names a narrower intended use:

> "A **fit-risk advisory** for a made-to-measure ordering flow: flagging that a
> given size is likely to run small or large for this body."

That question is in-distribution — it is what the model was trained to answer —
so it was implemented (`app/services/fit.py`, `ml.assess_fit_risk`) and the two
missing features were exposed on the request schema.

It was then tested against the only hypothesis that makes it useful: **for a fixed
size, a larger body should be more likely to find it too small.**

`P(runs_small)`, height fixed at 165 cm, garment `dress`:

| weight (kg) | size 4 | size 8 | size 12 | size 16 | size 20 |
|---|---|---|---|---|---|
| 45 | 0.136 | 0.111 | 0.141 | 0.180 | 0.139 |
| 55 | 0.193 | 0.206 | 0.282 | 0.346 | 0.388 |
| 65 | 0.088 | 0.131 | 0.207 | 0.386 | 0.442 |
| 75 | 0.090 | 0.090 | 0.100 | 0.212 | 0.259 |
| 85 | 0.082 | 0.073 | 0.078 | 0.123 | 0.163 |
| 95 | 0.107 | 0.095 | 0.084 | 0.107 | 0.143 |
| 105 | 0.041 | 0.035 | 0.031 | 0.041 | **0.057** |

`P(runs_small)` **falls** as body size rises, at every one of the five sizes. A
105 kg customer is the *least* likely to be warned that a size runs small. The
relationship is not merely weak, it is backwards.

Supplying the previously-missing `bust_band` / `bust_cup`, scaled realistically
with the body, does not repair it — size 12, height 165 cm:

| weight / bra | P(runs_small) | P(fits) | P(runs_large) |
|---|---|---|---|
| 45 kg · 30A | 0.199 | 0.442 | 0.359 |
| 55 kg · 32B | 0.353 | 0.377 | 0.269 |
| 65 kg · 34B | 0.183 | 0.521 | 0.296 |
| 75 kg · 36C | 0.094 | 0.482 | 0.423 |
| 85 kg · 38D | 0.111 | 0.600 | 0.289 |
| 95 kg · 40DD | 0.105 | 0.621 | 0.274 |
| 105 kg · 42DD | 0.040 | 0.740 | 0.220 |

Still monotonically decreasing where it should increase.

### 2.4 Why the model is like this

The RentTheRunway `fit` label records how a renter felt about **the size they
themselves chose**, not how a given size maps to a given body. Renters
self-select: someone who habitually orders well for their body reports "fit"
regardless of their size. The model therefore learns *"who reports satisfaction"*,
not *"which size suits this body"* — and satisfaction correlates with the renter,
not with any size/body relationship we could act on. This is
[selection bias](https://en.wikipedia.org/wiki/Selection_bias) in the label, and
no amount of feature engineering at inference time removes it.

### 2.5 Decision

**The fit recommender is not surfaced to customers in any framing.**

The alternative — shipping a directional claim that a marker could falsify in two
minutes by entering two body weights — is a considerably worse outcome than an
absent feature. The model, its card, its dataset and its metrics remain published
as ML artefacts; what is withdrawn is the product claim.

`POST /api/ml/fit-risk` is retained as the evaluation surface that produced the
tables above, so the finding is reproducible against the live deployment. It is
not called from the wizard.

**If it were to be revisited**, the fix is at training time, not integration
time: restrict to a single garment category, normalise `size` within brand and
category, and evaluate against the monotonicity criterion in §2.3 rather than a
two-point directional assert.

---

## 3. The garment classifier: a hosting constraint, not a model failure

`threadcraft-garment-classifier` (fine-tuned `google/vit-base-patch16-224-in21k`,
25 classes, accuracy 0.6875 / macro-F1 0.3482) works. It cannot be hosted on this
project's budget.

| Option | Verdict |
|---|---|
| Render free web service | 512 MB RAM; torch ≈ 800 MB installed + ViT ≈ 350 MB resident. Does not fit. |
| HF Inference Providers | `inferenceProviderMapping` for this repo is `{}` — no provider serves it. |
| HF Space, CPU Gradio/Docker | Now requires a PRO subscription for personal accounts. |
| HF Space, ZeroGPU (the free tier) | Requires an account **older than 30 days**; this account was created 2026-08-15. Ineligible until mid-September. |
| Browser-side ONNX (transformers.js) | Feasible, but ≈ 90 MB per visitor and a new frontend dependency. |

**Decision:** the classifier runs locally (`requirements-classifier.txt`,
`ML_ENABLE_CLASSIFIER=true`) and is demonstrated from a local instance. The
deployed site reports it as unavailable *explicitly*, rather than silently
rendering nothing as it previously did.

This is a deployment-economics constraint on a working model, and it is stated as
such rather than presented as a finished feature.

### 3.1 Distribution shift, and the filter it forced

Running the model locally exposed a second problem, unrelated to hosting.

Measured on the **catalogue images it was trained on** (60×80 product shots,
white background), top-1 accuracy is **16/24 = 0.67**, consistent with the model
card's reported 0.6875. Measured on **ThreadCraft's own photographs** — ordinary
lifestyle images, which is exactly what a customer uploads — it is **1/8 =
0.125**, and it fails confidently:

| Photo | Raw top prediction |
|---|---|
| `dress.jpg` | **Bra** (0.55) |
| `kurta.jpg` | **Bra** (0.68) |
| `skirt.jpg` | **Bra** (0.59) |
| `tshirt.jpg` | Kurtas (0.61) |

The model card anticipates the cause: the training images are 60×80 catalogue
photographs, so the network learns silhouette on a plain background and does not
transfer to real photographs. Note also that ThreadCraft does not tailor
underwear at all — `Bra`, `Briefs`, `Trunk` and `Innerwear Vests` are among the
25 retail classes, so those suggestions are wrong *by construction* regardless
of the image.

Two guards were therefore added to `POST /api/ml/classify-garment`:

1. **Only surface labels that map to a garment ThreadCraft tailors.** An
   unmatched top prediction means no suggestion, not a suggestion the shop
   cannot fulfil.
2. **A confidence floor of 0.35.** Correct in-distribution predictions mostly
   score 0.5–0.96 while mistakes sit at 0.23–0.49; the sellable labels surviving
   guard (1) on real photographs score 0.04–0.26. Below the floor the model is
   guessing, and "that looks like a Kurta (4% confidence)" is noise presented as
   advice.

Measured effect on what a customer is actually shown:

| Input set | Suggestions offered | Correct |
|---|---|---|
| Catalogue images (12) | 6 | **6** |
| Real photographs (8) | 1 | 0 |

Precision of a *shown* suggestion rises from 0.67 (raw top-1) to **6/7 ≈ 0.86**,
at the cost of staying silent more often. For an assistive default the customer
can override, that is the right trade: a wrong suggestion costs more than an
absent one.

A side effect worth noting — the original label matcher compared `"Tshirts"`
against the catalogue name `"T-shirt"` by substring and never matched, so the
classifier could never have suggested a T-shirt. Both sides are now normalised
(case, punctuation, trailing plural) and compared against the slug as well.

**For the demo: use catalogue-style images** — a single garment, plain
background. On a lifestyle photograph the honest outcome is silence.

---

## 4. What this cost, and what it bought

Two features were removed from the product as a result of this evaluation. In
exchange the project can state, with evidence, which of its models are
trustworthy and which are not — which is a stronger claim than four models
nominally "integrated". A model that is wrong in a way the user cannot detect is
worse than no model.
