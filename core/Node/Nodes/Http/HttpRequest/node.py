"""
HTTP Request Node

Single Responsibility: Perform an HTTP request (GET, POST, PUT, PATCH, DELETE, etc.)
with configurable URL, headers, body, and auth. Outputs status, headers, body, and
duration for downstream nodes.
"""

import ast
import json
import time
from typing import Optional, Dict, Any

import httpx
import structlog

from .....log_safe import log_safe_output
from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import HttpRequestForm

logger = structlog.get_logger(__name__)


class HttpRequestNode(BlockingNode):
    """
    BlockingNode that performs a single HTTP request.

    Configuration (via form): method, url, headers, query_params, body,
    timeout_seconds, auth_type (None/Basic/Bearer), and auth credentials.

    Output: data[output_key] = { status, headers, body, duration_ms, error }.
    On request failure, error is set and the workflow continues (no re-raise).
    """

    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "http-request"

    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool for I/O-bound HTTP."""
        return PoolType.ASYNC

    @property
    def label(self) -> str:
        """Human-readable label for UI display."""
        return "HTTP Request"

    @property
    def description(self) -> str:
        """Description of what this node does."""
        return (
            "Makes an HTTP request (GET, POST, PUT, PATCH, DELETE, etc.) "
            "to a URL with configurable headers, body, timeout, and auth."
        )

    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "http"

    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return HttpRequestForm()

    async def setup(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient()
        logger.debug("HTTP Request client initialized", node_id=self.node_config.id)

    async def cleanup(self, node_data: Optional[NodeOutput] = None) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client") and self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP Request client closed", node_id=self.node_config.id)

    def _parse_json_field(self, value: Any, field_name: str) -> Any:
        """Parse a form value as JSON if it's a non-empty string; otherwise return dict/empty."""
        if value is None:
            return {} if field_name != "body" else ""
        if isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            return {} if field_name != "body" else ""
        try:
            parsed = json.loads(value)
            if field_name != "body" and not isinstance(parsed, dict):
                return {}
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {field_name}: {e}") from e

    def _parse_body(self, value: Any) -> Any:
        """
        Parse body: dict/list (sent as JSON) or string (raw).
        When Jinja renders e.g. {{ data.data_transformer }} it can produce a
        Python-repr string (single quotes). We try json.loads then ast.literal_eval
        so the user can send valid JSON; headers (e.g. Content-Type) are always
        defined by the user in the form.
        """
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return ""
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
            if value.startswith("{") or value.startswith("["):
                try:
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, (dict, list)):
                        return parsed
                except (ValueError, SyntaxError):
                    pass
            return value
        return value

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Perform the HTTP request and attach result to node_data.data[output_key].
        On httpx errors, set error in output and do not re-raise.
        """
        # 1. Read from cleaned_data
        url = (self.form.cleaned_data.get("url") or "").strip()
        method = (self.form.cleaned_data.get("method") or "GET").upper()
        timeout_seconds = self.form.cleaned_data.get("timeout_seconds") or 30
        auth_type = (self.form.cleaned_data.get("auth_type") or "").strip().lower()
        auth_username = (self.form.cleaned_data.get("auth_username") or "").strip()
        auth_password = self.form.cleaned_data.get("auth_password") or ""
        auth_bearer_token = (self.form.cleaned_data.get("auth_bearer_token") or "").strip()

        if not url:
            raise ValueError("URL is required")

        # 2. Parse headers, query_params, body (string -> dict or keep string for body)
        try:
            headers_raw = self.form.cleaned_data.get("headers") or ""
            query_params_raw = self.form.cleaned_data.get("query_params") or ""
            body_raw = self.form.cleaned_data.get("body") or ""

            headers = self._parse_json_field(headers_raw, "headers")
            query_params = self._parse_json_field(query_params_raw, "query_params")
            body = self._parse_body(body_raw)
        except ValueError as e:
            raise ValueError(str(e)) from e

        # 3. Build auth
        auth = None
        if auth_type == "basic" and (auth_username or auth_password):
            auth = httpx.BasicAuth(auth_username, auth_password)
        elif auth_type == "bearer" and auth_bearer_token:
            headers = dict(headers) if isinstance(headers, dict) else {}
            headers["Authorization"] = f"Bearer {auth_bearer_token}"

        timeout = float(timeout_seconds) if timeout_seconds else 30.0
        if timeout <= 0:
            timeout = 30.0

        # 4. Build request kwargs
        request_kwargs: Dict[str, Any] = {
            "method": method,
            "url": url,
            "timeout": timeout,
            "auth": auth,
        }
        if headers:
            request_kwargs["headers"] = headers
        if query_params:
            request_kwargs["params"] = query_params

        if method in ("POST", "PUT", "PATCH") and body is not None:
            if isinstance(body, dict):
                request_kwargs["json"] = body
            else:
                request_kwargs["content"] = body if isinstance(body, (bytes, str)) else str(body)

        logger.info(
            "HTTP request",
            node_id=self.node_config.id,
            method=method,
            url=log_safe_output(url),
        )

        start = time.perf_counter()
        result_body: Any = None
        result_headers: Dict[str, str] = {}
        status_code = 0
        error_info: Optional[Dict[str, Any]] = None

        try:
            response = await self._client.request(**request_kwargs)
            status_code = response.status_code
            result_headers = dict(response.headers)
            try:
                result_body = response.json()
            except Exception:
                result_body = response.text

            logger.info(
                "HTTP response",
                node_id=self.node_config.id,
                status=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
        except httpx.HTTPError as e:
            error_info = {"message": str(e), "type": type(e).__name__}
            logger.warning(
                "HTTP request failed",
                node_id=self.node_config.id,
                error=log_safe_output(str(e)),
                type=type(e).__name__,
            )
        except Exception as e:
            error_info = {"message": str(e), "type": type(e).__name__}
            logger.error(
                "HTTP request error",
                node_id=self.node_config.id,
                error=log_safe_output(str(e)),
                exc_info=True,
            )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        output_key = self.get_unique_output_key(node_data, "http_request")
        node_data.data[output_key] = {
            "status": status_code,
            "headers": result_headers,
            "body": result_body,
            "duration_ms": duration_ms,
            "error": error_info,
        }

        return NodeOutput(
            id=node_data.id,
            data=node_data.data,
            metadata={
                "sourceNodeID": self.node_config.id,
                "sourceNodeName": self.node_config.type,
                "operation": "http_request",
            },
        )
