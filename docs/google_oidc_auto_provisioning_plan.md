# Google Login / OIDC Integration Plan

## 1. Objective

Add Google authentication to `mobal/auth-service` using OpenID Connect.

Repository:

    mobal/auth-service

Google must be treated as an external Identity Provider (IdP).

The existing Authorization Server remains responsible for issuing the
application's own:

    authorization_code
    access_token
    refresh_token

Google tokens MUST NOT replace the application's own access/refresh tokens.

The user should be able to authenticate using either:

    email + password

or:

    Google

Both authentication methods must eventually result in the SAME local user
identity and the SAME existing OAuth authorization flow.

## 1.1 Current Implementation Status — 2026-09-23

For the current milestone, the scope is limited to implementing the Google
OIDC flow in `auth-service`. User-service identity storage, linking, and
provisioning are intentionally deferred to a later milestone.

The auth-service OIDC browser round trip and local OAuth continuation are
implemented and covered by unit and integration tests using mocked Google
endpoints.

### Implemented

- Google login button on the hosted login page.
- Authorization-code redirect and callback endpoints.
- Server-side `state` and `nonce` generation, persistence, expiry, and
  one-time consumption.
- Google discovery-document lookup with issuer validation and circuit
  breaking.
- Authorization-code exchange and ID-token signature/claim validation for
  issuer, audience, expiration, nonce, and verified email.
- Local browser-session creation and continuation of the pending local OAuth
  authorization request.
- Issuance of the local authorization code; Google tokens are not returned to
  the browser.

### Current user resolution behavior

`AuthService.authenticate_google_user()` resolves an existing local user by
verified Google email. This path is controlled by
`google_dev_email_login_enabled` and is disabled by default. It is sufficient
for the current auth-service-only milestone. It will be replaced later when
user-service adds external-identity ownership keyed by `(issuer, subject)`.

### Deferred to the user-service milestone

- External-identity ownership and lookup APIs.
- `(issuer, subject)` identity resolution.
- Account-linking policy and atomic link/create operations.
- New-user provisioning.
- Replacement of the development email lookup and its feature flag.
- End-to-end tests against the future user-service identity contract.

The current implementation satisfies the auth-service portion of Sprint 2 and
Sprint 4. Sprints 1 and 3 describe deferred user-service work and are not
required for this milestone.

---

# 2. High-Level Architecture

Target flow:

    SPA
     |
     v
    GET /oauth/authorize
     |
     | no auth session
     v
    Auth Service Login Page
     |
     +--------------------------+
     |                          |
     | Email + Password         |
     |                          |
     | [ Continue with Google ] |
     |                          |
     +--------------------------+
                 |
                 | Google selected
                 v
        Auth Service
        /login/google
                 |
                 | redirect
                 v
              Google
                 |
                 | user authenticates
                 v
              Google
                 |
                 | authorization code
                 v
        Auth Service
        /login/google/callback
                 |
                 | exchange Google code
                 | validate ID token
                 v
        Resolve local identity
                 |
          +------+------+
          |             |
      existing       new user
          |             |
          +------+------+
                 |
                 v
        local user_id resolved
                 |
                 v
        create Auth Service
        browser session
                 |
                 v
        resume original
        /oauth/authorize
                 |
                 v
        local authorization code
                 |
                 v
              SPA
                 |
                 | code + PKCE verifier
                 v
        POST /oauth/token
                 |
                 v
        local access_token
        local refresh_token

---

# 3. Standards

Google authentication must use:

- OAuth 2.0 Authorization Code Flow
- OpenID Connect 1.0

Relevant specifications:

- OpenID Connect Core 1.0
- OAuth 2.0 — RFC 6749
- OAuth 2.0 Security Best Current Practice — RFC 9700

Google-specific implementation must follow Google's current OpenID Connect
documentation.

Do NOT invent:

    grant_type=google

Do NOT send Google ID tokens to the existing password grant.

Do NOT use Google email address as the permanent external identity identifier.

---

# 4. Identity Model

## Core Rule

External identities MUST be identified using:

    issuer + subject

For Google this will normally correspond to:

    iss
    sub

from the validated Google ID token.

Example:

    issuer:
        https://accounts.google.com

    subject:
        123456789012345678901

The `sub` claim is the external identity identifier.

Email MUST NOT be used as the primary Google identity key.

---

# 5. Recommended Data Model

