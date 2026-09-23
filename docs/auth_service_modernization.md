# Auth Service Modernization — Authorization Code + PKCE Migration

## 1. Objective

Modernize `mobal/auth-service` so that SPA clients use:

- OAuth 2.0 Authorization Code Flow
- PKCE with `S256`
- Authorization Server hosted login page
- Server-side browser authentication session

The existing OAuth 2.0 Resource Owner Password Credentials grant:

    grant_type=password

is DEPRECATED but MUST remain supported for backwards compatibility.

This project MUST NOT remove or disable the password grant.

The target state is:

    NEW SPA CLIENTS
        -> Authorization Code + PKCE

    LEGACY CLIENTS
        -> Password Grant
        -> still supported
        -> deprecated
        -> compatibility only

Normal email/password authentication remains supported.

The deprecated component is specifically the OAuth grant:

    grant_type=password

NOT password-based user authentication itself.

## 1.1 Repository Baseline (2026-09-19)

This plan was reconciled with the current repository before implementation.
The following is the verified starting point:

- `POST /oauth/token` supports `password`, `refresh_token`,
  `authorization_code`, and `client_credentials` through
  `app/routers/oauth/auth_router.py`.
- `grant_type=password` is currently operational and already returns a
  deprecation `Warning` header. It MUST remain compatible.
- `GET /oauth/authorize` currently requires an OAuth bearer token through
  `get_jwt_bearer`; there is no browser authentication session, `/login` route,
  logout route, or pending authorization-request store.
- Authorization codes are stored in DynamoDB with a 10-minute TTL and are
  atomically marked consumed before exchange validation. The repository stores
  `client_id`, `redirect_uri`, and PKCE fields.
- Authorization-code exchange validates the redirect URI and PKCE, but the
  token request model does not carry `client_id`; client binding at exchange is
  therefore not yet enforced.
- PKCE accepts both `S256` and `plain`, and missing method defaults to `plain`.
  SPA/public-client policy must be added explicitly.
- Redirect URI validation exists, but `_validate_redirect_uri` currently skips
  validation when client lookup raises and allows clients without registered
  redirect URIs. This behavior requires a security decision and tests before
  the endpoint becomes browser-facing.
- The OAuth client model contains `id`, `name`, `secret`, `scopes`, and
  `redirect_uris`; it does not currently contain per-client allowed grant
  types or an explicit public-client flag.
- The existing tests cover token grants, bearer authorization, PKCE storage and
  authorization-code consumption, but do not yet cover the complete hosted
  login flow.

This baseline is descriptive, not an implementation commitment. Epic 1 must
confirm it and record any changes in `docs/auth-current-flow.md` and
`docs/oauth-security-audit.md` before behavior is changed.

## 1.2 Implementation Status

The first modernization increment is implemented:

- hosted `/login` GET/POST flow with CSRF-protected pending requests;
- DynamoDB-backed browser sessions and logout;
- session-aware `/oauth/authorize` with a compatibility bearer path;
- `S256` enforcement for the browser/public-client path;
- client binding for PKCE authorization-code exchanges;
- infrastructure tables, IAM access, integration coverage, and architecture
  documentation.

Remaining work is tracked in the audit and includes populating explicit client
grant permissions for new registrations, broader negative security tests, and
SPA application changes outside this repository.

---

# 2. Standards

Implementation should follow:

- RFC 6749 — OAuth 2.0 Authorization Framework
  - Section 4.1 — Authorization Code Grant

- RFC 7636 — Proof Key for Code Exchange (PKCE)

- RFC 9700 — Best Current Practice for OAuth 2.0 Security

Important architectural requirements:

- Resource Owner Password Credentials is considered legacy/deprecated.
- It remains implemented only for backwards compatibility.
- New SPA clients MUST NOT use password grant.
- SPA is a public OAuth client.
- SPA MUST NOT have a client secret.
- Authorization Code Flow MUST use PKCE.
- PKCE MUST use `S256`.
- Authorization codes MUST be short-lived.
- Authorization codes MUST be single-use.
- Redirect URIs MUST be validated against registered redirect URIs.
- New SPA authentication MUST NOT send user credentials to `/oauth/token`.

---

# 3. Supported Grant Types

