# OAuth Security Audit

Status: implementation baseline review, 2026-09-19

## Addressed findings

| Severity | Finding | Resolution |
| --- | --- | --- |
| HIGH | `/oauth/authorize` required an OAuth bearer token for the modern browser flow | Hosted login and server-side browser sessions are now available; the bearer path remains for compatibility. |
| HIGH | Browser authorization had no protected pending-request state | OAuth parameters are stored server-side behind an opaque, short-lived request ID and CSRF token. |
| HIGH | Authorization-code replay was possible unless consumption was atomic | DynamoDB conditional consumption remains required before token issuance. |
| HIGH | Modern PKCE exchange did not bind the code to a submitted client ID | PKCE codes require `client_id` and reject mismatches. |
| MEDIUM | Login had no hosted session/logout mechanism | `/login` creates an HttpOnly session cookie and `/logout` revokes it. |
| HIGH | Login CSRF token was not browser-bound | Pending-request CSRF values are checked against a short-lived `login_csrf` cookie. |
| MEDIUM | Password-grant usage was not observable without credential logging | Password-grant use emits a structured telemetry event without username, password, or tokens. |

## Remaining findings

| Severity | Finding | Required follow-up |
| --- | --- | --- |
| MEDIUM | Existing client records may omit grant restrictions | New registrations can set optional `allowed_grant_types`; omitted values preserve legacy behavior. |
| MEDIUM | Legacy non-PKCE authorization-code exchanges remain accepted for compatibility | Migrate remaining clients, then require PKCE for all public clients. |
| MEDIUM | Redirect URI normalization permits equivalent default ports/trailing slash handling | Confirm the registration contract and move to exact RFC-compliant matching if required. |
| LOW | Password-grant metric has no client-id dimension | Keep the metric aggregate-only; client context remains in structured logs without credentials. |
| LOW | Login error and session behavior need broader negative integration coverage | Add tests for expired sessions, expired pending requests, replayed CSRF tokens, and logout. |

## Credential and token handling

- Passwords are sent only to the user-service validation endpoint.
- `/login` never issues OAuth tokens directly.
- Authorization codes and session IDs are opaque random values.
- Access tokens, refresh tokens, authorization codes, PKCE verifiers, and
  passwords must not be logged.
- `grant_type=password` remains supported only as a legacy compatibility path.
