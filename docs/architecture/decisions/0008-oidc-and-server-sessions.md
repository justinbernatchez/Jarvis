# ADR-0008: Use OIDC with Server-Side Browser Sessions

- Status: Accepted
- Date: 2026-08-18

## Context

JARVIS begins as a personal cloud-ready web application but must later support
multiple users and non-browser clients. The architecture should avoid storing
long-lived identity-provider tokens in browser storage and should not couple
domain code to one managed identity vendor.

## Decision

Use standards-based OIDC Authorization Code with PKCE. FastAPI handles
`/api/v1/auth/login`, `/api/v1/auth/callback`, and
`/api/v1/auth/logout`, then creates an opaque, revocable application session.

OIDC validation is fail closed:

- exact issuer allowlist and HTTPS discovery/JWKS;
- permitted signature algorithms and key rotation;
- signature, `iss`, `aud`/`azp`, `exp`, `iat`, nonce, and authentication-time
  validation;
- single-use server-side state and PKCE verifier with short expiry;
- exact redirect URI construction;
- required MFA assurance for owner/admin access.

Browser session requirements:

- cookie name begins with `__Host-`;
- `Secure`, `HttpOnly`, `SameSite=Lax`, path `/`, and no Domain attribute;
- only a versioned keyed-HMAC digest of the opaque token is stored, with an
  explicit verification-key rotation procedure;
- session rotation occurs after login and privilege changes;
- logout and administrative revocation take immediate effect;
- Origin validation and CSRF tokens protect state-changing requests;
- web assets and `/api` are served under one origin.

External identities are mapped by `(issuer, subject)`. Email is profile data,
not an identity key. JARVIS owns roles and workspace memberships instead of
trusting provider role claims.

The initial deployment allowlists the owner's `(issuer, subject)` and uses
provider-enforced MFA. Email is not an allowlist key. Open registration is
disabled.

Future desktop, mobile, and agent clients use a separate OIDC PKCE/bearer-token
path with explicit API audiences.

## Consequences

Benefits:

- no refresh token is stored in browser-accessible storage;
- sessions can be revoked immediately;
- a managed or self-hosted OIDC provider can be substituted;
- application roles remain consistent across providers.

Costs:

- browser requests require a session lookup;
- FastAPI owns callback, CSRF, rotation, and expiry behavior;
- same-origin routing is part of the deployment contract;
- non-browser clients need a separate, carefully scoped token path.

