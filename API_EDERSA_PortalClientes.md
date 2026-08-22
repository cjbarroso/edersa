# EDERSA – Portal de Clientes / Pagos — API notes

Reverse-engineered from a single captured browser request (GeneXus AJAX postback).
**No live request was replayed** — this is a static analysis of the captured `curl`.

> ⚠️ The original capture contained PII (customer name, address, account number) and
> live session secrets (`AJAX_SECURITY_TOKEN`, `GX_SESSION_ID`, `JSESSIONID`).
> Those are **redacted / shown as placeholders** here. Never commit real tokens or
> customer data to this repo.

All numeric identifiers, invoice values, and payment barcode examples in this
document are synthetic. Never replace them with values copied from a live account.

---

## 1. Platform

The portal is a **GeneXus**-generated Java web application (Responsive Web Design / "RWD").
Tells:

- Servlet path `.../servlet/com.portalclientes.edersa.rwdhomemaster`
  (`rwd` + `homemaster` = a GeneXus RWD *master page* object).
- `GxAjaxRequest: 1` header and `AJAX_SECURITY_TOKEN` header — GeneXus AJAX event protocol.
- Body fields `GXEvent`, `GXParm0..N` — GeneXus server-event dispatch + parameters.
- Cookies `GX_SESSION_ID`, `GX_CLIENT_ID` — GeneXus session/client identity.
- `JSESSIONID=...worker2` — Java servlet container session (behind a load balancer; `worker2` = backend node).

So this is a classic GeneXus "fire a server event, POST the current control state back" call —
conceptually similar to ASP.NET's `__doPostBack` / viewstate.

---

## 2. Endpoint

```
POST /PortalClientes_EDERSA_PROD/servlet/com.portalclientes.edersa.rwdhomemaster
Host: pagos.edersa.com.ar
```

Query string:
- `gx-no-cache=<epoch-ms>` — cache-buster timestamp only.

Environment segment in the path: **`PortalClientes_EDERSA_PROD`** → production deployment.

---

## 3. Required headers

| Header | Purpose |
|---|---|
| `AJAX_SECURITY_TOKEN: <hex>` | GeneXus per-session anti-CSRF token. Must match the server session. |
| `GxAjaxRequest: 1` | Marks the call as a GeneXus AJAX event (vs. full page load). |
| `Content-Type: application/x-www-form-urlencoded` | Body encoding. |
| `Origin` / `Referer` | Same-origin; server likely checks these. |
| `Cookie` (see below) | Session binding. |

### Cookies

| Cookie | Meaning |
|---|---|
| `GX_SESSION_ID` | GeneXus session id (URL-encoded, base64-ish). **Secret.** |
| `GX_CLIENT_ID` | GeneXus client GUID. |
| `JSESSIONID` | Java servlet session (`.workerN` suffix = LB sticky node). **Secret.** |
| `_ga`, `_gid`, `_ga_*` | Google Analytics only — not needed for the API. |

To call the API programmatically you must first establish a session by logging in
through the normal flow so the server issues valid `GX_SESSION_ID` / `JSESSIONID` /
`AJAX_SECURITY_TOKEN`. These are not forgeable.

---

## 4. Request body (form-urlencoded)

Top-level fields:

| Field | Captured value (redacted) | Interpretation |
|---|---|---|
| `GXEvent` | `<64-hex hash>` | Opaque hash the server maps to a specific server-side event handler (e.g. the "continuar / elegir medio de pago" button). Stable per event, not per session. |
| `GXParm0` | *(empty)* | — |
| `GXParm1` | `<accountKey>` | Internal account key (= `GXParm3` + trailing `0`). |
| `GXParm2` | `[]` (`%5B%5D`) | Empty JSON array (selected items?). |
| `GXParm3` | `<accountKey>` | Account/contract key. Also appears in the Referer. |
| `GXParm4` | `AIngreso` | Mode/action flag (screen "Ingreso"). |
| `GXParm5` | *(empty)* | — |
| `GXParm6..GXParm13` | `0` / `false` | Flags / counters (mostly zero). |
| `GXParm14` | **big JSON** (see §5) | The full debt-detail grid state. |
| `GXParm15` | `0` | — |
| `GXParm16` | `106` | **Empresa / company code** (106). |
| `GXParm17` | `<cliente>` | **Cliente (customer number)**. |
| `GXParm18` | `2` | **Suffix / subcuenta** (customer `<cliente>/2`). |
| `GXParm19` | `MPAG` | Screen/flow code — "Medio de PAGo" (payment-method step). |
| `GXParm20` | `N` | Boolean-ish flag ("N" = no). |