The Authorization Server should support:

    authorization_code

        Preferred interactive authentication mechanism.

        Required for SPA clients.

        SPA clients MUST use PKCE with S256.


    refresh_token

        Used to obtain new access tokens.


    client_credentials

        Used for machine-to-machine authentication where applicable.


    password

        DEPRECATED.

        Retained for backwards compatibility.

        MUST NOT be used by new SPA clients.

        MUST NOT be removed as part of this project.

---

# 4. Current Architecture

The existing SPA authentication approximately behaves as:

    SPA
     |
     | email + password
     v
    POST /oauth/token

    grant_type=password
    username=...
    password=...

     |
     v

    access_token
    refresh_token


The project already contains parts of Authorization Code / PKCE infrastructure.

The implementation MUST be audited before adding parallel or replacement code.

Reuse existing components where they are correct.

---

# 5. Target Architecture

Modern SPA authentication:

    SPA
     |
     | generate:
     |
     | code_verifier
     | code_challenge
     | state
     |
     v
    GET /oauth/authorize
     |
     | no authenticated browser session
     v
    Authorization Server Login Page
     |
     | email + password
     v
    POST /login
     |
     | authenticate user
     | create auth session
     v
    resume authorization request
     |
     v
    authorization code
     |
     v
    302 redirect
     |
     v
    SPA /callback?code=...&state=...
     |
     | validate state
     v
    POST /oauth/token

    grant_type=authorization_code
    code=...
    code_verifier=...

     |
     | validate authorization code
     | validate PKCE
     | consume authorization code
     v

    access_token
    refresh_token


Legacy authentication remains available:

    LEGACY CLIENT
         |
         | email + password
         v
    POST /oauth/token

    grant_type=password

         |
         v

    access_token
    refresh_token

---

# 6. Security Model

Three concepts MUST remain separate.

## User Authentication

Email/password answers:

    "Who is the user?"

It authenticates the resource owner.

---

## PKCE

PKCE answers:

    "Does the party exchanging this authorization code possess
     the verifier associated with the authorization request?"

PKCE does NOT authenticate the user.

---

## Authorization Code

Authorization code is a short-lived, single-use credential connecting:

    authenticated user
        +
    OAuth client
        +
    redirect URI
        +
    PKCE challenge

to the token exchange.

---

# EPIC 1 — Audit Existing OAuth Implementation

## Goal

Understand and document the current authentication and authorization
implementation before changing behavior.

Do NOT rewrite working components without a concrete reason.

---

## TASK 1.1 — Map Existing Authentication Flows

Inspect the repository and document:

- `/oauth/authorize`
- `/oauth/token`
- password grant
- authorization_code grant
- refresh_token grant
- client_credentials grant if applicable
- OAuth client model
- public/client authentication
- authorization code storage
- PKCE implementation
- access token issuance
- refresh token issuance
- token validation
- user-service communication
- redirect URI validation
- current `/oauth/authorize` Bearer-token requirement

Produce:

    docs/auth-current-flow.md

Include Mermaid diagrams for:

1. Password grant
2. Existing authorization code flow
3. Refresh token flow

### Acceptance Criteria

- Every authentication-related endpoint is documented.
- Relevant services are identified.
- Relevant repositories are identified.
- Relevant models are identified.
- Existing PKCE behavior is documented.
- Authorization-code lifecycle is documented.
- Existing password-grant behavior is documented.
- No production behavior changes in this task.

---

## TASK 1.2 — OAuth Security Audit

Review the implementation against:

- RFC 6749
- RFC 7636
- RFC 9700

Inspect at minimum:

- authorization-code entropy
- authorization-code TTL
- authorization-code single-use behavior
- atomic authorization-code consumption
- PKCE verifier validation
- S256 implementation
- whether `plain` PKCE is accepted
- redirect URI validation
- exact redirect URI matching
- client_id binding
- redirect_uri binding
- refresh-token handling
- refresh-token rotation if implemented
- token leakage through logs
- credential leakage through logs
- error responses
- CORS configuration
- SPA client secrets
- `/oauth/authorize` authentication model
- password-grant implementation

Produce:

    docs/oauth-security-audit.md

Classify findings:

    CRITICAL
    HIGH
    MEDIUM
    LOW

Do NOT remove password grant during this audit.

---

# EPIC 2 — Authorization Server Browser Session

## Goal

Allow `/oauth/authorize` to identify an authenticated browser user without
requiring an existing OAuth Bearer access token.

The Authorization Server must maintain its own browser authentication session.

