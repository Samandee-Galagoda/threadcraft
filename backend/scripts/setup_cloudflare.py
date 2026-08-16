#!/usr/bin/env python3
"""Configure and verify Cloudflare Workers AI for garment mockup generation.

Prompts for the credentials with the token hidden, generates a real test image
to prove they work, and only then writes them to .env. Nothing lands in shell
history, and nothing is written until a generation actually succeeds.

    python scripts/setup_cloudflare.py            # interactive setup
    python scripts/setup_cloudflare.py --check    # test what's already in .env

Where to get the two values (both free, no card):
  1. https://dash.cloudflare.com  ->  AI  ->  Workers AI  ->  "Use REST API"
  2. Your Account ID is shown on that page
  3. Click "Create a Workers AI API Token", confirm, and copy the token
     (a custom token needs both `Workers AI - Read` and `Workers AI - Edit`)
"""

import argparse
import base64
import getpass
import os
import sys
import time
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_MODEL = "@cf/black-forest-labs/flux-1-schnell"
TEST_PROMPT = (
    "professional fashion product photograph of a dress, V-neck, long sleeves, "
    "burgundy silk fabric, full-length front view on a plain studio background"
)


def mask(value: str) -> str:
    if not value:
        return "(not set)"
    return f"{value[:4]}…{value[-4:]} ({len(value)} chars)" if len(value) > 12 else "(set)"


def read_env() -> dict:
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    return values


def generate(account_id: str, api_token: str, model: str = DEFAULT_MODEL):
    """Returns (image_bytes, error_message). Exactly one will be None."""
    try:
        import httpx
    except ImportError:
        return None, "httpx isn't installed — activate the venv first."

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {api_token}"},
                # `steps`, not `num_steps`, and no negative_prompt — Workers AI
                # rejects any unrecognised property with a 400.
                json={"prompt": TEST_PROMPT, "steps": 4},
            )
    except Exception as exc:
        return None, f"Request failed: {type(exc).__name__}: {exc}"

    elapsed = int((time.perf_counter() - started) * 1000)

    if response.status_code == 401:
        return None, "401 Unauthorized — the API token is wrong or lacks Workers AI permissions."
    if response.status_code == 403:
        return None, "403 Forbidden — token valid but missing `Workers AI - Edit` permission."
    if response.status_code == 404:
        return None, (
            f"404 Not Found — check the Account ID, or the model id ({model}) is unavailable on your account."
        )
    if response.status_code == 429:
        return None, "429 Rate limited — daily free neuron allowance may be exhausted."
    if response.status_code == 400:
        return None, (
            f"400 Bad input — the model rejected the request body. Credentials are "
            f"fine (this is past auth). Response: {response.text[:250]}"
        )
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}: {response.text[:300]}"

    # flux-1-schnell returns JSON with a base64 image; other models return raw bytes.
    if response.headers.get("content-type", "").startswith("application/json"):
        body = response.json()
        encoded = (body.get("result") or {}).get("image")
        if not encoded:
            return None, f"Unexpected response shape: {str(body)[:300]}"
        data = base64.b64decode(encoded)
    else:
        data = response.content

    print(f"  generated {len(data):,} bytes in {elapsed} ms")
    return data, None


def write_env(account_id: str, api_token: str) -> None:
    if not ENV_PATH.exists():
        print(f"\n{ENV_PATH} doesn't exist — create it from .env.example first.")
        return
    lines = ENV_PATH.read_text().splitlines()
    updates = {"CF_ACCOUNT_ID": account_id, "CF_API_TOKEN": api_token}
    seen = set()
    out = []
    for line in lines:
        key = line.partition("=")[0].strip()
        if key in updates and not line.lstrip().startswith("#"):
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n")
    print(f"Written to {ENV_PATH} (gitignored).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="test credentials already in .env")
    args = parser.parse_args()

    if args.check:
        env = read_env()
        account_id = os.environ.get("CF_ACCOUNT_ID") or env.get("CF_ACCOUNT_ID", "")
        api_token = os.environ.get("CF_API_TOKEN") or env.get("CF_API_TOKEN", "")
        print(f"CF_ACCOUNT_ID: {mask(account_id)}")
        print(f"CF_API_TOKEN:  {mask(api_token)}")
        if not account_id or not api_token:
            print("\nBoth are required. Run without --check to set them up.")
            return 1
        print("\nGenerating a test image…")
        data, error = generate(account_id, api_token)
    else:
        print(__doc__.split("Where to get")[1].strip().join(["Where to get", ""]))
        print()
        account_id = input("CF_ACCOUNT_ID: ").strip()
        if not account_id:
            print("Account ID is required.")
            return 1
        api_token = getpass.getpass("CF_API_TOKEN (hidden): ").strip()
        if not api_token:
            print("API token is required.")
            return 1
        print("\nGenerating a test image to verify the credentials…")
        data, error = generate(account_id, api_token)

    if error:
        print(f"\n✗ {error}")
        print("\nNothing was written. Fix the above and run this again.")
        return 1

    out_path = Path("cloudflare_test_mockup.png")
    out_path.write_bytes(data)
    print(f"\n✓ Working. Test image saved to {out_path.resolve()}")
    print("  Open it — you should see a generated dress, not a placeholder.")

    if not args.check:
        answer = input("\nWrite these credentials to backend/.env? [y/N] ").strip().lower()
        if answer == "y":
            write_env(account_id, api_token)
            print("\nAlso paste the same two values into Render's environment variables,")
            print("so the deployed API generates real mockups too.")
        else:
            print("Not written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
