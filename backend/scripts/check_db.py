#!/usr/bin/env python3
"""Build and test a database URL without pasting secrets into your shell history.

Two ways to run it:

  # 1. Interactive — prompts for the password (hidden), builds a correctly
  #    encoded URL, tests it, and offers to write it to .env
  python scripts/check_db.py

  # 2. Test whatever DATABASE_URL is already set (env var or .env)
  python scripts/check_db.py --check

Nothing is printed with the password visible, and nothing is sent anywhere
except your own database.
"""

import argparse
import getpass
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def redact(url: str) -> str:
    """Mask the password so a URL can be shown safely."""
    return re.sub(r"(://[^:/@]+:)[^@]*(@)", r"\1<redacted>\2", url)


def describe(url: str) -> None:
    """Print the URL's structure without revealing the password."""
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        print(f"  cannot even split the URL: {exc}")
        return
    print(f"  scheme   : {parts.scheme or '(none)'}")
    print(f"  username : {parts.username or '(none)'}")
    print(f"  password : {'set (' + str(len(parts.password)) + ' chars)' if parts.password else '(none)'}")
    print(f"  host     : {parts.hostname or '(none)'}")
    print(f"  port     : {parts.port or '(default)'}")
    print(f"  database : {parts.path.lstrip('/') or '(none)'}")
    print(f"  query    : {parts.query or '(none)'}")


def diagnose(url: str) -> list[str]:
    """Common, specific problems — checked before we bother the network."""
    problems = []

    if not url.strip():
        return ["DATABASE_URL is empty."]

    if url.startswith("postgresql://") or url.startswith("postgres://"):
        problems.append(
            "Scheme is missing the driver. SQLAlchemy needs 'postgresql+psycopg2://', not 'postgresql://'."
        )

    if "YOUR_PASSWORD" in url or "<" in url or ">" in url:
        problems.append("The password placeholder hasn't been replaced with a real value.")

    if "\n" in url or "\r" in url:
        problems.append("The URL contains a line break — the paste was split across lines.")

    if url != url.strip():
        problems.append("The URL has leading or trailing whitespace.")

    # A raw '@' inside the password makes the parser read the wrong host.
    userinfo = url.split("://", 1)[-1].split("/", 1)[0]
    if userinfo.count("@") > 1:
        problems.append(
            "The password appears to contain an unencoded '@'. Special characters "
            "must be percent-encoded — this script does that for you."
        )

    if url.startswith("postgresql") and "sslmode" not in url and "neon.tech" in url:
        problems.append("Neon requires SSL — append '?sslmode=require'.")

    if "neon.tech" in url and "-pooler." not in url:
        problems.append(
            "Using Neon's direct host. Prefer the '-pooler' host: a free-tier "
            "instance that sleeps and wakes drops direct connections."
        )

    return problems


def test_connection(url: str) -> bool:
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("SQLAlchemy isn't installed — activate the venv first.")
        return False

    try:
        engine = create_engine(url, pool_pre_ping=True)
    except Exception as exc:
        print(f"\n✗ SQLAlchemy could not parse the URL: {exc}")
        return False

    try:
        with engine.connect() as conn:
            version = conn.execute(text("select version()")).scalar()
        print(f"\n✓ Connected: {version[:60]}")
        return True
    except Exception as exc:
        print(f"\n✗ Could not connect: {type(exc).__name__}: {str(exc)[:300]}")
        return False


def build_interactive() -> str:
    print("Build a Neon connection URL (password input is hidden).\n")
    host = input("Pooler host [ep-...-pooler.<region>.aws.neon.tech]: ").strip()
    if not host:
        print("Host is required.")
        sys.exit(1)
    if "-pooler." not in host:
        print("  note: that isn't the pooler host — prefer the one containing '-pooler'.")

    user = input("Role [neondb_owner]: ").strip() or "neondb_owner"
    database = input("Database [neondb]: ").strip() or "neondb"
    password = getpass.getpass("Password (hidden): ")
    if not password:
        print("Password is required.")
        sys.exit(1)

    # quote() with an empty safe list percent-encodes @ : / ? # etc., which is
    # what makes an awkward password survive being embedded in a URL.
    return (
        f"postgresql+psycopg2://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}/{database}?sslmode=require"
    )


def write_to_env(url: str) -> None:
    if not ENV_PATH.exists():
        print(f"\n{ENV_PATH} doesn't exist — create it from .env.example first.")
        return
    answer = input("\nWrite this as DATABASE_URL in backend/.env? [y/N] ").strip().lower()
    if answer != "y":
        print("Not written. Set it in Render's dashboard instead.")
        return
    lines = ENV_PATH.read_text().splitlines()
    out, replaced = [], False
    for line in lines:
        if line.startswith("DATABASE_URL=") and not replaced:
            out.append(f"DATABASE_URL={url}")
            replaced = True
        elif line.startswith("DATABASE_URL="):
            out.append(f"# {line}")  # comment out any duplicate
        else:
            out.append(line)
    if not replaced:
        out.append(f"DATABASE_URL={url}")
    ENV_PATH.write_text("\n".join(out) + "\n")
    print(f"Written to {ENV_PATH} (which is gitignored).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="test the existing DATABASE_URL instead of building one"
    )
    args = parser.parse_args()

    if args.check:
        url = os.environ.get("DATABASE_URL", "")
        if not url and ENV_PATH.exists():
            for line in ENV_PATH.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
        if not url:
            print("No DATABASE_URL found in the environment or backend/.env")
            return 1
        print(f"Testing: {redact(url)}\n")
        describe(url)
        problems = diagnose(url)
        if problems:
            print("\nProblems found:")
            for problem in problems:
                print(f"  • {problem}")
        return 0 if test_connection(url) else 1

    url = build_interactive()
    print(f"\nBuilt: {redact(url)}\n")
    describe(url)
    ok = test_connection(url)
    if ok:
        print("\nThis exact string is what goes into Render's DATABASE_URL.")
        write_to_env(url)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