---

## TASK 2.1 — Implement Authentication Session

Implement a server-side browser authentication session.

Recommended model:

Browser stores:

    session_id=<opaque-random-value>

Server stores:

    session_id
    user_id
    created_at
    expires_at

The browser cookie MUST NOT contain:

- password
- access token
- refresh token
- authorization code

### Cookie Requirements

Production cookie configuration:

    HttpOnly
    Secure
    SameSite=Lax
    Path=/

Evaluate whether additional cookie attributes are appropriate for the deployed
domain architecture.

Session IDs must:

- be cryptographically random
- contain sufficient entropy
- expire
- be revocable

### Acceptance Criteria

- Browser session identifies authenticated user.
- Session expiration works.
- Session revocation works.
- Session cookie is HttpOnly.
- Production cookie is Secure.
- Passwords are never stored in session.
- Access tokens are not used as browser login sessions.

---

## TASK 2.2 — Pending Authorization Request

When an unauthenticated browser calls:

    GET /oauth/authorize

the authorization request must survive the login process.

Create a short-lived pending authorization request.

Example model:

    request_id
    client_id
    redirect_uri
    response_type
    scope
    state
    code_challenge
    code_challenge_method
    created_at
    expires_at

Browser receives only an opaque:

    request_id

The server stores the trusted authorization parameters.

Do NOT trust OAuth parameters reposted from arbitrary browser form fields after
authentication.

### Acceptance Criteria

- Pending authorization requests expire.
- request_id is cryptographically unpredictable.
- OAuth parameters cannot be modified during login.
- Successful login resumes the exact original authorization request.
- Invalid request_id fails safely.
- Expired request_id fails safely.

---

# EPIC 3 — Authorization Server Login UI

## Goal

Provide a minimal server-rendered login page from FastAPI.

Do NOT introduce React, Vue or another SPA framework into the auth-service.

Prefer:

    FastAPI
    +
    Jinja2
    +
    minimal CSS

---

## TASK 3.1 — Implement GET /login

Implement:

    GET /login?request_id=...

Render a minimal login page containing:

- product/logo area
- email input
- password input
- Sign in button
- accessible error area
- responsive layout

Suggested structure:

    app/
      templates/
        base.html
        login.html

      static/
        auth.css

UI style:

- modern
- minimal
- responsive
- centered login card
- no unnecessary JavaScript
- accessible form controls

### Form Requirements

Email:

    type="email"
    autocomplete="username"

Password:

    type="password"
    autocomplete="current-password"

### Acceptance Criteria

- Works without JavaScript.
- Works on mobile.
- Works on desktop.
- Password is never rendered back into HTML.
- Error messages do not disclose whether an account exists.
- request_id is preserved safely.

---

## TASK 3.2 — Implement POST /login

Implement credential authentication.

Example:

    POST /login

    request_id=<opaque-request-id>
    email=user@example.com
    password=...

Behavior:

1. Validate pending authorization request.
2. Authenticate email/password using existing authentication logic.
3. If authentication fails:
   - return login page
   - show generic error
4. If authentication succeeds:
   - create browser authentication session
   - resume pending authorization request

IMPORTANT:

`/login` MUST NOT issue OAuth tokens.

It authenticates the browser user only.

### Successful Conceptual Flow

    POST /login
        |
        v
    validate credentials
        |
        v
    user_id
        |
        v
    create auth session
        |
        v
    continue authorization request

### Acceptance Criteria

`POST /login` MUST NOT directly return:

    access_token
    refresh_token

Invalid credentials return a generic message:

    Invalid email or password.

Do not reveal:

    user does not exist

versus:

    password is incorrect

---

## TASK 3.3 — Login CSRF Protection

Protect the login flow against CSRF/login-CSRF as appropriate for the selected
session architecture.

CSRF values must:

- be unpredictable
- be bound to the relevant browser/session/request
- expire
- be validated

Add negative tests.

---

# EPIC 4 — Refactor /oauth/authorize

## Goal

Make `/oauth/authorize` the browser entry point for modern OAuth authorization.

It must no longer require a pre-existing OAuth access token to identify the user.

---

## TASK 4.1 — Session-Aware Authorization Endpoint

Expected request:

    GET /oauth/authorize
        ?response_type=code
        &client_id=my-spa
        &redirect_uri=https://app.example.com/callback
        &code_challenge=...
        &code_challenge_method=S256
        &state=...

