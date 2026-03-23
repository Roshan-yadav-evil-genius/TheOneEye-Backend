"""
HtmlToMarkdown Node

Single Responsibility: Convert HTML content to markdown and forward the result.
"""

from typing import Any, Optional

import structlog
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import HtmlToMarkdownForm

logger = structlog.get_logger(__name__)


def _markdown_from_result(result: Any) -> str:
    if result is None:
        return ""
    raw = getattr(result, "raw_markdown", None)
    if isinstance(raw, str):
        return raw
    if hasattr(result, "model_dump"):
        dumped = result.model_dump()
        if isinstance(dumped.get("raw_markdown"), str):
            return dumped["raw_markdown"]
    return ""


class HtmlToMarkdown(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "html-to-markdown"

    @property
    def label(self) -> str:
        return "HTML to Markdown"

    @property
    def description(self) -> str:
        return "Convert HTML content to markdown using crawl4ai"

    @property
    def icon(self) -> str:
        return "markdown"

    def get_form(self) -> Optional[BaseForm]:
        return HtmlToMarkdownForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        html = self.form.get_field_value("html_content")
        if not html or not str(html).strip():
            raise ValueError("HTML content is required")

        generator = DefaultMarkdownGenerator()
        result = generator.generate_markdown(str(html))
        markdown_text = _markdown_from_result(result)

        logger.info(
            "HTML to markdown conversion completed",
            node_id=self.node_config.id,
            output_chars=len(markdown_text),
        )

        raw_overwrite = self.form.get_field_value("overwrite")
        overwrite = raw_overwrite not in (False, "false", "off", "0", None, "")

        payload = {"markdown": markdown_text}
        metadata = {
            "sourceNodeID": self.node_config.id,
            "sourceNodeName": self.node_config.type,
            "operation": "html_to_markdown",
        }

        if overwrite:
            return NodeOutput(id=node_data.id, data=payload, metadata=metadata)

        output_key = self.get_unique_output_key(node_data, "html_to_markdown")
        existing = dict(node_data.data) if node_data.data else {}
        output_data = {**existing, output_key: payload}
        return NodeOutput(id=node_data.id, data=output_data, metadata=metadata)
