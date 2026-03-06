# auth-service

Authentication and authorization service built with FastAPI, AWS Lambda, DynamoDB, and Terraform.

The service provides OAuth-style token issuance and revocation endpoints, user registration with scope-based authorization, and production-ready CI checks.

## Table of Contents

- Overview
- Features
- Architecture
- API Endpoints
- RFC 6749 OAuth 2.0 Compliance
- Configuration
- Local Development
- Quality and Testing
- Build and Deployment
- Infrastructure
- Troubleshooting

## Overview

`auth-service` is a stateless API layer designed to run on AWS Lambda behind API Gateway.

Core responsibilities:

- Authenticate users with username/password and issue JWT + refresh tokens
- Refresh access tokens with refresh tokens
- Issue machine-to-machine access tokens using `client_credentials`
- Revoke tokens
- Register users (protected endpoint with scope checks)

## Features

- FastAPI-based HTTP API
- **RFC 6749 OAuth 2.0 compliant** token endpoint (`/oauth/token`)
- **Authorization code flow with PKCE support** (RFC 7636)
- Scope-aware authorization (`users:write`, `users:read`, etc.)
- JWT access token generation with configurable lifetime
- Refresh token persistence and revocation via DynamoDB
- Centralized exception handling with consistent JSON error responses
- Correlation ID middleware for request tracing
- CI pipeline with lint, security scan, tests, coverage, and SonarQube scan
- 98% test coverage with 96 passing tests

## Architecture

High-level flow:

1. Request enters FastAPI app (`app/api_handler.py`)
2. Middleware adds correlation ID and common middleware stack is applied
3. API router delegates to auth endpoints (`app/api/v1/routers/auth_router.py`)
4. Services implement business logic (`app/services/*.py`)
5. Repositories persist/read data from DynamoDB (`app/repositories/*.py`)

Main runtime components:

- API app: `app/api_handler.py`
- Versioned router: `app/api/v1/api.py`
- Auth routes: `app/api/v1/routers/auth_router.py`
- Domain services: `app/services/`
- Persistence repositories: `app/repositories/`
- Models: `app/models/`
- Infrastructure as code: `infrastructure/`

## API Endpoints

Base path: `/api/v1`

### `POST /api/v1/oauth/token`

Consumes `application/x-www-form-urlencoded` body.

Supported `grant_type` values:

- `password`
- `refresh_token`
- `client_credentials`
- `authorization_code`

Response model:

- `access_token`
- `refresh_token` (not returned for `client_credentials`)
- `token_type` (`Bearer`)
- `expires_in`
- `scope`

#### Password grant example

```bash
curl -X POST http://localhost:8080/api/v1/oauth/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "grant_type=password" \
	-d "username=root@squarelabs.hu" \
	-d "password=not_so_secure_password"
```

#### Refresh token grant example

```bash
curl -X POST http://localhost:8080/api/v1/oauth/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "grant_type=refresh_token" \
	-d "refresh_token=<refresh_token>"
```

#### Client credentials grant example

```bash
curl -X POST http://localhost:8080/api/v1/oauth/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-H "Authorization: Basic <base64(client_id:client_secret)>" \
	-d "grant_type=client_credentials" \
	-d "scope=users:read"
```

#### Authorization code grant example

```bash
curl -X POST http://localhost:8080/api/v1/oauth/token \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-d "grant_type=authorization_code" \
	-d "code=<authorization_code>" \
	-d "redirect_uri=https://client.example.com/callback" \
	-d "code_verifier=<pkce_verifier>"
```

### `GET /api/v1/oauth/authorize`

Initiates the authorization code flow. Requires authentication with a valid JWT bearer token.

**Query parameters:**

- `client_id` (required) — Client application identifier
- `redirect_uri` (required) — Callback URL where authorization code will be sent
- `response_type` (required) — Must be `code`
- `scope` (optional) — Space-separated scopes (defaults to user's role-based scopes)
- `state` (optional) — Client state for CSRF protection
- `code_challenge` (optional) — PKCE code challenge (RFC 7636)
- `code_challenge_method` (optional) — `S256` or `plain` (required if code_challenge provided)

**Response:**

Redirects to `redirect_uri` with query parameters:
- `code` — Authorization code (10-minute expiration, one-time use)
- `state` — Echoed state parameter (if provided)

**Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/oauth/authorize?client_id=my-app&redirect_uri=https://client.example.com/callback&response_type=code&scope=users:read&state=xyz123&code_challenge=E9Melhoa2OwkFrlvQYW3jxjfkTRzIxXfsQeuCCqRCw&code_challenge_method=S256" \
	-H "Authorization: Bearer <access_token>" \
	-L
```

**PKCE Flow:**

1. Client generates `code_verifier` (cryptographically random string)
2. Client computes `code_challenge = BASE64URL(SHA256(code_verifier))` for S256 method
3. Client calls `/oauth/authorize` with `code_challenge` and `code_challenge_method=S256`
4. Service returns authorization `code`
5. Client exchanges code at `/oauth/token` with `grant_type=authorization_code` and original `code_verifier`
6. Service validates PKCE and returns tokens

### `POST /api/v1/oauth/revoke`

Revokes the currently authenticated token.

```bash
curl -X POST http://localhost:8080/api/v1/oauth/revoke \
	-H "Content-Type: application/x-www-form-urlencoded" \
	-H "Authorization: Bearer <access_token>" \
	-d "token=<access_token_or_refresh_token>"
```

### `POST /api/v1/register`

Requires bearer token with `users:write` scope.

```bash
curl -X POST http://localhost:8080/api/v1/register \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <access_token_with_users:write>" \
	-d '{
		"email": "newuser@squarelabs.hu",
		"username": "newuser",
		"password": "password123",
		"confirmPassword": "password123",
		"displayName": "New User"
	}'