### If No Authentication Session Exists

    validate authorization request
        |
        v
    create pending authorization request
        |
        v
    redirect to:

    /login?request_id=...

### If Authentication Session Exists

    validate authorization request
        |
        v
    identify authenticated user
        |
        v
    create authorization code
        |
        v
    redirect to registered redirect_uri

### Acceptance Criteria

- Bearer access token is not required for browser authorization.
- Unknown client_id is rejected.
- Invalid redirect_uri is rejected.
- Unsupported response_type is rejected.
- PKCE is required for SPA/public clients.
- S256 is required for SPA/public clients.
- state is returned unchanged when supplied.
- Authorization code is associated with authenticated user.

---

## TASK 4.2 — Harden Authorization Codes

Every authorization code MUST be bound to:

    user_id
    client_id
    redirect_uri
    code_challenge
    code_challenge_method

Authorization code requirements:

- cryptographically unpredictable
- short-lived
- single-use
- atomically consumed

Recommended maximum lifetime:

    <= 10 minutes

Prefer a shorter lifetime if compatible with the existing architecture.

### Negative Tests

Must fail:

    same code used twice

    wrong client_id

    wrong redirect_uri

    expired code

    wrong code_verifier

---

# EPIC 5 — PKCE Hardening

## Goal

Ensure existing PKCE implementation is RFC 7636 compatible and safe for SPA
clients.

---

## TASK 5.1 — Require S256 for SPA/Public Clients

SPA generates:

    code_verifier = cryptographically_random_value

Then:

    code_challenge =
        BASE64URL(SHA256(ASCII(code_verifier)))

Authorization request:

    GET /oauth/authorize
        ...
        &code_challenge=<challenge>
        &code_challenge_method=S256

Token exchange:

    POST /oauth/token

    grant_type=authorization_code
    code=<authorization-code>
    client_id=<spa-client>
    redirect_uri=<registered-uri>
    code_verifier=<original-verifier>

Server calculates:

    BASE64URL(SHA256(code_verifier))

and compares it against the stored:

    code_challenge

### Acceptance Criteria

- S256 works.
- Missing verifier fails.
- Incorrect verifier fails.
- Missing challenge fails for SPA/public clients.
- `plain` is rejected for SPA/public clients.
- verifier format/length is validated.
- verifier is not logged.
- challenge is bound to the authorization code.

---

# EPIC 6 — SPA Migration

## Goal

Migrate the SPA away from:

    grant_type=password

The SPA must use:

    Authorization Code + PKCE

The server-side password grant remains available for legacy clients.

---

## TASK 6.1 — Implement Authorization Code + PKCE Client

SPA must:

1. Generate code_verifier.
2. Generate S256 code_challenge.
3. Generate unpredictable state.
4. Store verifier and state temporarily.
5. Redirect browser to `/oauth/authorize`.
6. Receive callback.
7. Validate returned state.
8. Exchange authorization code using verifier.
9. Handle resulting tokens using existing application token strategy.

Conceptual login:

    login()
        |
        +-> generate verifier
        |
        +-> generate challenge
        |
        +-> generate state
        |
        +-> store verifier/state
        |
        +-> window.location = /oauth/authorize

Callback:

    /auth/callback?code=...&state=...

Then:

    validate state

Then:

    POST /oauth/token

    grant_type=authorization_code
    client_id=...
    code=...
    redirect_uri=...
    code_verifier=...

### Acceptance Criteria

SPA contains NO:

    client_secret

SPA no longer sends:

    username
    password

to:

    /oauth/token

SPA login starts with browser navigation to:

    /oauth/authorize

---

## TASK 6.2 — Callback Error Handling

Handle:

- missing code
- missing state
- invalid state
- authorization error
- expired authorization code
- token exchange failure
- network failure

On state mismatch:

    DO NOT exchange authorization code.

Clear temporary PKCE/state values after:

- successful completion
- terminal failure

---

# EPIC 7 — Password Grant Deprecation and Compatibility

## Goal

Keep:

    grant_type=password

fully operational for existing consumers while explicitly treating it as a
legacy compatibility mechanism.

This project MUST NOT remove the password grant.

---

## TASK 7.1 — Mark Password Grant Deprecated

Update:

- README
- API documentation
- OpenAPI descriptions
- developer documentation
- examples

