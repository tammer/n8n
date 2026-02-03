"""
Fetch all meetings from MeetGeek API.
API docs: https://docs.meetgeek.ai/api-reference/v1/meetings
"""

import argparse
import os
import re
import urllib.request
import urllib.error
import urllib.parse
import json
import time

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_all_meetings(token: str | None = None) -> list[dict]:
    """
    Fetch all meetings from MeetGeek API with pagination.
    Returns a list of dicts with meeting_id, timestamp_start_utc, timestamp_end_utc.

    Pass the Bearer token as `token`, or set MEETGEEK_API_TOKEN env var.
    """
    api_token = (token or os.environ.get("MEETGEEK_API_TOKEN") or "").strip()
    if not api_token:
        raise ValueError("Provide token or set MEETGEEK_API_TOKEN")

    # EU base URL (use api.meetgeek.ai or api-us.meetgeek.ai if needed)
    base_url = "https://api.meetgeek.ai/v1/teams/1843/meetings"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "User-Agent": "curl/8.0",  # API often blocks Python's default User-Agent
    }

    all_meetings: list[dict] = []
    cursor: str | None = None
    limit = 500  # max per request

    while True:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        url = f"{base_url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"MeetGeek API error {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Request failed: {e.reason}") from e

        meetings = data.get("meetings") or []
        all_meetings.extend(meetings)

        pagination = data.get("pagination") or {}
        next_cursor = pagination.get("next_cursor")
        if not next_cursor or not meetings:
            break
        cursor = next_cursor

    return all_meetings


def get_meeting(meeting_id: str, token: str | None = None) -> dict:
    """
    Get meeting details by ID (GET /v1/meetings/{meetingId}).
    Returns meeting shard with source, title, host_email, etc.
    https://docs.meetgeek.ai/api-reference/v1/meeting
    """
    api_token = (token or os.environ.get("MEETGEEK_API_TOKEN") or "").strip()
    if not api_token:
        raise ValueError("Provide token or set MEETGEEK_API_TOKEN")

    base_url = "https://api.meetgeek.ai/v1/meetings"
    url = f"{base_url}/{meeting_id}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
        "User-Agent": "curl/8.0",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"MeetGeek API error {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Request failed: {e.reason}") from e


def meeting_date_utc(meeting: dict) -> str | None:
    """Return yyyy-mm-dd of meeting start in UTC, or None if missing."""
    ts = meeting.get("timestamp_start_utc") or ""
    if not ts:
        return None
    # Handle ISO-like timestamps: "2025-02-03T14:00:00Z" or "2025-02-03 14:00:00"
    return ts[:10] if len(ts) >= 10 else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch MeetGeek meetings and send to webhook.")
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        metavar="yyyy-mm-dd",
        help="Optional: only process meetings that start on this date (UTC)",
    )
    args = parser.parse_args()

    filter_date: str | None = None
    if args.date is not None:
        if not DATE_RE.match(args.date):
            parser.error("date must be in format yyyy-mm-dd")
        filter_date = args.date

    meetings = get_all_meetings()

    if filter_date is not None:
        meetings = [m for m in meetings if meeting_date_utc(m) == filter_date]
        print(f"Filtered to {len(meetings)} meetings on {filter_date}\n", flush=True)
    else:
        print(f"Fetched {len(meetings)} meetings\n", flush=True)

    webhook_base = "https://tammer.app.n8n.cloud/webhook/supa-from-id"

    for m in meetings:
        meeting_id = m.get("meeting_id", "")
        try:
            details = get_meeting(meeting_id)
            source = details.get("source", "")
            join_link = details.get("join_link", None)
            start_utc = details.get("timestamp_start_utc", "")
            title = details.get("title", "")
            participant_emails = details.get("participant_emails", [])
            participant_emails_str = " and ".join(participant_emails)
            lines = ", ".join([title, meeting_id, source, start_utc, participant_emails_str])

            url = f"{webhook_base}?id={meeting_id}"
            try:
                with urllib.request.urlopen(url) as resp:
                    print("webhook ok", resp.getcode(), ",", lines, flush=True)
                    time.sleep(8)
            except urllib.error.HTTPError as e:
                print("  -> webhook error", e.code, e.read().decode(), flush=True)
        except Exception as e:
            print(meeting_id, f"error: {e}", flush=True)