External identities should belong to the user domain.

Preferred conceptual model:

    users
    -----
    id
    email
    name
    ...

    user_identities
    ---------------
    id
    user_id
    issuer
    subject
    email
    created_at
    updated_at

Required uniqueness:

    UNIQUE(issuer, subject)

Depending on the current architecture, this data SHOULD live in `user-service`
rather than the auth-service token/session store.

The agent MUST inspect the existing user-service integration before deciding
where this model belongs.

Do not duplicate user ownership into auth-service unnecessarily.

---

# 6. Identity Resolution Algorithm

After validating Google's ID token:

    claims.iss
    claims.sub
    claims.email
    claims.email_verified

resolve the local user.

Conceptually:

    identity = findIdentity(
        issuer = claims.iss,
        subject = claims.sub
    )

    if identity exists:

        return identity.user


    else:

        evaluate account-linking policy

The external identity MUST always be persisted using:

    issuer + subject

Never persist Google identity using email alone.

---

# EPIC 1 — Audit Existing User Identity Architecture

## Goal

Understand how users are currently represented and where external identities
should live.

---

## TASK 1.1 — Inspect User Service Integration

Inspect:

- UserServiceClient
- user lookup methods
- user creation methods
- email uniqueness behavior
- password ownership
- user identifiers
- authentication APIs
- user-service database/model if available
- existing external identity concepts if any

Determine:

    where should external identities live?

Preferred answer:

    user-service

unless the existing architecture provides a strong reason otherwise.

### Deliverable

Create:

    docs/external-identities.md

Document:

- user ownership
- identity ownership
- lookup API requirements
- create/link API requirements
- uniqueness requirements
- migration requirements

---

# EPIC 2 — External Identity Model

## Goal

Represent Google identity independently from the user's email address.

---

## TASK 2.1 — Add External Identity Model

Introduce an external identity model.

Minimum fields:

    user_id
    issuer
    subject
    email
    created_at
    updated_at

Required constraint:

    UNIQUE(issuer, subject)

Optional metadata may include:

    provider
    display_name
    picture_url

but these MUST NOT become authentication keys.

Example:

    {
      "user_id": "local-user-id",
      "issuer": "https://accounts.google.com",
      "subject": "123456789012345678901",
      "email": "user@gmail.com"
    }

### Acceptance Criteria

- `(issuer, subject)` uniquely identifies an external identity.
- Multiple authentication methods can belong to one local user.
- Email is not the external primary key.
- External identity can be looked up efficiently.
- Duplicate `(issuer, subject)` cannot be created.

---

## TASK 2.2 — Add User-Service Identity APIs

If identities belong to user-service, add internal APIs equivalent to:

    GET external identity by issuer + subject

    CREATE external identity for user

    CREATE user + external identity

Exact endpoint naming should follow existing project conventions.

Operations that create/link identity must handle concurrency safely.

### Acceptance Criteria

Two simultaneous first-time Google logins for the same:

    issuer + subject

must NOT create two local identities/users.

Uniqueness must ultimately be enforced by storage, not only application-level
"check then insert" logic.

---

# EPIC 3 — Google OIDC Configuration

## Goal

Configure Google as an external OIDC provider.

---

## TASK 3.1 — Add Configuration

Add configuration for:

    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET

and any necessary callback/base URL configuration following existing project
configuration conventions.

Never commit secrets.

Production secrets must come from the project's existing secret-management
mechanism.

Configure callback URI such as:

    https://auth.example.com/login/google/callback

The exact route may be adapted to existing routing conventions.

---

## TASK 3.2 — Provider Metadata

Prefer OpenID Connect discovery instead of hardcoding provider endpoints where
supported by the selected library.

The implementation needs the equivalent of:

    authorization_endpoint
    token_endpoint
    jwks_uri
    issuer

Validate discovered issuer.

Cache metadata/JWKS appropriately.

Do not fetch discovery/JWKS unnecessarily on every request if the selected
library already provides safe caching.

---

# EPIC 4 — Start Google Login

## TASK 4.1 — Add Google Login Button

Add to the Authorization Server login page:

    Continue with Google

The button must initiate Google authentication through the auth-service.

It must NOT directly implement application OAuth token issuance.

Example route:

    GET /login/google?request_id=...

The original pending authorization request MUST survive the Google round trip.

---

## TASK 4.2 — Generate OIDC Security Parameters