Clearly document:

    DEPRECATED:
    Resource Owner Password Credentials Grant

    This grant exists for backwards compatibility only.

    New SPA applications MUST use Authorization Code + PKCE.

Do NOT remove the implementation.

### Acceptance Criteria

Existing clients using:

    grant_type=password

continue to function.

Documentation no longer recommends password grant for new applications.

---

## TASK 7.2 — Add Password Grant Telemetry

Add telemetry for password-grant usage.

Track at minimum:

    oauth_password_grant_requests_total

Include:

    client_id

when safely available.

Example:

    oauth_password_grant_requests_total{
        client_id="legacy-client"
    }

Do NOT log:

- password
- access token
- refresh token
- authorization code
- session ID
- PKCE verifier

### Purpose

Telemetry should allow maintainers to determine which clients still depend on
the legacy grant.

Telemetry MUST NOT automatically disable the grant.

---

## TASK 7.3 — Restrict Password Grant to Legacy Clients Where Possible

Inspect the existing OAuth client model.

If it supports or can safely support allowed grant types, introduce:

    allowed_grant_types

Example legacy client:

    allowed_grant_types:
      - password
      - refresh_token

Example SPA:

    allowed_grant_types:
      - authorization_code
      - refresh_token

New SPA clients MUST NOT receive password grant permission.

IMPORTANT:

Do NOT introduce a breaking database migration solely to satisfy this task.

If introducing per-client grant permissions would create significant migration
risk:

1. document the limitation
2. create a follow-up task
3. preserve current compatibility

### Acceptance Criteria

- Existing legacy clients continue working.
- New SPA clients use authorization_code.
- Password grant is not recommended or automatically selected for SPA clients.

---

## TASK 7.4 — Preserve Legacy Password Grant

The existing password grant MUST remain functional.

Regression test:

    curl -X POST 'https://auth.example.com/oauth/token' \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode 'grant_type=password' \
      --data-urlencode 'client_id=legacy-client' \
      --data-urlencode 'username=user@example.com' \
      --data-urlencode 'password=secret'

Expected for a valid legacy client:

    {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "expires_in": ...
    }

Do NOT refactor password grant unnecessarily.

Changes to shared token issuance logic MUST preserve existing behavior.

### Required Regression Tests

    valid legacy password grant
        -> success

    invalid password
        -> authentication failure

    invalid user
        -> authentication failure without user enumeration

    refresh token
        -> unchanged

    authorization_code
        -> success

    authorization_code + PKCE
        -> success

---

# EPIC 8 — Logout

## TASK 8.1 — Authorization Server Logout

Implement:

    POST /logout

Behavior:

- invalidate Authorization Server browser session
- expire/delete browser session cookie
- do not accept arbitrary redirect destinations

If post-logout redirects are supported:

- register allowed logout redirect URIs
- strictly validate destination

### Acceptance Criteria

After logout:

    GET /oauth/authorize

requires authentication again.

Logout does NOT disable legacy OAuth tokens unless that behavior is explicitly
part of the existing token revocation model.

---

# EPIC 9 — Automated Security and Integration Tests

## TASK 9.1 — Full Modern Flow Test

Automated integration test:

    generate verifier
        |
        v
    generate challenge
        |
        v
    /oauth/authorize
        |
        v
    /login
        |
        v
    successful authentication
        |
        v
    authorization code
        |
        v
    /oauth/token + verifier
        |
        v
    access token + refresh token

Verify resulting access token can access an authenticated resource.

---

## TASK 9.2 — PKCE Attack Tests

### Stolen Code Without Verifier

Input:

    valid authorization code
    missing verifier

Expected:

    invalid_grant

---

### Wrong Verifier

Input:

    valid authorization code
    incorrect verifier

Expected:

    invalid_grant

---

### Authorization Code Replay

First exchange:

    success

Second exchange:

    invalid_grant

---

### Modified Redirect URI

Expected:

    failure

---

### Modified client_id

Expected:

    failure

---

## TASK 9.3 — Authorization Request Security Tests

Test:

- unregistered redirect_uri
- malformed redirect_uri
- unknown client
- missing PKCE for SPA
- `code_challenge_method=plain` for SPA
- expired pending login request
- modified pending authorization request
- invalid session
- expired session
- login CSRF failure
- authorization-code replay

---

## TASK 9.4 — Legacy Compatibility Tests

The modern authentication changes MUST NOT break password grant.

