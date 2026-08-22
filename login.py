#!/usr/bin/env python3
"""
EDERSA session bootstrap (browser-based).

The portals are GeneXus WorkWithPlus apps that AES-encrypt AJAX events with a
per-session key, so we drive the real login form with a headless browser. The flow:

  1. Log in at Oficina Virtual (tramites.edersa.com.ar) — login is by EMAIL.
  2. Follow the "Ir a Facturas y Pagos" SSO handoff to the Portal de Clientes
     (pagos.edersa.com.ar), which is where billing/debt data lives.
  3. Return the pagos.edersa.com.ar session cookies + account querystring + the
     debt GXState (read straight from the DOM).

Downstream, plain-HTTP requests with those cookies are enough (see edersa_client.py).

Credentials come from .env (USERNAME/PASSWORD or EDERSA_USER/EDERSA_PASS). We parse
.env directly rather than via os.environ, because USERNAME collides with a built-in
Windows environment variable.

Setup (one time):
    pip install playwright
    playwright install chromium

Run:
    python login.py            # logs in + handoff, writes cookies.json, prints account qs
"""
from __future__ import annotations

import json
import os
import sys

LOGIN_URL = ("https://tramites.edersa.com.ar/OFICINA_VIRTUAL_PROD_EDERSA/"
             "servlet/com.oficinavirtual.login")
HOME = ("https://tramites.edersa.com.ar/OFICINA_VIRTUAL_PROD_EDERSA/servlet/"
        "com.oficinavirtual.wwpbaseobjects.home")
WANTED = ("GX_SESSION_ID", "GX_CLIENT_ID", "JSESSIONID")


def _read_dotenv(path: str = ".env") -> dict:
    env = {}
    if not os.path.exists(path):
        return env
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _load_env() -> tuple[str, str]:
    env = _read_dotenv()
    user = (env.get("EDERSA_USER") or env.get("USERNAME") or "").strip()
    pw = (env.get("EDERSA_PASS") or env.get("PASSWORD") or "").strip()
    if not user or not pw:
        sys.exit("Set EDERSA_USER/EDERSA_PASS (or USERNAME/PASSWORD) in .env. "
                 "Login is by email.")
    return user, pw


def fetch_portal_state(headless: bool = True) -> dict:
    """Run the full browser flow. Returns:
        {cookies: {..}, account_qs: str, gxstate: dict}
    where gxstate is the Portal de Clientes home state (contains the debt payload).
    """
    user, pw = _load_env()
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        sys.exit("playwright not installed. Run:\n"
                 "  pip install playwright\n  playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.goto(LOGIN_URL, wait_until="networkidle")
        page.fill("#vUSUARIO", user)
        page.fill("#vPASSWORD", pw)
        page.click("#BTNENTER")
        page.wait_for_timeout(3500)
        if "home" not in page.url:
            page.goto(HOME, wait_until="networkidle")
        if page.query_selector("#vPASSWORD") and "login" in page.url:
            browser.close()
            sys.exit("Login failed — check credentials in .env.")

        # Discover all accounts (cliente/suffix) from the Oficina Virtual home,
        # before the handoff (the account selector lists every account).
        accounts = page.evaluate(r"""() => {
          const seen={}, out=[];
          const nodes=[...document.querySelectorAll(
              "a[href*='cuentaactual'],[onclick*='cuentaactual'],"
              +"[id*='CUENTA'],[id*='Cuenta'],li,a,span,div")];
          for(const n of nodes){
            const t=(n.innerText||'').replace(/\s+/g,' ').trim();
            const m=t.match(/\b(\d{3,7})\s*\/\s*(\d{1,2})\b/);
            if(m){
              const key=m[1]+'/'+m[2];
              if(!(key in seen)){ seen[key]=1;
                out.push({cliente:m[1], suffix:m[2], label:t.slice(0,70)}); }
            }
          }
          return out;
        }""")

        clicked = page.evaluate("""() => {
          const a=[...document.querySelectorAll('a[data-gx-evt]')]
                    .find(x=>/Ir a Facturas y Pagos/i.test(x.innerText||''));
          if(!a) return false; a.scrollIntoView(); a.click(); return true;
        }""")
        if not clicked:
            browser.close()
            sys.exit("Could not find the 'Ir a Facturas y Pagos' handoff link.")

        # The handoff navigates the same tab (sometimes a popup). Poll for the
        # pagos page instead of a fixed sleep — headless timing varies.
        target = None
        for _ in range(30):  # up to ~30s
            target = next((pp for pp in ctx.pages if "pagos.edersa" in pp.url), None)
            if target:
                break
            page.wait_for_timeout(1000)
        if target is None:
            browser.close()
            sys.exit("Did not reach the Portal de Clientes (pagos).")
        try:
            target.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        # ensure the debt state is actually rendered
        try:
            target.wait_for_selector("input[name='GXState']", timeout=10000)
        except Exception:
            pass

        gxstate = json.loads(
            target.eval_on_selector("input[name='GXState']", "e => e.value"))
        portal_url = target.url
        cookies = {c["name"]: c["value"] for c in ctx.cookies()
                   if c["name"] in WANTED and "pagos.edersa" in c["domain"]}
        browser.close()

    account_qs = portal_url.split("?", 1)[1] if "?" in portal_url else ""
    return {"cookies": cookies, "account_qs": account_qs,
            "gxstate": gxstate, "accounts": accounts}


def main() -> None:
    headless = _read_dotenv().get("EDERSA_HEADLESS", "1") != "0"
    state = fetch_portal_state(headless=headless)
    if not state["cookies"]:
        sys.exit("Reached the portal but captured no pagos cookies.")
    with open("cookies.json", "w", encoding="utf-8") as fh:
        json.dump(state["cookies"], fh, indent=2)
    print("Wrote cookies.json:", ", ".join(sorted(state["cookies"])))
    print("Account querystring (set as EDERSA_HOME_QS for edersa_client.py):")
    print("  " + state["account_qs"])


if __name__ == "__main__":
    main()