`GXParm16/17/18` together = the identity `106 · <cliente> · 2`, matching the account
key in `GXParm1/3` and the `Referer` (`...,<cliente>,2,AIngreso,`).

---

## 5. `GXParm14` — debt-detail payload (JSON, URL-encoded)

This is the state of the on-screen "Detalle de deuda" grid, sent back to the server.
Structure:

```jsonc
{
  "TextoEncabezado": "Cliente: <cliente>/<suffix>: <NAME>\nDomicilio: <ADDRESS>\nDetalle de deuda desde el <DATE>",
  "TextoEncabezadoVisible": "S",
  "Facturas": [ /* array of invoice objects, see below */ ],
  "TextoPie": "Cantidad de comprobantes: <COUNT> - Importe Total: <TOTAL>\nCant. comprobantes adeudados: <PENDING_COUNT> - Importe Adeudado: <PENDING_TOTAL>\nPuede existir deuda anterior. Consulte en nuestras oficinas.",
  "TextoPieVisible": "S"
}
```

### Invoice object (`Facturas[]`)

The grid uses a generic `CampoN{Titulo,Visible,Valor}` shape — column title, visibility
flag (`S`/`N`), and value. Mapping observed:

| Field | Título | Meaning | Example |
|---|---|---|---|
| Campo1 | Fecha | Issue date | `<DD/MM/YY>` |
| Campo2 | Comprobante | Invoice number | `FC   B-0000-00000000` |
| Campo3 | Fecha Vto | Due date | `<DD/MM/YY>` |
| Campo4 | Total Factura | Invoice total | `<AMOUNT>` |
| Campo5 | Cuota Adeudada | Which installment owed | `Ninguna` / `Ambas` |
| Campo6 | Tipo | Document type | `FACTURA MASIVA` |
| Campo7 | Saldo | Outstanding balance | `$         0.00` |
| Campo8 | Pagar | Pay options string | `#Pago Total <AMOUNT>#Cuota 1 <AMOUNT>#Cuota 2 <AMOUNT>` |
| Campo9 | Pagado | Paid flag (`Visible:N`, internal) | `S` / `N` |
| Campo10 | Estado | Status | `Pagado` / `Impaga` |
| Campo11 | Domicilio | Address (hidden, `Visible:N`) | `<ADDRESS>` |
| Campo12 | Barra 1 | Payment barcode, installment 1 (hidden) | `<SYNTHETIC_BARCODE_1>` |
| Campo13 | Barra 2 | Payment barcode, installment 2 (hidden) | `<SYNTHETIC_BARCODE_2>` |
| Campo14 | Marca en proceso cuota1 | "in process" flag c1 (hidden) | |
| Campo15 | Marca en proceso cuota2 | "in process" flag c2 (hidden) | |
| Campo16 | Fecha grabac TRBANR1 cuota1 | bank-record timestamp c1 (hidden) | |
| Campo17 | Fecha grabac TRBANR1 cuota2 | bank-record timestamp c2 (hidden) | |
| Campo18 | Parametro Tolerancia horas | grace-period hours param (hidden) | `1` |
| `Identificador` | — | Unique invoice key | `<SYNTHETIC_INVOICE_ID>` |
| `ImpresionIndividual` | — | Printable individually | `S` |
| `ImpresionCupon` | — | Coupon printable | `S` |