Before redirecting to Google, generate appropriate correlation values.

At minimum:

    state
    nonce

Store server-side correlation data containing:

    state
    nonce
    pending_authorization_request_id
    created_at
    expires_at

Use opaque, cryptographically unpredictable values.

Do NOT trust these values solely because the browser sends them back.

---

## TASK 4.3 — Redirect to Google Authorization Endpoint

Redirect browser to Google's authorization endpoint.

Request appropriate OpenID Connect scope:

    openid
    email
    profile

Request only scopes actually needed.

Conceptual request:

    response_type=code
    client_id=<google-client-id>
    redirect_uri=<auth-service-google-callback>
    scope=openid email profile
    state=<random>
    nonce=<random>

Do not request unrelated Google API scopes.

### Acceptance Criteria

- state is unpredictable.
- nonce is unpredictable.
- state expires.
- nonce expires.
- pending local authorization request is preserved.
- redirect_uri is fixed/configured.
- requested scopes are minimal.

---

# EPIC 5 — Google Callback

## TASK 5.1 — Implement Callback Endpoint

Implement:

    GET /login/google/callback

Handle:

    code
    state
    error

First validate the returned state.

If state is invalid:

    STOP

Do not exchange the authorization code.

---

## TASK 5.2 — Exchange Google Authorization Code

Exchange the Google authorization code at Google's token endpoint.

The exchange occurs server-to-server from auth-service.

Google credentials must remain server-side.

Expected response includes an:

    id_token

Potentially also:

    access_token

The Google access token is NOT the application's access token.

Do not expose Google tokens to the SPA unless a separate explicit feature
requires Google API access.

---

# EPIC 6 — Validate Google ID Token

## Goal

Never trust decoded JWT claims without cryptographic and semantic validation.

---

## TASK 6.1 — Validate Signature

Validate Google ID token signature using Google's published signing keys.

Use a maintained OIDC/JWT library.

Do NOT manually implement JWT cryptography.

---

## TASK 6.2 — Validate Claims

Validate at minimum as required by the selected OIDC flow/library:

    iss
    aud
    exp
    nonce

Also correctly handle relevant temporal claims.

`aud` must identify this Google OAuth client.

`nonce` must match the nonce created when login started.

Do not simply:

    base64 decode JWT
        ->
    trust payload

### Acceptance Criteria

Reject:

- invalid signature
- unexpected issuer
- wrong audience
- expired token
- incorrect nonce
- malformed token

---

# EPIC 7 — Local Identity Resolution

## Goal

Map the validated Google identity to exactly one local user.

---

## TASK 7.1 — Existing Google Identity

First lookup:

    issuer + subject

Example:

    issuer = claims.iss
    subject = claims.sub

If found:

    local_user = identity.user

Do NOT perform email-based rematching for an already linked external identity.

This is the normal login path after the first successful link.

---

## TASK 7.2 — First-Time Google Login With No Existing User

If:

    issuer + subject

does not exist and there is no matching local account according to the selected
account-linking policy:

Create:

    local user
        +
    external identity

The operation should be transactional/atomic where the architecture permits.

Store:

    issuer
    subject

and useful profile metadata where appropriate.

Do not make mutable Google profile data authoritative for unrelated local user
fields without an explicit policy.

---

# EPIC 8 — Existing Account Linking

## Goal

Safely handle:

    local user already exists
        +
    first Google login

This is security-sensitive.

---

## TASK 8.1 — Define Account-Linking Policy

Do NOT blindly implement:

    if local_user.email == google.email:
        merge()

without explicitly evaluating the security consequences.

At minimum inspect:

    email
    email_verified
    existing authentication methods
    existing user-service email verification state
    possibility of account takeover
    organization/domain-specific requirements

The safest generic design is explicit linking from an already authenticated
local account.

If automatic email-based linking is desired for this product, it MUST be an
explicit documented product/security decision.

---

## TASK 8.2 — Verified Email Handling

If email is used during account discovery/linking, require the provider's email
verification status according to the selected linking policy.

Do not automatically trust an unverified email claim.

Conceptually:

    if email linking is enabled:

        require:
            claims.email exists
            claims.email_verified == true

But:

    email_verified == true

alone does NOT mean:

    automatically merge every account with this email

The final behavior must follow the documented linking policy.

---

## TASK 8.3 — Recommended Safe Linking Flow

