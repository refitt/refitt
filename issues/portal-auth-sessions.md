---
status: unshaped
kind: feature
appetite: big
lane: public
---

# Give browser sessions a real auth lifecycle

## Problem

REFITT's auth was designed for machine clients. Invariant §5 describes the posture:
- Credentials are one key:secret pair per user, enforced by `Client.user_id unique`
  (`model.py:454`).
- `GET /token` with HTTP Basic mints a Fernet bearer token (`route/token.py:26-30`). Its `sub` is the
  `Client.id`, it lasts 900 s by default (`model.py:552`), and `exp=-1` means it never expires
  (`api/token.py:284-286,310`).
- Bearer validation decrypts the token, checks `exp` with a naive `datetime.now()`
  (`server/auth.py:68`), loads the client, and checks `valid`. **It never consults the `Session`
  row.** That is the revocation gap invariant §5 already records: re-issuing a token or rotating the
  secret leaves earlier tokens valid until they expire, and only `Client.valid=false` cuts
  everything off.
- The token is misnamed `JWT` (`api/token.py:252`) and is not RFC 7519.
- The rootkey is cached for the process lifetime (`api/token.py:76-80`). There is no key rotation
  (no MultiFernet), so rotating the rootkey invalidates every token.

**What a browser portal needs that is absent:**
1. **Human login.** `User` has no credential fields. The SDK's `login()` opens a web page, asks for
   the key:secret with `input()`, and stores the secret in `~/.refitt/config.toml`
   (`api/request.py:85-112`). There is no SSO/OIDC, password, or magic-link flow, and no account
   lifecycle.
2. **A session model for browsers.**
   - Refreshing requires the long-lived secret (`api/request.py:119-136`), so a browser would have to
     hold it.
   - A backend-for-frontend with HttpOnly cookies needs CSRF protection, which is absent (AGENTS.md
     §3).
   - There is no refresh-token rotation and no logout or server-side revocation.
   - `Session.client_id unique` (`model.py:559-560`) allows one session row per client, so one
     device logging in replaces another.
3. **Safe methods.** The routes that mint or rotate credentials are GETs: `GET /token`,
   `GET /token/<id>`, `GET /client/<id>` (rotates key and secret), and `GET /client/secret/<id>`
   (`route/token.py`, `route/client.py`). GETs are prefetched and cached by browsers and are
   CSRF-exposed under cookie auth. They also break §7.

## Why it was deferred

This redesigns invariant §5's auth posture and §7's session rules, both Tier 1, with a human gate on
every CONFIRMED finding. It needs schema changes ([`db-migrations.md`](db-migrations.md)) and the app
factory. **Pre-existing.**

## Outcome / vision

Humans sign in to refitt.org with a supported identity flow. Browser sessions use short-lived access
tokens and rotating refresh tokens (or a backend-for-frontend with HttpOnly cookies and CSRF
protection), with real logout and server-side revocation, and several concurrent sessions per user.
Credential-minting endpoints are non-GET. Machine clients keep a key:secret path. The rootkey can
rotate without logging everyone out.

## Sketch of the acceptance criteria

- **R1** — WHEN a session is revoked, every access token issued under it SHALL be rejected on its
  next use.
- **R2** — WHEN a user signs in on a second device, the first device's session SHALL remain valid.
- **R3** — No route that creates, rotates or reveals a credential SHALL be reachable with GET.
- **R4** — WHEN the token-encryption key is rotated, tokens issued under the previous key SHALL
  remain valid until they expire.
- **R5** — WHEN a browser session uses cookie authentication, every state-changing request without a
  valid CSRF token SHALL be refused.
- **R6** — WHEN a machine client authenticates with key:secret, it SHALL work as before.

## Notes

- Shaping decisions:
  - The identity provider (institutional SSO / CILogon, OIDC, local accounts).
  - Bearer-in-browser vs. backend-for-frontend.
  - Whether the inverted 401/403 mapping survives. Browser interceptors expect 401 for "re-auth".
  - The migration path for existing machine clients and the published SDK.
- `api/token.py`, `server/auth.py` and the token/client routes are high-blast-radius. The §5/§7 text
  changes through `/rf-harness`.
- Related: [`api-app-factory.md`](api-app-factory.md),
  [`api-contract-portal.md`](api-contract-portal.md), [`seed-dataset-v2.md`](seed-dataset-v2.md)
  (personas).
- Found by: out-of-cycle roadmap evidence sweep, 2026-10-04.