`Identificador` decodes roughly as an account prefix, suffix, issue date,
comprobante, and rubro (`ENER` = energía). Keep live identifiers out of examples.

### The barcode fields (`Campo12/13Valor`)

Only populated for **unpaid** invoices. They are Argentine bill-payment barcodes
(Pago Fácil / Rapipago / bank "link" networks). Example (installment 1):

```
<SYNTHETIC_BARCODE_1>
```

Embeds a company/rubro prefix, comprobante, amount field, due date, and check
digit. Do not document a live barcode or invoice amount.

---

## 6. What this particular call does

- Screen flow `MPAG` ("medio de pago"), mode `AIngreso`, for customer **106 / <cliente> / 2**.
- Posts the current debt grid back to the server.
- The grid can contain paid and unpaid invoices, with payment barcodes on unpaid rows.
- Live counts, invoice numbers, amounts, and barcodes are intentionally omitted.

So this is the step where the user, having reviewed the debt detail, proceeds toward
selecting a payment method for the outstanding invoice. The `GXEvent` hash is the
"continue / go to payment" server event.

---

## 7. Notes for building against it

1. **Session first.** You cannot call this cold — you need a live authenticated
   session (`GX_SESSION_ID`, `JSESSIONID`, matching `AJAX_SECURITY_TOKEN`). Automate
   the login flow first, then reuse the cookies + token.
2. **`GXEvent` is opaque.** Its hash is generated server-side per event/page; scrape it
   from the rendered page rather than hardcoding — it can change on redeploys.
3. **The grid is server-authoritative, but state is round-tripped.** GeneXus sends the
   current control values (`GXParm14`) back. For a read-only integration you likely
   want an *earlier*, simpler event that just *returns* the debt detail rather than this
   payment-progression event.
4. **Prefer an official channel if one exists.** Check whether EDERSA exposes a
   documented API or a "cuenta digital" / billing export before depending on this
   internal GeneXus AJAX protocol, which is brittle across deployments.
5. **Respect terms of use & rate limits.** This is a production billing/payment system;
   only automate access to your own account and within the portal's terms.

---

## 8. Sensitive values seen in the capture (do NOT commit real ones)

- `AJAX_SECURITY_TOKEN` — session anti-CSRF token.
- `GX_SESSION_ID`, `JSESSIONID` — session identifiers.
- Customer name, service address, account `<cliente>/2` — PII.
- Payment barcodes — allow anyone to pay/identify the bill; treat as sensitive.

Keep these in a local, git-ignored secrets/config file, never in source.

---

## 9. Login — Oficina Virtual (`tramites.edersa.com.ar`)

Login is a **separate GeneXus app** from the payment portal:

```
GET/POST /OFICINA_VIRTUAL_PROD_EDERSA/servlet/com.oficinavirtual.login
Host: tramites.edersa.com.ar
```

- `GET` issues fresh `GX_SESSION_ID`, `GX_CLIENT_ID`, `JSESSIONID` cookies and renders
  `MAINFORM` (`method=post`, `action=com.oficinavirtual.login`).
- Fields:
  - `vUSUARIO` — **email** (config `UsuNomEmail=true`; placeholder text "Email").
  - `vPASSWORD` — password.
  - `BTNENTER` — submit button, `data-gx-evt="5"` ("Iniciar sesión").
  - `GXState` — hidden field (single-quoted) carrying `AJAX_SECURITY_TOKEN` (96 chars),
    `GX_AJAX_KEY`, `GX_AJAX_IV`, and per-variable `gxhash_*` JWTs.
- The submit is a **GeneXus WorkWithPlus AJAX event** (`GXEvent=gx.ajax.encryptParms(...)`,
  AES with the per-session `GX_AJAX_KEY`/`GX_AJAX_IV`), so replicating login with raw
  HTTP is brittle. **Drive the form with a headless browser** (`login.py`).