Preferred flow for an existing local account:

    Google login
        |
        v
    external identity not found
        |
        v
    local account with same email exists
        |
        v
    require proof of ownership of existing local account
        |
        v
    link Google identity
        |
        v
    continue login

Possible proof:

    existing authenticated session

or:

    re-authentication using existing local authentication mechanism

Do not ask for the user's existing password if the account does not have a
password authentication method.

---

## TASK 8.4 — Optional Automatic Linking Policy

If the product explicitly chooses automatic linking by verified email, implement
it behind a clearly named policy/configuration decision.

Example conceptual configuration:

    EXTERNAL_IDENTITY_AUTO_LINK_VERIFIED_EMAIL=true

Default should be selected deliberately, not accidentally.

If enabled:

    external identity not found
        |
        v
    email_verified == true
        |
        v
    exactly one eligible local user with same normalized email
        |
        v
    atomically link external identity
        |
        v
    login

If anything is ambiguous:

    DO NOT LINK AUTOMATICALLY

### Acceptance Criteria

- Duplicate identities cannot be created.
- Ambiguous matches fail safely.
- Unverified email cannot trigger automatic linking.
- Linking decision is documented.
- Existing external identity always wins over later email comparison.

---

# EPIC 9 — Complete Local Authorization Flow

## Goal

Google authentication must feed back into the same local authorization process
as password authentication.

After Google identity resolves to:

    local_user_id

create/update the normal Authorization Server browser session.

Then resume the pending local authorization request.

Do NOT return Google tokens to the SPA.

---

## TASK 9.1 — Create Local Browser Session

After successful Google authentication:

    Google identity
        |
        v
    local user_id
        |
        v
    auth-service browser session

Use the SAME session mechanism used by email/password login.

Do not create a separate "Google session" architecture.

---

## TASK 9.2 — Resume Pending Authorization Request

After session creation:

    pending request
        |
        v
    /oauth/authorize
        |
        v
    local authorization code
        |
        v
    SPA callback

The SPA should not need to know whether authentication occurred through:

    password

or:

    Google

From the SPA's OAuth perspective both produce:

    local authorization code

---

# EPIC 10 — Logout Semantics

## TASK 10.1 — Local Logout

Normal application logout should terminate the local Authorization Server
session.

It does NOT necessarily need to log the user out of their Google account.

Document this behavior explicitly.

Do not redirect to arbitrary logout URLs.

---

# EPIC 11 — Error Handling

## TASK 11.1 — Google Authorization Errors

Handle provider errors including:

    access_denied

For example, if user cancels Google login:

    return to local login page

with a generic message.

Do not expose raw provider internals unnecessarily.

---

## TASK 11.2 — Identity Resolution Errors

Handle safely:

- missing subject
- missing required claims
- duplicate identity conflict
- ambiguous local email match
- user-service unavailable
- user creation failure
- identity linking failure

Never silently create a second account after a known linking conflict.

---

# EPIC 12 — Security Logging and Telemetry

## TASK 12.1 — Authentication Events

Record security-relevant events such as:

    google_login_started
    google_login_succeeded
    google_login_failed
    external_identity_created
    external_identity_linked
    external_identity_conflict

Include safe identifiers where appropriate.

Do NOT log:

    Google authorization code
    Google access token
    Google ID token
    local access token
    local refresh token
    password
    session ID
    OAuth state
    OIDC nonce

---

# EPIC 13 — Automated Tests

## TASK 13.1 — Existing Identity Login

Test:

    valid Google response
        |
        v
    known issuer + subject
        |
        v
    existing local user
        |
        v
    local session
        |
        v
    local authorization code

No new user is created.

---

## TASK 13.2 — New User Login

Test:

    valid Google response
        |
        v
    unknown issuer + subject
        |
        v
    no matching local account
        |
        v
    create local user
        |
        v
    create external identity
        |
        v
    login succeeds

---

## TASK 13.3 — Account Linking

Test according to selected linking policy.

At minimum:

    known email
    unknown Google subject
    verified email

Verify the selected policy is applied.

Also test:

    email_verified=false

must NOT trigger automatic email linking.

---

## TASK 13.4 — Invalid OIDC Responses

Test rejection of:

    invalid state
    invalid nonce
    invalid signature
    wrong issuer
    wrong audience
    expired ID token
    malformed ID token

No local session should be created.

---

## TASK 13.5 — Concurrency