```

### `GET /health`

Health endpoint:

```json
{"status": "healthy"}
```

## RFC 6749 OAuth 2.0 Compliance

This service is **fully RFC 6749 compliant** with the following implementation details:

### Request Format

- All token requests use `application/x-www-form-urlencoded` body
- Grant types: `password`, `refresh_token`, `client_credentials`, `authorization_code`
- Client authentication for `client_credentials` via HTTP Basic (RFC 7617)
- Authorization code flow with PKCE support (RFC 7636)

### Response Format

Token responses include:

- `access_token` (required)
- `token_type: Bearer` (required)
- `expires_in` (required)
- `scope` (optional, returned when applicable)
- `refresh_token` (only for `password` and `refresh_token` grants)

### Cache Control Headers

All token responses (Section 5.1) include:

- `Cache-Control: no-store` — Prevents token caching
- `Pragma: no-cache` — Fallback for older clients

### Error Handling

OAuth errors follow RFC 6749 error specifications:

- `invalid_request` — Missing or invalid parameters
- `invalid_client` — Client authentication failed (Basic auth)
- `invalid_grant` — User/credential validation failed
- `invalid_scope` — Requested scope not allowed
- `unsupported_grant_type` — Unknown grant type

All errors include optional `error_description` field.

### Client Credentials Grant Security

Basic auth credentials are validated with:

- Strict Base64 decoding (`validate=True`)
- Rejection of malformed or incomplete credentials
- Argon2 hashing for stored client secrets
- Standard `WWW-Authenticate: Basic` challenge on failure

## Configuration

Settings are defined in `app/settings.py` and loaded from environment variables.

Required/important variables:

- `APP_NAME`
- `DEFAULT_TIMEZONE`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `STAGE`
- `JWT_SECRET_SSM_PARAM_NAME` (SSM parameter name that stores the JWT secret)

Optional variables (with defaults):

- `JWT_TOKEN_LIFETIME` (default: `3600`)
- `REFRESH_TOKEN_LIFETIME` (default: `2592000`)
- `DEBUG` (default: `false`)
- `JWT_ISSUER` (default: empty)
- `LOG_LEVEL`
- `POWERTOOLS_*`

Notes:

- `jwt_secret` is fetched from AWS SSM Parameter Store at runtime.
- DynamoDB table names are stage-prefixed, for example:
	- `<stage>-users`
	- `<stage>-tokens`
	- `<stage>-services`
	- `<stage>-authorization_codes`

## Local Development

### Prerequisites

- Python `>= 3.14`
- `uv`
- Docker (for build scripts)
- AWS credentials for integration with AWS resources

### Install dependencies

```bash
make install
```

### Run locally

```bash
uv run uvicorn app.api_handler:app --host localhost --port 8080 --reload
```

### Project layout

```text
app/
	api/
	models/
	repositories/
	security/
	services/
infrastructure/
scripts/
tests/
```

## Quality and Testing

Main commands:

- Format: `make format`
- Lint: `make lint`
- Security scan: `make bandit`
- Type check: `make ty`
- Tests + coverage: `make test`

Run everything locally:

```bash
make all
```

Test stack includes:

- `pytest`
- `pytest-cov`
- `pytest-xdist`
- `moto` for AWS mocking

## Build and Deployment

### Build artifacts

- Lambda package: `scripts/build_api.sh`
- Dependencies layer: `scripts/build_requirements_layer.sh`

These scripts output archives under `dist/`:

- `dist/api.zip`
- `dist/requirements.zip`

### Upload artifacts to S3

- Lambda package upload: `scripts/upload_api.sh`
- Layer upload: `scripts/upload_requirements_layer.sh`

The upload scripts generate environment files in `dist/` with artifact metadata:

- `dist/api.env`
- `dist/requirements.layer.env`

### Terraform

Infrastructure configuration is located in `infrastructure/`.

Typical flow:

```bash
make tflint
cd infrastructure
terraform init
terraform plan
terraform apply
```

## Infrastructure

Terraform provisions:

- Lambda function (`python3.14`) running `app.api_handler.handler`
- API Gateway integration
- DynamoDB tables for users, tokens, and services
- IAM roles/policies
- SSM-based secret integration for JWT secret

`terraform.auto.tfvars` contains environment-specific values like artifact bucket and hashes.

## CI

Workflow: `.github/workflows/ci.yml`

CI triggers:

- `push` (all branches)
- `pull_request` (all branches)
- `workflow_dispatch`

CI stages:

1. Dependency installation (`uv sync --locked`)
2. Bandit security scan
3. Ruff lint and format check
4. Pytest with coverage report
5. Codecov upload
6. SonarQube scan

Concurrency is configured to cancel in-progress runs on the same ref.

## Error Handling

The API uses centralized exception handlers:

- OAuth errors return `{ "error": "...", "error_description": "..." }`
- Validation errors return structured error payload with `errors`
- Other HTTP/internal errors return normalized response shape

## Troubleshooting

### 401 `invalid_client` on `client_credentials`

- Ensure `Authorization: Basic <base64(client_id:client_secret)>` header is valid
- Ensure service credential exists in `<stage>-services`
- Ensure stored secret is Argon2 hash

### 422 validation errors on `/oauth/token`

- Send `application/x-www-form-urlencoded` body
- Include required fields for the selected `grant_type`

### JWT issues

- Verify `JWT_SECRET_SSM_PARAM_NAME` exists in SSM
- Verify Lambda/runtime IAM policy allows `ssm:GetParameter`

### DynamoDB `ResourceNotFoundException`

- Check `STAGE` value and table names
- Ensure Terraform stack has been applied for that stage

## License

See `LICENSE`.