Automated tests must verify:

    POST /oauth/token
    grant_type=password

continues working for existing supported clients.

Also verify:

    refresh_token

behavior remains compatible.

These tests are mandatory before merging the modernization.

---

# EPIC 10 — Documentation

## TASK 10.1 — Architecture Documentation

Create:

    docs/authentication.md

Include the following Mermaid diagram:

    sequenceDiagram
        autonumber

        actor User
        participant SPA
        participant Auth as Auth Service
        participant UserService as User Service
        participant API

        SPA->>SPA: Generate code_verifier
        SPA->>SPA: Generate S256 code_challenge
        SPA->>SPA: Generate state

        SPA->>Auth: GET /oauth/authorize + challenge + state

        alt No authentication session
            Auth-->>User: Render login page
            User->>Auth: POST /login email + password
            Auth->>UserService: Authenticate credentials
            UserService-->>Auth: User identity
            Auth->>Auth: Create browser session
        end

        Auth->>Auth: Create authorization code
        Auth-->>SPA: 302 callback?code=...&state=...

        SPA->>SPA: Validate state

        SPA->>Auth: POST /oauth/token<br/>code + code_verifier

        Auth->>Auth: Validate authorization code
        Auth->>Auth: Validate PKCE
        Auth->>Auth: Atomically consume code

        Auth-->>SPA: access_token + refresh_token

        SPA->>API: Authorization: Bearer access_token
        API-->>SPA: Protected resource

Explicitly document:

    Password authenticates the user.

    PKCE does NOT authenticate the user.

    PKCE proves possession of the verifier associated with
    the authorization request.

Also document the legacy path:

    grant_type=password

as:

    DEPRECATED — BACKWARDS COMPATIBILITY ONLY

---

# SPRINT 1 — Audit and Foundation

## Goal

Understand the existing implementation and build the browser-session foundation
without breaking any current authentication mechanism.

## Scope

- TASK 1.1 — Map existing authentication flows
- TASK 1.2 — OAuth security audit
- TASK 2.1 — Authentication session
- TASK 2.2 — Pending authorization request

## Deliverable

Auth-service can maintain browser authentication state and pending authorization
requests.

Existing flows continue working.

### Critical Constraint

DO NOT change or remove password grant behavior.

---

# SPRINT 2 — Login and Authorization Flow

## Goal

Implement Authorization Server hosted authentication and connect it to the
existing authorization-code infrastructure.

## Scope

- TASK 3.1 — Login UI
- TASK 3.2 — Login POST
- TASK 3.3 — Login CSRF
- TASK 4.1 — Session-aware `/oauth/authorize`
- TASK 4.2 — Authorization-code hardening
- TASK 5.1 — PKCE hardening

## Deliverable

The following works end-to-end in development:

    /oauth/authorize
        |
        v
    /login
        |
        v
    authorization code
        |
        v
    /oauth/token
        |
        v
    tokens

At the same time:

    grant_type=password

continues working.

---

# SPRINT 3 — SPA Migration

## Goal

Move the SPA from password grant to Authorization Code + PKCE.

## Scope

- TASK 6.1 — SPA PKCE implementation
- TASK 6.2 — Callback/error handling
- TASK 7.1 — Password grant deprecation documentation
- TASK 7.2 — Password grant telemetry
- TASK 7.3 — Grant restrictions where safe
- TASK 9.1 — Full flow integration tests
- TASK 9.2 — PKCE attack tests
- TASK 9.3 — Authorization security tests

## Deliverable

Production SPA uses:

    authorization_code + PKCE/S256

Production SPA no longer uses:

    grant_type=password

Authorization Server STILL supports:

    grant_type=password

for backwards compatibility.

---

# SPRINT 4 — Stabilization and Compatibility

## Goal

Finalize the new architecture while guaranteeing backwards compatibility.

## Scope

- TASK 7.4 — Legacy password grant regression tests
- TASK 8.1 — Logout
- TASK 9.4 — Legacy compatibility tests
- TASK 10.1 — Architecture documentation
- README update
- OpenAPI update
- dead SPA password-grant code cleanup
- final security review

## Deliverable

Two supported paths exist.

### Modern

    SPA
        |
        v
    Authorization Code
        +
    PKCE S256
        |
        v
    access/refresh tokens

### Legacy

    Legacy Client
        |
        v
    grant_type=password
        |
        v
    access/refresh tokens

