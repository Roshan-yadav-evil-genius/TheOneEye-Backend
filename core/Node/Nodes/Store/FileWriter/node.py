"""
FileWriter Node

Single Responsibility: Write workflow data to files.
"""

import json
import os
from typing import Optional
import aiofiles
import structlog

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import FileWriterForm

logger = structlog.get_logger(__name__)


class FileWriter(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "file-writer"

    def get_form(self) -> Optional[BaseForm]:
        return FileWriterForm()

    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC

    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """
        Write node data to a file.
        
        If 'content' field is provided, uses that value (after Jinja rendering).
        Otherwise, uses node_data.data (current behavior).
        """
        # Get form values using cleaned_data (consistent with other nodes)
        file_path = self.form.cleaned_data.get("file_path")
        mode = self.form.cleaned_data.get("mode", "w")
        content_value = self.form.cleaned_data.get("content", "").strip()

        if not file_path:
            raise ValueError("File path not configured")

        # Enforce bin/FileWritter directory
        file_path = os.path.join("bin", "FileWritter", file_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        # Determine content to write
        if content_value:
            # Use provided content (already Jinja-rendered by populate_form_values)
            content = content_value
            logger.debug("Using content from form field", file=file_path, node_id=self.node_config.id)
        else:
            # Use current behavior: node_data.data
            content = node_data.data
            
            # Serialize if not string
            if not isinstance(content, str):
                try:
                    # If appending, add newline for separation usually, or depends on format. 
                    # For basic writer, just dump.
                    content = json.dumps(content, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.warning("Failed to serialize data to JSON, casting to string", error=str(e))
                    content = str(content)
            logger.debug("Using node_data.data as content", file=file_path, node_id=self.node_config.id)
        
        # Add newline if appending and content doesn't have it?
        # Let's keep it raw for 'w', maybe add newline for 'a' if likely a log/jsonl?
        # User requirement: "take and put nodedata". 
        # I'll append a newline if mode is 'a' to ensure separation.
        if mode == 'a' and not content.endswith('\n'):
             content += '\n'

        try:
            async with aiofiles.open(file_path, mode=mode, encoding='utf-8') as f:
                await f.write(content)
            
            logger.info("Written data to file", file=file_path, mode=mode, used_content_field=bool(content_value), node_id=self.node_config.id)
            
            # Pass through data
            return node_data
            
        except Exception as e:
            logger.error("Failed to write to file", file=file_path, error=str(e), node_id=self.node_config.id)
            raise e

