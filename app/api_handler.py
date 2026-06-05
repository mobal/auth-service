from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.middleware.exceptions import ExceptionMiddleware

from app import settings
from app.exceptions import OAuthException
from app.middlewares import CorrelationIdMiddleware
from app.models.response.error import ErrorResponse, ValidationErrorResponse
from app.routers.oauth.auth_router import router as auth_router

logger = Logger()

app = FastAPI(
    debug=settings.debug if settings.stage != "prod" else False,
    title="AuthApp",
    version="1.0.0",
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware)
app.add_middleware(ExceptionMiddleware, handlers=app.exception_handlers)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.include_router(auth_router, tags=["auth"])

handler = Mangum(app)
handler = logger.inject_lambda_context(handler, clear_state=True, log_event=True)


@app.exception_handler(OAuthException)
def oauth_exception_handler(request: Request, error: OAuthException) -> JSONResponse:
    logger.warning(
        "OAuth exception handled",
        extra={"path": request.url.path, "method": request.method},
    )
    logger.exception(error)
    content: dict = {"error": error.oauth_error}
    if error.oauth_error_description:
        content["error_description"] = error.oauth_error_description
    return JSONResponse(
        content=content,
        status_code=error.status_code,
        headers=dict(error.headers) if error.headers else {},
    )


@app.exception_handler(BotoCoreError)
@app.exception_handler(Exception)
def botocore_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception reached global exception handler",
        extra={"path": request.url.path, "method": request.method},
    )
    logger.exception(
        "Unhandled exception",
        extra={
            "exception_type": type(error).__name__,
            "exception_message": str(error),
            "exception_repr": repr(error),
            "exception_cause": repr(error.__cause__) if error.__cause__ else None,
            "exception_context": (
                repr(error.__context__) if error.__context__ else None
            ),
            "path": request.url.path,
            "method": request.method,
        },
    )
    if settings.debug:
        error_message = (
            f"{type(error).__name__}: {str(error) or repr(error)}"
            if str(error)
            else repr(error)
        )
    else:
        error_message = "Internal Server Error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        content=ErrorResponse(status=status_code, error=error_message).model_dump(
            by_alias=True
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception handled",
        extra={"status_code": error.status_code, "path": request.url.path},
    )
    logger.exception(error)

    return JSONResponse(
        content=ErrorResponse(status=error.status_code, error=error.detail).model_dump(
            by_alias=True
        ),
        status_code=error.status_code,
        headers=dict(error.headers) if error.headers else None,
    )


@app.exception_handler(RequestValidationError)
def request_validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "Request validation error handled",
        extra={"path": request.url.path, "method": request.method},
    )
    logger.exception(error)
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    return JSONResponse(
        content=ValidationErrorResponse(
            status=status_code,
            error="Validation Error",
            errors=jsonable_encoder(error.errors()),
        ).model_dump(by_alias=True),
        status_code=status_code,
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    logger.debug("Health check endpoint called")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api_handler:app", host="localhost", port=8080, reload=True)
