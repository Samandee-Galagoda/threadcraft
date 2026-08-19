# Image credits

Photography is from [Pexels](https://www.pexels.com). The
[Pexels License](https://www.pexels.com/license/) permits free use for
commercial and personal projects, allows modification, and does not require
attribution — these are recorded anyway so the provenance of every asset in the
repository is traceable.

| File | Pexels photo | Subject |
|---|---|---|
| `frontend/public/img/about-atelier.jpg` | [6461121](https://www.pexels.com/photo/6461121/) | Tailor cutting cloth in a workshop |
| `frontend/public/img/about-measure.jpg` | [2974113](https://www.pexels.com/photo/2974113/) | Measuring tape over a dress form |
| `frontend/public/img/about-tailor.jpg` | [16468623](https://www.pexels.com/photo/16468623/) | Tailor at work among fabric rolls |

All three were requested from the Pexels CDN pre-cropped to the aspect ratio the
layout uses, rather than downloaded full-size and cropped in CSS — 188 KB for
the set, against ~630 KB for the same images at their native 1400×2100.

## How-it-works step images

| File | Pexels photo | Subject |
|---|---|---|
| `frontend/public/img/step-design.jpg` | [7147468](https://www.pexels.com/photo/7147468/) | Garment sketches pinned beside fabric |
| `frontend/public/img/step-material.jpg` | [4614195](https://www.pexels.com/photo/4614195/) | Fabric samples on a design board |
| `frontend/public/img/step-pricing.jpg` | [8030142](https://www.pexels.com/photo/8030142/) | Fabric swatches laid out with a tablet |
| `frontend/public/img/step-preview.jpg` | [7147552](https://www.pexels.com/photo/7147552/) | Fabric samples beside sketches in an atelier |

Steps 1 and 4 reuse `tshirt.jpg` and `measurement-guide.jpg`, which the repo
already carried, rather than downloading near-duplicates.

## Material swatches

Photographed fabric swatches, shown in the design wizard, on the home page and
in the fabric catalogue dialog.

| File | Pexels photo | Fabric |
|---|---|---|
| `frontend/public/img/materials/cotton.jpg` | [7641222](https://www.pexels.com/photo/7641222/) | White woven cotton, plain weave |
| `frontend/public/img/materials/linen.jpg` | [7641150](https://www.pexels.com/photo/7641150/) | Natural linen with visible slub |
| `frontend/public/img/materials/silk.jpg` | [4863033](https://www.pexels.com/photo/4863033/) | Silk with sheen and drape |
| `frontend/public/img/materials/chiffon.jpg` | [7946560](https://www.pexels.com/photo/7946560/) | Sheer lightweight chiffon |
| `frontend/public/img/materials/satin.jpg` | [1487809](https://www.pexels.com/photo/1487809/) | Navy satin, fine weave and sheen |
| `frontend/public/img/materials/denim.jpg` | [34851013](https://www.pexels.com/photo/34851013/) | Indigo denim twill |
| `frontend/public/img/materials/velvet.jpg` | [7232401](https://www.pexels.com/photo/7232401/) | Green velvet pile |

Each was checked by eye against the fabric it claims to be before use — the
first pass returned eyelet lace for chiffon, a loose knit for cotton, and a
flower arrangement for silk, none of which a customer could have identified.
Requested as 420x420 crops, the size the swatch renders at: 308 KB for all seven.
