"""
HTTP Response Node

Single Responsibility: Set HTTP status code and body for API workflow responses.

This node is for API workflows only. When placed as the last node, the execute
endpoint returns the configured status and body instead of the default 200/400 envelope.
"""

import json
from typing import Optional, List
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import HttpResponseForm

logger = structlog.get_logger(__name__)


class HttpResponseNode(BlockingNode):
    """
    BlockingNode that outputs a reserved HTTP response shape (status + body).

    The API execution layer detects this shape and returns Response(body, status=status)
    to the client. Use body_source 'from_input' to pass through upstream data, or
    'custom' to define a JSON body (Jinja supported).
    """

    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "http-response"

    @property
    def label(self) -> str:
        """Display name for UI."""
        return "HTTP Response"

    @property
    def description(self) -> str:
        """Node description for documentation."""
        return "Set HTTP status code and response body for API workflows. Use as the last node to control the execute endpoint response."

    @property
    def icon(self) -> str:
        """Icon identifier for UI."""
        return "reply"

    @property
    def supported_workflow_types(self) -> List[str]:
        """HTTP Response only makes sense in API (request-response) workflows."""
        return ['api']

    def get_form(self) -> Optional[BaseForm]:
        """Return the configuration form."""
        return HttpResponseForm()

    @property
    def execution_pool(self) -> PoolType:
        """Use ASYNC pool."""
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Build the reserved output shape: __http_response__, status, body.

        Body comes from upstream data (from_input) or from the form's custom JSON (custom).
        """
        status_code = self.form.cleaned_data.get('status_code', 200)
        body_source = self.form.cleaned_data.get('body_source', 'from_input')

        if body_source == 'from_input':
            body = dict(node_data.data) if node_data.data else {}
        else:
            # custom: use form body_json (may contain Jinja, so use get_field_value)
            raw = self.form.get_field_value('body_json') or ''
            raw = raw.strip() if raw else '{}'
            if not raw:
                body = {}
            else:
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.error(
                        "Invalid JSON in HTTP Response custom body",
                        error=str(e),
                        node_id=self.node_config.id
                    )
                    raise ValueError(f"Invalid JSON in custom body: {e}")

        metadata = dict(node_data.metadata) if isinstance(node_data.metadata, dict) else {}

        return NodeOutput(
            id=node_data.id,
            data={
                '__http_response__': True,
                'status': status_code,
                'body': body,
            },
            metadata=metadata,
        )