Simulate two first-time login requests for the same:

    issuer + subject

The result MUST be:

    one external identity
    one associated local user

not duplicate users.

---

# EPIC 14 — Login UI Update

## TASK 14.1 — Add Google Button

Update the FastAPI/Jinja login page.

Conceptually:

    ┌─────────────────────────────┐
    │                             │
    │        Welcome back         │
    │                             │
    │ Email                       │
    │ [_______________________]   │
    │                             │
    │ Password                    │
    │ [_______________________]   │
    │                             │
    │ [        Sign in        ]   │
    │                             │
    │ --------- or ----------     │
    │                             │
    │ [  Continue with Google ]   │
    │                             │
    └─────────────────────────────┘

Google button should preserve the current pending authorization request.

Do not implement Google authentication directly in frontend JavaScript if the
server-side OIDC flow can handle it.

---

# SPRINT 1 — Identity Foundation

## Scope

- TASK 1.1 — User architecture audit
- TASK 2.1 — External identity model
- TASK 2.2 — User-service identity APIs
- TASK 3.1 — Google configuration
- TASK 3.2 — Provider metadata

## Deliverable

The system can represent:

    local user
        <->
    external Google identity

using:

    issuer + subject

No Google login needs to be exposed to users yet.

---

# SPRINT 2 — Google OIDC Flow

## Scope

- TASK 4.1 — Google login button
- TASK 4.2 — state + nonce
- TASK 4.3 — Google authorization redirect
- TASK 5.1 — callback
- TASK 5.2 — authorization-code exchange
- TASK 6.1 — signature validation
- TASK 6.2 — claims validation

## Deliverable

Auth-service can securely authenticate a Google identity.

No unsafe automatic account merging should be introduced implicitly.

---

# SPRINT 3 — User Resolution and Linking

## Scope

- TASK 7.1 — Existing identity
- TASK 7.2 — New user
- TASK 8.1 — Linking policy
- TASK 8.2 — Verified email handling
- TASK 8.3 — Safe linking
- TASK 8.4 — Optional automatic linking

## Deliverable

Google identity reliably resolves to exactly one local user.

Document the selected account-linking policy.

---

# SPRINT 4 — Authorization Integration

## Scope

- TASK 9.1 — Local browser session
- TASK 9.2 — Resume authorization
- TASK 10.1 — Logout semantics
- TASK 11.1 — Provider errors
- TASK 11.2 — Identity errors
- TASK 12.1 — Security telemetry
- TASK 14.1 — Final login UI

## Deliverable

The complete browser flow works:

    SPA
        |
        v
    /oauth/authorize
        |
        v
    login page
        |
        v
    Continue with Google
        |
        v
    Google
        |
        v
    auth-service callback
        |
        v
    local user
        |
        v
    local auth session
        |
        v
    local authorization code
        |
        v
    SPA
        |
        v
    local /oauth/token
        |
        v
    local tokens

---

# SPRINT 5 — Security and Regression Testing

## Scope

- TASK 13.1 — Existing identity
- TASK 13.2 — New user
- TASK 13.3 — Account linking
- TASK 13.4 — Invalid OIDC responses
- TASK 13.5 — Concurrency
- regression tests for password login
- regression tests for legacy password grant
- regression tests for Authorization Code + PKCE
- documentation

## Deliverable

Google authentication is production-ready without breaking existing
authentication mechanisms.

---

# Complete Sequence Diagram

    sequenceDiagram
        autonumber

        actor User
        participant SPA
        participant Auth as Auth Service
        participant Google
        participant Users as User Service

        SPA->>SPA: Generate PKCE verifier/challenge
        SPA->>SPA: Generate OAuth state

        SPA->>Auth: GET /oauth/authorize

        Auth-->>User: Render login page

        User->>Auth: Continue with Google

        Auth->>Auth: Generate Google state + nonce
        Auth->>Auth: Store pending authorization context

        Auth-->>User: Redirect to Google

        User->>Google: Authenticate

        Google-->>Auth: callback?code=...&state=...

        Auth->>Auth: Validate state

        Auth->>Google: Exchange Google authorization code
        Google-->>Auth: ID token

        Auth->>Auth: Validate signature
        Auth->>Auth: Validate iss
        Auth->>Auth: Validate aud
        Auth->>Auth: Validate exp
        Auth->>Auth: Validate nonce

        Auth->>Users: Find identity by issuer + subject

        alt Existing external identity
            Users-->>Auth: Existing local user
        else Unknown external identity
            Auth->>Users: Resolve/create/link local user
            Users-->>Auth: Local user
        end

        Auth->>Auth: Create local browser session

        Auth->>Auth: Resume pending OAuth authorization

        Auth->>Auth: Create local authorization code

        Auth-->>SPA: 302 callback?code=LOCAL_CODE&state=LOCAL_STATE

        SPA->>SPA: Validate local OAuth state

        SPA->>Auth: POST /oauth/token<br/>LOCAL_CODE + PKCE verifier

        Auth->>Auth: Validate PKCE
        Auth->>Auth: Consume local authorization code

        Auth-->>SPA: Local access_token + refresh_token

