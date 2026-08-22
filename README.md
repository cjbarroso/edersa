# EDERSA portal automation

Read-only automation for the EDERSA (Río Negro electric utility) customer portals.
Fetches your billing/debt detail as structured JSON.

Two GeneXus (WorkWithPlus) apps are involved:

| App | Host | Role |
|---|---|---|
| Oficina Virtual | `tramites.edersa.com.ar/OFICINA_VIRTUAL_PROD_EDERSA` | Login (by email) |
| Portal de Clientes / Pagos | `pagos.edersa.com.ar/PortalClientes_EDERSA_PROD` | Bills, debt, payment |

**Key finding:** reading data needs only valid session cookies — an authenticated
GET of the portal home embeds the full debt dataset in the page's `GXState`
(`vSALWSCONSULTAFACTURAS`). Login events are AES-encrypted per session, so we log in
with a browser and then use plain HTTP for reads. See
[`API_EDERSA_PortalClientes.md`](API_EDERSA_PortalClientes.md) for the full protocol notes.

## Architecture (two tiers)

1. **Login is browser-driven** (`login.py`, Playwright). GeneXus AES-encrypts AJAX
   events per session, so we drive the real form. The flow is:
   login at `tramites.` → land on Oficina Virtual home → click **"Ir a Facturas y
   Pagos"** (SSO handoff) → land on the `pagos.` Portal de Clientes, which sets the
   `pagos.edersa.com.ar` session cookies and renders the debt in `GXState`.
2. **Data reads are browser-free** (`edersa_client.py`, `requests`). Once you have
   `pagos.` cookies, a plain authenticated GET returns everything.

`get_invoices.py` runs tier 1 end-to-end and parses the result; it also saves the
session to `cookies.json` so subsequent refreshes can use the fast tier-2 client.

## Files

- `get_invoices.py` — **main entry**: login + handoff + parse → invoices JSON (`--pending`)
- `login.py` — browser login/handoff; writes `cookies.json`, prints the account key
- `edersa_client.py` — browser-free refresh from `cookies.json` → JSON
- `scripts/install_skill.py` — installs the `run-edersa-portal` agent skill from this repository
- `.env.example` — configuration template (copy to `.env`)

## Install the agent skill from private GitHub

Full agent-facing installation instructions are in
[`docs/INSTALL_AGENT_SKILL.md`](docs/INSTALL_AGENT_SKILL.md).

Quick start, after GitHub access is configured:

```bash
gh repo clone cjbarroso/edersa edersa
python edersa/scripts/install_skill.py --repo edersa
```

## Setup

Dependencies are pinned in `requirements.txt` (`requests`, `playwright`). Use an
**isolated virtualenv** — don't install into your system Python.

### With `uv` (recommended)

```bash
cd edersa
uv venv                                              # creates .venv/
uv pip install -r requirements.txt
.venv/Scripts/python -m playwright install chromium  # Windows
# .venv/bin/python  -m playwright install chromium   # macOS/Linux
cp .env.example .env                                 # set USERNAME (email) + PASSWORD
```

### Without `uv` (plain venv + pip)

```bash
cd edersa
python -m venv .venv
# activate:
.venv\Scripts\activate        # Windows PowerShell/cmd
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Then run either with the venv activated (`python get_invoices.py …`) or by calling the
venv interpreter directly without activating:

```bash
.venv/Scripts/python get_invoices.py --pending      # Windows
.venv/bin/python get_invoices.py --pending          # macOS/Linux
```

> Playwright's Chromium is cached per-user (`~/.cache/ms-playwright` /
> `%USERPROFILE%\AppData\Local\ms-playwright`), so `playwright install chromium` is a
> one-time download shared across venvs on that machine.

**Get invoices for ALL your accounts (one command):**

```bash
python get_invoices.py --pending > pending.json     # only unpaid
python get_invoices.py           > all.json          # everything
```

It auto-discovers every account (`cliente/suffix`) on your login from the Oficina
Virtual home, then reads each one with a single session. Output shape:

```jsonc
{
  "accounts": [
    { "cliente": "123456", "suffix": "1", "label": "… LOCALIDAD EJEMPLO …",
      "encabezado": "…", "pie": "…", "cantidad": 1,
      "facturas": [ { "comprobante": "FC   B-0042-…", "saldo": "$…",
                      "estado": "Impaga", "barra1": "…", "barra2": "…", … } ] },
    { "cliente": "654321", "suffix": "2", "label": "… OTRA LOCALIDAD …", … }
  ],
  "pending_total_count": 2
}
```

This also writes `cookies.json`.

> The Portal de Clientes keys off `cliente,suffix` (the leading account key in the URL
> is ignored), so one authenticated session reads all your accounts.

**Fast browser-free refresh of a single account** (until the session expires): set
`EDERSA_HOME_QS` in `.env` to `0,<cliente>,<suffix>,AIngreso,` then:

```bash
python edersa_client.py > debt.json     # reads cookies.json automatically
```

Output shape:

```jsonc
{
  "encabezado": "Cliente: …\nDomicilio: …\nDetalle de deuda desde el …",
  "pie": "Cantidad de comprobantes: 30 - Importe Total: $… …",
  "cantidad": 30,
  "facturas": [
    { "fecha": "…", "comprobante": "FC   B-0042-…", "vencimiento": "…",
      "total": "$…", "saldo": "$…", "estado": "Pagado|Impaga",
      "cuota_adeudada": "…", "tipo": "…", "identificador": "…",
      "barra1": "…", "barra2": "…" }
  ]
}
```

`barra1`/`barra2` are the Pago Fácil/Rapipago payment barcodes; they are populated
only on unpaid invoices.

## Notes / etiquette

- Sessions expire — re-run login (or refresh cookies) when `edersa_client.py` reports
  the session looks expired.
- Only automate access to **your own** account, and stay within the portal's terms.
- Never commit `.env` or `cookies.json` (both are git-ignored).
- This is unofficial and depends on the portal's internal GeneXus structure, which can
  change on redeploys.
