#!/usr/bin/env python3
"""
EDERSA Portal de Clientes — read-only client.

The portal is a GeneXus (WorkWithPlus) app. Reading billing/debt data only needs
valid session cookies: an authenticated GET of the home servlet embeds the full
debt dataset inside the page's `GXState` hidden field, under `vSALWSCONSULTAFACTURAS`.

This module does NOT log in (GeneXus encrypts AJAX events per-session). Obtain
cookies via `login.py` (browser) or by pasting them from your browser devtools,
and supply them through environment variables / .env. See README.md.

Never commit real cookies or credentials.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

import requests

BASE = "https://pagos.edersa.com.ar/PortalClientes_EDERSA_PROD/servlet"
SERVLET = "com.portalclientes.edersa.rwdhomemaster"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")

# Querystring identifying the account/home state, e.g. "0,123456,1,AIngreso,"
# Defaults to env; if absent we GET the base servlet and follow whatever it renders.
HOME_QS = os.environ.get("EDERSA_HOME_QS", "").strip()


def _cookie_header() -> str:
    """Build a Cookie header. Sources, in priority order:
    1. EDERSA_COOKIE (full Cookie header string)
    2. cookies.json (produced by login.py) — {"GX_SESSION_ID": ..., ...}
    3. individual EDERSA_GX_SESSION_ID / EDERSA_JSESSIONID / ... vars
    """
    full = os.environ.get("EDERSA_COOKIE", "").strip()
    if full:
        return full
    cj = os.environ.get("EDERSA_COOKIES_FILE", "cookies.json")
    if os.path.exists(cj):
        with open(cj, encoding="utf-8") as fh:
            data = json.load(fh)
        if data:
            return "; ".join(f"{k}={v}" for k, v in data.items())
    parts = []
    for name, env in (
        ("GX_SESSION_ID", "EDERSA_GX_SESSION_ID"),
        ("GX_CLIENT_ID", "EDERSA_GX_CLIENT_ID"),
        ("JSESSIONID", "EDERSA_JSESSIONID"),
    ):
        val = os.environ.get(env, "").strip()
        if val:
            parts.append(f"{name}={val}")
    if not parts:
        sys.exit("No cookies found. Set EDERSA_COOKIE or EDERSA_GX_SESSION_ID/"
                 "EDERSA_JSESSIONID (see README.md).")
    return "; ".join(parts)


def build_session(cookie_header: str | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA,
                      "Cookie": cookie_header or _cookie_header()})
    return s


def account_qs(cliente: str | int, suffix: str | int) -> str:
    """The server ignores the leading account key and keys off cliente,suffix."""
    return f"0,{cliente},{suffix},AIngreso,"


def fetch_home(session: requests.Session, qs: str | None = None) -> str:
    url = f"{BASE}/{SERVLET}"
    qs = qs if qs is not None else HOME_QS
    if qs:
        url += "?" + qs
    r = session.get(url, timeout=30)
    r.raise_for_status()
    if "RWDHome Master" not in r.text and "GXState" not in r.text:
        raise RuntimeError("Response doesn't look like the authenticated home page "
                           "(session likely expired). Re-authenticate.")
    return r.text


def get_debt(session: requests.Session, qs: str | None = None) -> dict:
    return parse_debt(extract_gxstate(fetch_home(session, qs)))


def extract_gxstate(page_html: str) -> dict:
    """GXState is a hidden input whose value may be single- or double-quoted."""
    m = re.search(r"name=[\"']GXState[\"']\s+value=(['\"])(.*?)\1\s*/?>",
                  page_html, re.S)
    if not m:
        raise RuntimeError("GXState hidden field not found.")
    return json.loads(html.unescape(m.group(2)))


def _find_facturas(gxstate: dict) -> dict:
    """Return the sub-object holding TextoEncabezado/Facturas/TextoPie."""
    direct = gxstate.get("vSALWSCONSULTAFACTURAS")
    if isinstance(direct, dict) and "Facturas" in direct:
        return direct
    for v in gxstate.values():                       # fallback: scan
        if isinstance(v, dict) and "Facturas" in v:
            return v
    raise RuntimeError("Debt payload (Facturas) not present in GXState.")


@dataclass
class Invoice:
    fecha: str
    comprobante: str
    vencimiento: str
    total: str
    saldo: str
    estado: str
    cuota_adeudada: str
    tipo: str
    identificador: str
    barra1: str
    barra2: str


def _campo(inv: dict, n: int) -> str:
    return (inv.get(f"Campo{n}Valor") or "").strip()


def parse_debt(gxstate: dict) -> dict:
    data = _find_facturas(gxstate)
    invoices = []
    for inv in data.get("Facturas", []):
        invoices.append(asdict(Invoice(
            fecha=_campo(inv, 1),
            comprobante=_campo(inv, 2),
            vencimiento=_campo(inv, 3),
            total=_campo(inv, 4),
            cuota_adeudada=_campo(inv, 5),
            tipo=_campo(inv, 6),
            saldo=_campo(inv, 7),
            estado=_campo(inv, 10),
            identificador=(inv.get("Identificador") or "").strip(),
            barra1=_campo(inv, 12),
            barra2=_campo(inv, 13),
        )))
    return {
        "encabezado": data.get("TextoEncabezado", ""),
        "pie": data.get("TextoPie", ""),
        "cantidad": len(invoices),
        "facturas": invoices,
    }


def main() -> None:
    try:                                             # always emit UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    session = build_session()
    result = get_debt(session)
    if result["cantidad"] == 0 and not HOME_QS:
        print("WARNING: 0 invoices and EDERSA_HOME_QS is unset. The account "
              "context lives in that querystring — set it in .env "
              "(e.g. '0,123456,1,AIngreso,').", file=sys.stderr)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