---

# Two Separate OAuth/OIDC Flows

It is important not to confuse the two authorization codes.

There are TWO independent code exchanges.

## External Google OIDC Flow

    Auth Service
        |
        v
    Google
        |
        v
    GOOGLE_AUTHORIZATION_CODE
        |
        v
    Auth Service
        |
        v
    Google ID Token

Purpose:

    authenticate external Google identity

The SPA should not handle this Google authorization code in the recommended
server-side architecture.

---

## Local OAuth Flow

    SPA
        |
        v
    Auth Service
        |
        v
    LOCAL_AUTHORIZATION_CODE
        |
        v
    SPA
        |
        + PKCE verifier
        |
        v
    Auth Service
        |
        v
    LOCAL ACCESS/REFRESH TOKENS

Purpose:

    authorize the SPA against our own system

These flows MUST remain conceptually and technically separate.

---

# Manual Acceptance Flow

## 1. Start Local Authorization

Browser navigates to:

    GET /oauth/authorize
        ?response_type=code
        &client_id=my-spa
        &redirect_uri=https://app.example.com/callback
        &code_challenge=...
        &code_challenge_method=S256
        &state=LOCAL_STATE

Expected:

    local login page

---

## 2. Select Google

User clicks:

    Continue with Google

Expected:

    browser redirects to Google

The local pending authorization request remains stored server-side.

---

## 3. Authenticate With Google

User authenticates at Google.

Google redirects to:

    /login/google/callback
        ?code=GOOGLE_CODE
        &state=GOOGLE_STATE

---

## 4. Validate Google Response

Auth-service must:

    validate GOOGLE_STATE
        |
        v
    exchange GOOGLE_CODE
        |
        v
    validate Google ID token
        |
        v
    resolve issuer + subject
        |
        v
    resolve local user

---

## 5. Resume Local Authorization

Auth-service creates local browser session.

Then:

    pending local authorization
        |
        v
    LOCAL_AUTHORIZATION_CODE

Browser redirects to:

    https://app.example.com/callback
        ?code=LOCAL_AUTHORIZATION_CODE
        &state=LOCAL_STATE

---

## 6. SPA Exchanges Local Code

SPA sends:

    POST /oauth/token

    grant_type=authorization_code
    client_id=my-spa
    code=LOCAL_AUTHORIZATION_CODE
    redirect_uri=https://app.example.com/callback
    code_verifier=<LOCAL_PKCE_VERIFIER>

Expected:

    {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "expires_in": ...
    }

The tokens are issued by:

    mobal/auth-service

NOT Google.

---

# Definition of Done

The following checklist describes the complete target architecture. For the
current auth-service-only milestone, the OIDC, local authorization, UI, and
security sections are in scope. The Identity and account-linking requirements
that depend on user-service are explicitly deferred and are not blockers for
this milestone.

Google Login is DONE when all of the following are true.

## OIDC

- Google is integrated using OpenID Connect.
- Authorization Code flow is used.
- Google provider configuration is not hardcoded unnecessarily.
- Google client secret is stored securely.
- state is generated and validated.
- nonce is generated and validated.
- ID token signature is validated.
- issuer is validated.
- audience is validated.
- expiration is validated.
- nonce is validated.

## Identity

- Google identity uses issuer + subject.
- Email is not the external identity primary key.
- External identity has a unique issuer + subject constraint.
- Existing identity resolves to existing user.
- New identity can create a local user.
- Account-linking policy is explicitly documented.
- Unverified email cannot trigger automatic email linking.
- Concurrent first login cannot create duplicate identities.

## Local Authorization

