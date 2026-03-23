import asyncio
import runpy

from botocore.exceptions import BotoCoreError
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.api_handler import (
    botocore_error_handler,
    health_check,
    http_exception_handler,
    oauth_exception_handler,
    request_validation_error_handler,
)
from app.exceptions import OAuthException


class TestApiHandler:
    @staticmethod
    def _request() -> Request:
        return Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "path": "/",
                "headers": [],
            }
        )

    def test_successfully_handle_oauth_exception(self):
        request = self._request()
        error = OAuthException(
            "invalid_client",
            error_description="Bad credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

        response = oauth_exception_handler(request, error)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers["www-authenticate"] == "Basic"
        assert (
            response.body
            == b'{"error":"invalid_client","error_description":"Bad credentials"}'
        )

    def test_successfully_handle_http_exception(self):
        request = self._request()

        response = http_exception_handler(
            request,
            HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden"),
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert b'"status":403' in response.body
        assert b'"error":"Forbidden"' in response.body

    def test_successfully_handle_validation_error(self):
        request = self._request()
        error = RequestValidationError(
            [
                {
                    "loc": ("body", "grant_type"),
                    "msg": "Field required",
                    "type": "missing",
                }
            ]
        )

        response = request_validation_error_handler(request, error)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert b'"error":"Validation Error"' in response.body
        assert b'"grant_type"' in response.body

    def test_successfully_handle_botocore_error_in_debug(self, monkeypatch):
        request = self._request()
        monkeypatch.setattr("app.api_handler.settings.debug", True)
        error = BotoCoreError(error_msg="boom")

        response = botocore_error_handler(request, error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            b'"error":"BotoCoreError: An unspecified error occurred"' in response.body
        )

    def test_successfully_handle_botocore_error_without_debug(self, monkeypatch):
        request = self._request()
        monkeypatch.setattr("app.api_handler.settings.debug", False)
        error = BotoCoreError(error_msg="hidden")

        response = botocore_error_handler(request, error)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b'"error":"Internal Server Error"' in response.body

    def test_successfully_return_health_status(self):
        response = asyncio.run(health_check())

        assert response == {"status": "healthy"}

    def test_successfully_execute_main_module(self, mocker):
        mocked_run = mocker.patch("uvicorn.run")

        runpy.run_module("app.api_handler", run_name="__main__")

        mocked_run.assert_called_once_with(
            "app.api_handler:app", host="localhost", port=8080, reload=True
        )
