"""
Fetch all HubSpot contacts owned by a specific user via the HubSpot CRM Search API.
"""
import json
import urllib.request
import urllib.error


HUBSPOT_API_KEY = "SET_ME "

OWNER_ID = "29286558"
BASE_URL = "https://api.hubapi.com"
SEARCH_URL = f"{BASE_URL}/crm/v3/objects/contacts/search"
PAGE_SIZE = 100


def get_contacts_for_owner(api_key: str, owner_id: str) -> list[dict]:
    """Fetch all contacts owned by the given HubSpot user id."""
    all_contacts = []
    after = None

    while True:
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "hubspot_owner_id",
                            "operator": "EQ",
                            "value": owner_id,
                        }
                    ]
                }
            ],
            "limit": PAGE_SIZE,
        }
        if after is not None:
            body["after"] = after

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            SEARCH_URL,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"HubSpot API error {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Request failed: {e.reason}") from e

        results = result.get("results", [])
        all_contacts.extend(results)

        paging = result.get("paging", {})
        next_info = paging.get("next")
        if not next_info or "after" not in next_info:
            break
        after = next_info["after"]

    return [
        {
            "hubspot_id": str(c["id"]),
            "name": " ".join(
                filter(None, [
                    c.get("properties", {}).get("firstname", "").strip(),
                    c.get("properties", {}).get("lastname", "").strip(),
                ])
            ).strip() or "(no name)",
            "email": (c.get("properties", {}) or {}).get("email", "") or "",
        }
        for c in all_contacts
    ]


def main():
    contacts = get_contacts_for_owner(HUBSPOT_API_KEY, OWNER_ID)
    print(f"Total contacts for owner {OWNER_ID}: {len(contacts)}\n")
    for c in contacts:
        print(f"  {c['hubspot_id']}: {c['name']} <{c['email']}>")
    return contacts


if __name__ == "__main__":
    main()