Legacy path is:

    supported
    +
    tested
    +
    monitored
    +
    deprecated

It is NOT removed.

---

# Manual Acceptance Test — Modern Flow

## 1. Generate PKCE Values

    CODE_VERIFIER=$(openssl rand -base64 64 | tr -d '=+/' | cut -c1-64)

    CODE_CHALLENGE=$(printf '%s' "$CODE_VERIFIER" \
      | openssl dgst -sha256 -binary \
      | openssl base64 -A \
      | tr '+/' '-_' \
      | tr -d '=')

    STATE=$(openssl rand -hex 32)

---

## 2. Start Authorization

Open in browser:

    https://auth.example.com/oauth/authorize\
    ?response_type=code\
    &client_id=my-spa\
    &redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback\
    &code_challenge=<CODE_CHALLENGE>\
    &code_challenge_method=S256\
    &state=<STATE>

Expected:

    Authorization Server login page

if no browser session exists.

---

## 3. Authenticate

Enter email/password.

Expected:

    HTTP 302

to:

    https://app.example.com/callback?code=<CODE>&state=<STATE>

---

## 4. Verify State

Returned state MUST equal original state.

If:

    returned_state != original_state

then:

    ABORT

Do NOT exchange authorization code.

---

## 5. Exchange Authorization Code

    curl -X POST 'https://auth.example.com/oauth/token' \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode 'grant_type=authorization_code' \
      --data-urlencode 'client_id=my-spa' \
      --data-urlencode 'redirect_uri=https://app.example.com/callback' \
      --data-urlencode 'code=<CODE>' \
      --data-urlencode "code_verifier=$CODE_VERIFIER"

Expected:

    {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "expires_in": ...
    }

---

## 6. Verify Wrong PKCE Fails

Use a fresh authorization code but exchange with:

    code_verifier=WRONG

Expected OAuth error:

    invalid_grant

---

## 7. Verify Authorization Code Replay Fails

Exchange a valid authorization code successfully.

Then attempt to exchange the same code again.

Expected:

    invalid_grant

---

# Manual Acceptance Test — Legacy Compatibility

Password grant MUST continue working.

    curl -X POST 'https://auth.example.com/oauth/token' \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode 'grant_type=password' \
      --data-urlencode 'client_id=legacy-client' \
      --data-urlencode 'username=user@example.com' \
      --data-urlencode 'password=secret'

Expected for an existing authorized legacy client:

    {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "expires_in": ...
    }

This test MUST continue passing after the modernization.

---

# Final Architecture

                              ┌──────────────────────┐
                              │    AUTH SERVICE      │
                              └──────────┬───────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
                 │                                               │
            MODERN FLOW                                     LEGACY FLOW
                 │                                               │
                 ▼                                               ▼
        /oauth/authorize                                  /oauth/token
                 │                                               │
                 ▼                                      grant_type=password
              /login                                             │
                 │                                               │
          email/password                                         │
                 │                                               │
                 ▼                                               │
          browser session                                        │
                 │                                               │
                 ▼                                               │
        authorization code                                       │
                 │                                               │
                 ▼                                               │
           /oauth/token                                          │
                 │                                               │
       authorization_code                                        │
            + PKCE                                               │
                 │                                               │
                 └───────────────────┬───────────────────────────┘
                                     │
                                     ▼
                           access + refresh token


Modern flow:

    PREFERRED

    REQUIRED FOR SPA


Legacy flow:

    DEPRECATED

    BACKWARDS COMPATIBILITY ONLY

    STILL SUPPORTED

---

# Definition of Done

The project is DONE when ALL of the following are true:

## Modern Flow

- SPA uses Authorization Code Flow.
- SPA uses PKCE with S256.
- SPA has no client secret.
- SPA no longer uses password grant.
- SPA does not send user password to `/oauth/token`.
- SPA validates OAuth state.
- Authorization Server provides browser login.
- Authorization Server maintains browser authentication session.
- `/oauth/authorize` can initiate login.
- `/login` authenticates the user but does not issue OAuth tokens.

## Authorization Code Security

- Authorization codes are cryptographically unpredictable.
- Authorization codes are short-lived.
- Authorization codes are single-use.
- Authorization codes are atomically consumed.
- Authorization codes are bound to user_id.
- Authorization codes are bound to client_id.
- Authorization codes are bound to redirect_uri.
- Authorization codes are bound to PKCE challenge.

