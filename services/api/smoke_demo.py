"""Exercise the seeded local API using synthetic accounts and a temporary booking.

Run after migrations and seed.py: python smoke_demo.py
The temporary appointment is cancelled on exit. No real patient data is used.
"""

import argparse
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import httpx


def check(response: httpx.Response, operation: str, expected: int = 200):
    if response.status_code != expected:
        raise RuntimeError(
            f"{operation}: expected HTTP {expected}, received {response.status_code}"
        )
    return response.json() if response.content else None


def run(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("This synthetic-data smoke test only runs against a local HTTP API")

    with httpx.Client(base_url=f"{base_url.rstrip('/')}/api/v1", timeout=20) as client:
        auth = check(
            client.post(
                "/auth/login", json={"email": "maya.johnson@example.com", "password": "Patient123!"}
            ),
            "Maya login",
        )
        headers = {"Authorization": f"Bearer {auth['tokens']['access_token']}"}
        profile = check(client.get("/me/", headers=headers), "Patient profile")
        assert profile["profile"]["legal_first_name"] == "Maya"
        consents = check(client.get("/me/consents", headers=headers), "Patient consents")
        assert {"terms", "privacy", "telehealth"}.issubset(
            {c["consent_type"] for c in consents if c["status"] == "accepted"}
        )
        print("PASS: patient login, profile and consent data")

        clinicians = check(client.get("/practitioners"), "Practitioner discovery")["items"]
        assert clinicians, "No seeded practitioners found"
        practitioner = clinicians[0]
        today = datetime.now(UTC).date()
        availability = check(
            client.get(
                f"/practitioners/{practitioner['id']}/availability",
                params={
                    "start_date": today.isoformat(),
                    "end_date": (today + timedelta(days=7)).isoformat(),
                },
            ),
            "Availability",
        )
        slot = next(
            slot
            for slots in availability["availability"].values()
            for slot in slots
            if slot["is_available"]
        )
        print("PASS: practitioner discovery and available slots")

        key = str(uuid4())
        hold_data = {
            "practitioner_id": practitioner["id"],
            "slot_start": slot["start"],
            "visit_type": "video",
            "idempotency_key": key,
        }
        hold = check(
            client.post("/appointment-holds", json=hold_data, headers=headers),
            "Create appointment hold",
        )
        repeated_hold = check(
            client.post("/appointment-holds", json=hold_data, headers=headers),
            "Retry appointment hold",
        )
        assert repeated_hold["hold_id"] == hold["hold_id"]
        appointment = None
        try:
            confirm_data = {"hold_id": hold["hold_id"], "idempotency_key": key}
            appointment = check(
                client.post("/appointments", json=confirm_data, headers=headers),
                "Confirm appointment",
            )
            repeated = check(
                client.post("/appointments", json=confirm_data, headers=headers),
                "Retry appointment confirmation",
            )
            assert repeated["id"] == appointment["id"]
            assert appointment["status"] == "confirmed"
            appointments = check(
                client.get("/appointments", headers=headers), "List patient appointments"
            )
            assert appointment["id"] in {a["id"] for a in appointments["items"]}
            print("PASS: hold, confirmation, idempotent retries and appointment list")

            other_auth = check(
                client.post(
                    "/auth/login",
                    json={"email": "james.wilson@example.com", "password": "Patient123!"},
                ),
                "Second synthetic patient login",
            )
            other_headers = {"Authorization": f"Bearer {other_auth['tokens']['access_token']}"}
            check(
                client.get(f"/appointments/{appointment['id']}", headers=other_headers),
                "Cross-patient authorization",
                expected=403,
            )
            print("PASS: another patient cannot access the appointment")
        finally:
            if appointment:
                check(
                    client.post(
                        f"/appointments/{appointment['id']}/cancel",
                        headers=headers,
                        json={"reason": "Synthetic local smoke test cleanup"},
                    ),
                    "Cancel temporary smoke-test booking",
                )
                print("PASS: temporary booking cancelled")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8005")
    run(parser.parse_args().base_url)
