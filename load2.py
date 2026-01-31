"""
Fetch all meetings from MeetGeek API.
API docs: https://docs.meetgeek.ai/api-reference/v1/meetings
"""

import os
import urllib.request
import urllib.error
import urllib.parse
import json
import time


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
    base_url = "https://api.meetgeek.ai/v1/meetings"
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


if __name__ == "__main__":
    meetings = get_all_meetings()
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
            lines = ", ".join([meeting_id, source, start_utc, title, participant_emails_str])

            # Skip webhook if meeting was in 2025 and source is upload
            # if source != "upload":
            #     print("  -> skipped (already uploaded)")
            #     continue
            # if join_link is None:
            #     print("  -> skipping join link is None")
            #     continue

            url = f"{webhook_base}?id={meeting_id}"
            try:
                with urllib.request.urlopen(url) as resp:
                    print("webhook ok", resp.getcode(), ",", lines, flush=True)
                    time.sleep(8)
            except urllib.error.HTTPError as e:
                print("  -> webhook error", e.code, e.read().decode(), flush=True)
        except Exception as e:
            print(meeting_id, f"error: {e}", flush=True)