- Google authentication creates the normal local browser auth session.
- Google authentication resumes the existing local authorization request.
- SPA receives a LOCAL authorization code.
- SPA exchanges local code using PKCE.
- SPA receives LOCAL access/refresh tokens.
- Google tokens are not used as application access tokens.

## Compatibility

- Existing email/password login continues working.
- Existing Authorization Code + PKCE continues working.
- Legacy `grant_type=password` continues working.
- Google login does not require changing legacy clients.
- Existing refresh-token behavior remains compatible.

## UI

- Login page contains email/password authentication.
- Login page contains Continue with Google.
- Google round trip preserves the pending local authorization request.
- Authentication errors are presented safely.

## Security

- Passwords are never logged.
- Google authorization codes are never logged.
- Google access tokens are never logged.
- Google ID tokens are never logged.
- Local authorization codes are never logged.
- Local access/refresh tokens are never logged.
- OAuth state values are not logged.
- OIDC nonce values are not logged.
- Session identifiers are not logged.

---

# Critical Agent Instructions

## 1. DO NOT IMPLEMENT `grant_type=google`

Google is an external OpenID Connect Identity Provider.

It is NOT a local OAuth grant type.

---

## 2. DO NOT USE EMAIL AS GOOGLE IDENTITY

Incorrect:

    google identity = email

Correct:

    google identity = issuer + subject

Email may participate in account-linking policy, but it is not the stable
external identity key.

---

## 3. DO NOT TRUST AN ID TOKEN JUST BECAUSE IT DECODES

JWT decoding is not validation.

Validate:

    signature
    issuer
    audience
    expiration
    nonce

using a maintained OIDC/JWT library.

---

## 4. DO NOT SEND GOOGLE TOKENS TO THE SPA

Unless a future feature explicitly requires direct Google API access, keep
Google provider tokens inside auth-service.

The SPA receives tokens issued by our own Authorization Server.

---

## 5. DO NOT CREATE A SECOND AUTH SESSION SYSTEM

Password login and Google login must produce the same local browser session
type.

Correct:

    password ----\
                  -> local user -> local auth session
    Google ------/

---

## 6. DO NOT BLINDLY MERGE BY EMAIL

Before implementing automatic linking:

- inspect existing email verification
- inspect user-service behavior
- document policy
- account for account-takeover risk

Prefer explicit linking when security requirements are unclear.

---

## 7. DO NOT BREAK LEGACY PASSWORD GRANT

The following remains supported:

    grant_type=password

It is deprecated but intentionally retained for backwards compatibility.

Google integration must not modify this compatibility guarantee.

---

## 8. REUSE EXISTING COMPONENTS

Reuse existing:

- UserServiceClient
- authorization-code infrastructure
- PKCE infrastructure
- browser auth session
- token service
- refresh-token implementation
- client validation

when correct.

Do not build parallel versions unnecessarily.

---

## 9. KEEP EXTERNAL AND LOCAL CODES SEPARATE

Never confuse:

    GOOGLE_AUTHORIZATION_CODE

with:

    LOCAL_AUTHORIZATION_CODE

They belong to different OAuth/OIDC transactions and have different purposes.

---

## 10. REPORT AFTER EACH SPRINT

After every sprint provide:

### Changed Files

All added/modified/deleted files.

### Architecture Changes

What changed and why.

### Security Changes

Security-sensitive decisions and implementation details.

### Identity Changes

Any changes to:

    users
    external identities
    user-service APIs

### Configuration

New environment variables and secret requirements.

### Tests

Tests added and their purpose.

### Compatibility

Explicitly confirm:

    password login
    Authorization Code + PKCE
    refresh_token
    legacy grant_type=password

remain functional where applicable.

### Remaining Risks

Document unresolved security or account-linking questions.

---

# Non-Goals

This project does NOT:

- remove password authentication
- remove `grant_type=password`
- replace local access tokens with Google access tokens
- expose Google tokens to the SPA
- implement Google API access
- implement Google Drive/Gmail/etc. scopes
- implement arbitrary social-provider abstraction unless naturally justified
- automatically merge accounts by email without an explicit linking policy

The final authentication architecture is:

    Email/Password ----\
                        \
                         -> Local User
                        /       |
    Google OIDC -------/        v
                         Local Auth Session
                                |
                                v
                       Authorization Code
                                +
                              PKCE
                                |
                                v
                       Local Access Token
                       Local Refresh Token