- **Confirmed:** a successful login POST returns
  `{"gxCommands":[{"redirect":{"url":"com.oficinavirtual.wwpbaseobjects.home",...}}]}`.

### SSO handoff to the Portal de Clientes (confirmed)

Login lands on the Oficina Virtual **home** (`com.oficinavirtual.wwpbaseobjects.home`),
which lists the user's accounts and a card **"ACCESO FACTURAS Y PAGOS"**. Its anchor
(`<a data-gx-evt="5">`, caption "Ir a Facturas y Pagos") fires a GeneXus event that
**navigates the same tab to** `pagos.edersa.com.ar/PortalClientes_EDERSA_PROD/...
rwdhomemaster?<accountKey>,<cliente>,<suffix>,AIngreso,` and sets fresh
`pagos.edersa.com.ar` session cookies. From there the debt read in §10 works.
`login.py` automates exactly this and returns the pagos cookies + account querystring.
(Note: the account has multiple suministros, e.g. `…/1` and `…/2`; the handoff opens
the currently-selected "Cuenta Actual".)

### Config leaked in the login page's `GXState` (`vEMPRESACONFIG`)

The client-side state exposes backend infrastructure details:
`EmpresaID=106`, an internal `WSHost`/`WSUrl` (`/OFICINA_VIRTUAL_WS_PROD_EDERSA/servlet/`),
server `BaseDir` paths, an internal SMTP host/IP, and sender `noreply@edersa.com.ar`.
This is EDERSA's disclosure (visible to any client), not something to reproduce — see §11.

---

## 10. Read path (confirmed working)

An **authenticated GET** of the portal home returns the full debt dataset — no need to
replicate the encrypted AJAX event from the original capture:

```
GET /PortalClientes_EDERSA_PROD/servlet/com.portalclientes.edersa.rwdhomemaster?<accountKey>,<cliente>,<suffix>,AIngreso,
Cookie: GX_SESSION_ID=…; GX_CLIENT_ID=…; JSESSIONID=…
```

- The querystring (`EDERSA_HOME_QS`) supplies the account context. **Without it the home
  renders but the grid is empty** (verified: 0 invoices).
- The response HTML embeds the debt payload inside the `GXState` hidden field, under
  `vSALWSCONSULTAFACTURAS` — same `{TextoEncabezado, Facturas[], TextoPie}` shape as
  `GXParm14` in §5.
- `edersa_client.py` implements exactly this: GET → extract `GXState` → parse
  `vSALWSCONSULTAFACTURAS` → structured JSON. **Verified against the live session: 30
  invoices, totals, and the single unpaid invoice + barcode parsed correctly.**

### Account selection (confirmed)

- The querystring is `<accountKey>,<cliente>,<suffix>,AIngreso,` but **the server keys
  off `cliente,suffix` only — the leading `<accountKey>` is ignored** (verified: `0,...`
  and a bogus key both return the correct account). The account key is also unstable
  across captures, so build the querystring as `0,<cliente>,<suffix>,AIngreso,`.
- **One authenticated session serves multiple accounts.** A login may own several
  accounts; they're listed on the Oficina Virtual home account selector as
  `cliente/suffix | address`. `get_invoices.py` discovers them all and reads each with
  the same pagos session (verified with 2 accounts).

---

## 11. Security observations (informational)

Noticed while documenting — you may want to report these to EDERSA:

1. **Internal infra disclosure.** The login page's client-side `GXState`
   (`vEMPRESACONFIG`) exposes an internal service host/URL, server filesystem paths,
   and an internal SMTP host/IP. This is more than a browser client needs.
2. **Sensitive data in a round-tripped control.** The full billing history + payment
   barcodes travel in `GXParm14`/`GXState` on the client. Payment barcodes let anyone
   pay/identify a bill — treat captured payloads as sensitive.

These are the utility's to fix; noted here only so you handle captures carefully.
