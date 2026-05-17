"""
list_models.py — Lista todos los modelos disponibles en watsonx.ai.

Usa las credenciales definidas en .env:
  WATSONX_APIKEY
  WATSONX_URL      (default: https://us-south.ml.cloud.ibm.com)

Uso:
  python list_models.py
  python list_models.py --filter code
  python list_models.py --provider ibm
  python list_models.py --active-only
"""

from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2023-09-30"


def _get_iam_token(api_key: str) -> str:
    resp = requests.post(
        IAM_TOKEN_URL,
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _fetch_models(base_url: str, token: str) -> list[dict]:
    resp = requests.get(
        f"{base_url}/ml/v1/foundation_model_specs",
        params={"version": API_VERSION, "limit": 200},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("resources", [])


def _lifecycle_status(model: dict) -> str:
    lifecycle = model.get("lifecycle") or []
    for entry in lifecycle:
        if entry.get("id") == "available":
            return "available"
        if entry.get("id") == "deprecated":
            return "deprecated"
        if entry.get("id") == "withdrawn":
            return "withdrawn"
    return "unknown"


def _format_functions(model: dict) -> str:
    funcs = model.get("functions") or []
    return ", ".join(f.get("id", "") for f in funcs if f.get("id")) or "—"


def _print_table(models: list[dict]) -> None:
    col_id    = max(len(m["model_id"]) for m in models)
    col_label = max(len(m.get("label", "")) for m in models)
    col_prov  = max(len(m.get("provider", "")) for m in models)
    col_status = 10
    col_funcs  = 30

    header = (
        f"{'MODEL ID':<{col_id}}  "
        f"{'LABEL':<{col_label}}  "
        f"{'PROVIDER':<{col_prov}}  "
        f"{'STATUS':<{col_status}}  "
        f"FUNCTIONS"
    )
    sep = "─" * len(header)
    print(sep)
    print(header)
    print(sep)

    for m in models:
        status = _lifecycle_status(m)
        status_display = status if status == "available" else f"[{status}]"
        funcs = _format_functions(m)[:col_funcs]
        print(
            f"{m['model_id']:<{col_id}}  "
            f"{m.get('label', ''):<{col_label}}  "
            f"{m.get('provider', ''):<{col_prov}}  "
            f"{status_display:<{col_status}}  "
            f"{funcs}"
        )

    print(sep)
    print(f"Total: {len(models)} model(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="List watsonx.ai foundation models")
    parser.add_argument("--filter", metavar="TEXT",
                        help="Only show models whose ID or label contains TEXT (case-insensitive)")
    parser.add_argument("--provider", metavar="NAME",
                        help="Only show models from this provider (e.g. ibm, meta, google)")
    parser.add_argument("--active-only", action="store_true",
                        help="Hide deprecated and withdrawn models")
    args = parser.parse_args()

    api_key = os.getenv("WATSONX_APIKEY", "")
    base_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/")

    if not api_key or api_key == "your_api_key_here":
        sys.exit("ERROR: WATSONX_APIKEY is not set in .env")

    print("Authenticating with IBM IAM...", flush=True)
    try:
        token = _get_iam_token(api_key)
    except Exception as exc:
        sys.exit(f"ERROR: Could not get IAM token — {exc}")

    print(f"Fetching models from {base_url} ...", flush=True)
    try:
        models = _fetch_models(base_url, token)
    except Exception as exc:
        sys.exit(f"ERROR: Could not fetch models — {exc}")

    if args.active_only:
        models = [m for m in models if _lifecycle_status(m) == "available"]

    if args.provider:
        models = [m for m in models if args.provider.lower() in m.get("provider", "").lower()]

    if args.filter:
        needle = args.filter.lower()
        models = [
            m for m in models
            if needle in m.get("model_id", "").lower()
            or needle in m.get("label", "").lower()
            or needle in m.get("short_description", "").lower()
        ]

    if not models:
        print("No models match the given filters.")
        return

    print()
    _print_table(models)
    print()
    print("Use model_id in services/bob_client.py → MODEL_ID = \"<model_id>\"")


if __name__ == "__main__":
    main()
