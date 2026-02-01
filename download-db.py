"""
Download Supabase tables (notes, attendees, profiles) via REST API
and write each to a JSON file. Requires SUPABASE_SERVICE_ROLE_KEY or
SUPABASE_ANON_KEY in the environment.
"""

import os
import urllib.request
import urllib.error
import json


BASE_URL = "https://uhvcbstdykcvgmzqpvpd.supabase.co/rest/v1"
TABLES = ("notes", "attendees", "profiles")
PAGE_SIZE = 1000


def get_api_key() -> str:
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or ""
    ).strip()
    if not key:
        raise ValueError(
            "Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in the environment"
        )
    return key


def fetch_table(table: str, api_key: str) -> list[dict]:
    """Fetch all rows from a Supabase table using Range pagination."""
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    rows: list[dict] = []
    start = 0

    while True:
        end = start + PAGE_SIZE - 1
        headers_with_range = {**headers, "Range": f"{start}-{end}"}
        url = f"{BASE_URL}/{table}?order=id.asc"
        req = urllib.request.Request(url, headers=headers_with_range, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                chunk = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(
                f"Supabase API error for {table} {e.code}: {body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Request failed for {table}: {e.reason}") from e

        if isinstance(chunk, list):
            rows.extend(chunk)
            if len(chunk) < PAGE_SIZE:
                break
        else:
            rows.extend(chunk if isinstance(chunk, list) else [])
            break
        start = end + 1

    return rows


def main() -> None:
    api_key = get_api_key()
    for table in TABLES:
        rows = fetch_table(table, api_key)
        out_path = f"{table}.json"
        with open(out_path, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