## PKCE

- S256 works.
- S256 is required for SPA/public clients.
- Missing verifier fails.
- Wrong verifier fails.
- Missing challenge fails for SPA.
- `plain` PKCE is rejected for SPA/public clients.

## Browser Security

- Session cookie is HttpOnly.
- Production session cookie is Secure.
- Session expiration works.
- Logout invalidates browser session.
- Login CSRF protection exists.
- Redirect URIs are strictly validated.

## Legacy Compatibility

- `grant_type=password` STILL WORKS.
- Existing legacy consumers remain compatible.
- Password grant is marked DEPRECATED.
- Password grant is documented as compatibility-only.
- Password grant has regression tests.
- Password grant has usage telemetry.
- New SPA does NOT use password grant.
- No task in this project removes password grant.

## Existing Functionality

- refresh_token flow continues working.
- client_credentials continues working if currently supported.
- existing token format remains compatible unless explicitly documented.
- user-service integration remains compatible.

## Documentation

- README documents modern flow.
- README identifies password grant as deprecated.
- OpenAPI reflects deprecation.
- architecture documentation exists.
- Mermaid sequence diagram exists.
- security audit exists.

---

# Critical Agent Instructions

These instructions override implementation convenience.

## 1. DO NOT REMOVE PASSWORD GRANT

Do NOT delete:

    grant_type=password

Do NOT disable it globally.

Do NOT return:

    unsupported_grant_type

for currently supported legacy password-grant clients.

Password grant remains intentionally supported for backwards compatibility.

---

## 2. DO NOT CONFUSE PASSWORD AUTHENTICATION WITH PASSWORD GRANT

These are different concepts.

Keep:

    /login
        email
        password

This authenticates the user.

Also retain legacy:

    /oauth/token
        grant_type=password

for backwards compatibility.

New SPA uses the first mechanism as part of Authorization Code Flow.

---

## 3. REUSE EXISTING OAUTH IMPLEMENTATION

Inspect existing:

- authorization code implementation
- PKCE implementation
- token issuance
- refresh token implementation
- client validation

before adding new code.

Do NOT create parallel implementations unnecessarily.

---

## 4. DO NOT INTRODUCE SPA CLIENT SECRET

SPA is a public client.

Never solve client authentication by embedding:

    client_secret

inside frontend code.

---

## 5. /login MUST NOT ISSUE TOKENS

Correct:

    /login
        |
        v
    authenticated browser session
        |
        v
    authorization code
        |
        v
    /oauth/token
        |
        v
    tokens

Incorrect:

    /login
        |
        v
    access token

---

## 6. DO NOT USE ACCESS TOKEN AS BROWSER LOGIN SESSION

Browser authentication session and OAuth access token have different purposes.

Keep them separate.

---

## 7. DO NOT LOG SECRETS

Never log:

- password
- session ID
- authorization code
- PKCE verifier
- access token
- refresh token
- client secret

---

## 8. KEEP CHANGES REVIEWABLE

Do not implement the entire migration as one giant refactor.

Follow sprint boundaries.

Prefer small commits.

Preserve existing behavior unless a ticket explicitly changes it.

---

## 9. ADD REGRESSION TESTS BEFORE MODIFYING SHARED CODE

Before modifying shared token issuance/authentication logic, establish tests for:

- password grant
- refresh token
- authorization code
- PKCE

Existing legacy behavior must remain covered.

---

## 10. REPORT AFTER EACH SPRINT

At the end of each sprint provide:

### Changed Files

List files added/modified/deleted.

### Architecture Changes

Explain what changed and why.

### Security Changes

Explain security-sensitive behavior introduced or modified.

### Tests

List tests added and their purpose.

### Compatibility

Explicitly state whether:

    grant_type=password

still passes regression tests.

### Configuration / Migration

List:

- new environment variables
- database/schema changes
- deployment changes
- cookie/domain configuration

### Remaining Work

List incomplete tasks and known risks.

---

# Non-Goal

Removing Resource Owner Password Credentials is explicitly NOT part of this
project.

A future project MAY remove:

    grant_type=password

after all legacy consumers have migrated.

That decision must be made separately.

For this project the final state is:

    Authorization Code + PKCE
        = preferred modern flow

    Password Grant
        = deprecated legacy compatibility flow
