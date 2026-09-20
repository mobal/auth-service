# External identity ownership

## Decision

External identities belong to the user domain and should be persisted by
`user-service`. `auth-service` owns OAuth authorization codes, browser sessions,
and application tokens; it must not duplicate local-user ownership in those
stores.

The Google identity key is the pair:

```text
issuer + subject
```

The Google email address is profile data and may participate in an explicitly
documented account-linking policy, but it is not an identity key.

## Required user-service model

The user domain needs an external-identity record containing at least:

- `user_id`
- `issuer`
- `subject`
- `email`
- `created_at`
- `updated_at`

Storage must enforce uniqueness for `(issuer, subject)` and provide an
efficient lookup by that pair. The model must allow multiple authentication
methods to reference one local user.

## Required internal APIs

The exact paths should follow user-service conventions. The capabilities
needed by `auth-service` are:

- Find an external identity by issuer and subject.
- Create an external identity for an existing user.
- Atomically create a local user and external identity.
- Atomically link an external identity to an existing user.

Create/link operations must rely on a storage uniqueness constraint or an
equivalent transactional conditional write. An application-level check followed
by an unconditional insert is not sufficient for concurrent first-time logins.

## Account linking

The initial implementation must choose and document the product policy before
linking a previously unknown Google identity to an existing local account.
Explicit linking through an authenticated local session or re-authentication is
the recommended default. Automatic email linking, if approved, must require a
verified email, exactly one eligible local account, and an atomic link; any
ambiguity must fail closed.

## Migration

There is currently no external-identity model in this repository. No migration
should be added to the auth-service token/session tables. The user-service
should introduce its identity storage and backfill only from an authoritative
source, if one exists. Existing password users must remain unchanged until an
explicit linking action occurs.

## Auth-service boundary

`auth-service` will pass validated `(issuer, subject)` claims to the user-service
and receive a local `user_id`. It will then use the existing browser-session,
authorization-code, PKCE, access-token, and refresh-token mechanisms. Google
tokens remain server-side and are never application tokens.
