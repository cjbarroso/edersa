#!/usr/bin/env python3
"""
Log in to EDERSA, discover all accounts on the user, and return their invoices as
JSON — across every account. Use --pending to show only unpaid ones.

Flow: browser login + SSO handoff (once) to get pagos.edersa.com.ar cookies, then a
plain-HTTP GET per account (the server keys off cliente,suffix). Also saves the
session to cookies.json for browser-free refreshes via edersa_client.py.

Credentials come from .env (USERNAME/PASSWORD or EDERSA_USER/EDERSA_PASS).

Usage:
    python get_invoices.py             # all invoices, all accounts
    python get_invoices.py --pending   # only unpaid
"""
from __future__ import annotations

import json
import re
import sys

from login import fetch_portal_state
from edersa_client import build_session, get_debt, account_qs


def _is_pending(inv: dict) -> bool:
    estado = (inv.get("estado") or "").strip().lower()
    raw = re.sub(r"[^\d,.-]", "", inv.get("saldo") or "").replace(",", "")
    try:
        saldo = float(raw) if raw else 0.0
    except ValueError:
        saldo = 0.0
    return (estado not in ("pagado", "")) or saldo > 0


def _accounts_from(state: dict) -> list[dict]:
    """Discovered accounts, or fall back to the one from the handoff querystring."""
    if state.get("accounts"):
        return state["accounts"]
    parts = (state.get("account_qs") or "").split(",")
    if len(parts) >= 3:
        return [{"cliente": parts[1], "suffix": parts[2], "label": ""}]
    return []


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    pending_only = "--pending" in sys.argv[1:]

    state = fetch_portal_state()
    if state["cookies"]:
        with open("cookies.json", "w", encoding="utf-8") as fh:
            json.dump(state["cookies"], fh, indent=2)

    accounts = _accounts_from(state)
    if not accounts:
        sys.exit("No accounts discovered.")

    session = build_session("; ".join(f"{k}={v}" for k, v in state["cookies"].items()))

    out_accounts = []
    total_pending = 0
    for acc in accounts:
        debt = get_debt(session, account_qs(acc["cliente"], acc["suffix"]))
        facturas = debt["facturas"]
        if pending_only:
            facturas = [f for f in facturas if _is_pending(f)]
        pend = [f for f in debt["facturas"] if _is_pending(f)]
        total_pending += len(pend)
        out_accounts.append({
            "cliente": acc["cliente"],
            "suffix": acc["suffix"],
            "label": acc.get("label", ""),
            "encabezado": debt["encabezado"],
            "pie": debt["pie"],
            "cantidad": len(facturas),
            "facturas": facturas,
        })

    result = {"accounts": out_accounts, "pending_total_count": total_pending}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
