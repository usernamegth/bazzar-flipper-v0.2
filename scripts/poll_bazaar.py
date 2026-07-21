"""
Runs once per GitHub Actions invocation: fetches the Hypixel Bazaar API,
filters for high-liquidity / wide-spread items, and writes the result to
docs/data.json, which the static site (served via GitHub Pages) reads.

See the main README for the full explanation of the filter logic - this is
the same logic that previously lived in a FastAPI background loop, just
run as a one-shot script instead of a long-running server.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"

VOLUME_THRESHOLD = float(os.getenv("VOLUME_THRESHOLD", "50000"))
SPREAD_THRESHOLD_PCT = float(os.getenv("SPREAD_THRESHOLD_PCT", "10"))
WINDOW_DAYS = float(os.getenv("WINDOW_DAYS", "5"))
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "30"))
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "docs/data.json")


def compute_filtered(products: dict) -> list[dict]:
    results = []
    for product_id, data in products.items():
        qs = data.get("quick_status", {})

        buy_price = qs.get("buyPrice", 0) or 0
        sell_price = qs.get("sellPrice", 0) or 0
        buy_moving_week = qs.get("buyMovingWeek", 0) or 0
        sell_moving_week = qs.get("sellMovingWeek", 0) or 0

        if buy_price <= 0 or sell_price <= 0:
            continue

        est_buy_volume = buy_moving_week * (WINDOW_DAYS / 7)
        est_sell_volume = sell_moving_week * (WINDOW_DAYS / 7)

        if est_buy_volume < VOLUME_THRESHOLD or est_sell_volume < VOLUME_THRESHOLD:
            continue

        spread_pct = (buy_price - sell_price) / sell_price * 100
        if spread_pct < SPREAD_THRESHOLD_PCT:
            continue

        results.append(
            {
                "id": product_id,
                "name": product_id.replace("_", " ").title(),
                "buy_price": round(buy_price, 2),
                "sell_price": round(sell_price, 2),
                "spread_pct": round(spread_pct, 2),
                "est_buy_volume": round(est_buy_volume),
                "est_sell_volume": round(est_sell_volume),
                "buy_moving_week": round(buy_moving_week),
                "sell_moving_week": round(sell_moving_week),
            }
        )

    results.sort(key=lambda x: x["spread_pct"], reverse=True)
    return results


def load_existing(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"items": [], "products_scanned": 0, "last_updated": None}


def main():
    payload = load_existing(OUTPUT_PATH)
    error = None

    try:
        resp = requests.get(BAZAAR_URL, timeout=20)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success", False):
            raise RuntimeError(f"Hypixel API returned success=false: {body}")

        products = body.get("products", {})
        payload["items"] = compute_filtered(products)
        payload["products_scanned"] = len(products)
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        # Keep whatever the last good data was; just surface the error.
        # This mirrors how the original server-based version handled
        # transient API failures without wiping the dashboard.
        error = str(exc)

    payload["error"] = error
    payload["last_checked"] = datetime.now(timezone.utc).isoformat()
    payload["config"] = {
        "volume_threshold": VOLUME_THRESHOLD,
        "spread_threshold_pct": SPREAD_THRESHOLD_PCT,
        "window_days": WINDOW_DAYS,
        "poll_interval_minutes": POLL_INTERVAL_MINUTES,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    if error:
        print(f"Completed with error (kept previous data): {error}", file=sys.stderr)
    else:
        print(f"Wrote {len(payload['items'])} matching items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
