"""
Upload JSON backups to Supabase. Reads notes.json, attendees.json, profiles.json
and pushes rows to the same tables. Assumes tables are empty.
Requires SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in the environment.
"""

import json
import os
import urllib.request
import urllib.error

BASE_URL = "https://uhvcbstdykcvgmzqpvpd.supabase.co/rest/v1"


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


def post_rows(
    table: str,
    rows: list[dict],
    api_key: str,
    *,
    prefer_return: bool = True,
) -> list[dict]:
    """POST rows to a table. Returns inserted rows if prefer_return=True."""
    if not rows:
        return []
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if prefer_return:
        headers["Prefer"] = "return=representation"
    body = json.dumps(rows).encode()
    url = f"{BASE_URL}/{table}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            out = resp.read().decode()
            return json.loads(out) if out else []
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Supabase API error for {table} {e.code}: {e.read().decode()}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed for {table}: {e.reason}") from e


def load_json(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def main() -> None:
    api_key = get_api_key()

    # 1. Notes first (identity id) – insert one-by-one to get old_id -> new_id
    notes = load_json("notes.json")
    old_note_id_to_new: dict[int, int] = {}
    for row in notes:
        payload = {k: v for k, v in row.items() if k != "id"}
        inserted = post_rows("notes", [payload], api_key)
        if inserted:
            old_note_id_to_new[row["id"]] = inserted[0]["id"]
    print(f"Inserted {len(notes)} notes")

    # 2. Attendees (fk note_id) – map note_id, drop id
    attendees = load_json("attendees.json")
    if attendees:
        for row in attendees:
            row["note_id"] = old_note_id_to_new[row["note_id"]]
            row.pop("id", None)
        batch_size = 500
        for i in range(0, len(attendees), batch_size):
            post_rows("attendees", attendees[i : i + batch_size], api_key)
    print(f"Inserted {len(attendees)} attendees")

    # 3. Profiles (uuid id) – keep id, insert as-is
    profiles = load_json("profiles.json")
    if profiles:
        batch_size = 500
        for i in range(0, len(profiles), batch_size):
            post_rows("profiles", profiles[i : i + batch_size], api_key)
    print(f"Inserted {len(profiles)} profiles")


if __name__ == "__main__":
    main()
