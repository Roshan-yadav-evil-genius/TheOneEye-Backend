import structlog
from typing import Optional, Dict, Type
import pkgutil
import importlib
import inspect
from Node.Core.Node.Core.BaseNode import BaseNode, ProducerNode, BlockingNode, NonBlockingNode, ConditionalNode
from Node.Core.Node.Core.Data import NodeConfig
from .flow_utils import node_type

logger = structlog.get_logger(__name__)


class NodeRegistry:
    """
    Registry class responsible for discovering and creating node instances.
    """

    _node_registry: Optional[Dict[str, Type[BaseNode]]] = None
    _abstract_base_classes = {BaseNode, ProducerNode, BlockingNode, NonBlockingNode, ConditionalNode}

    @classmethod
    def _discover_node_classes(cls) -> Dict[str, Type[BaseNode]]:
        import Node.Nodes as Nodes
        discovered_classes = []

        def walk_packages(path, prefix):
            for importer, modname, ispkg in pkgutil.iter_modules(path, prefix):
                if ispkg:
                    try:
                        subpackage = importlib.import_module(modname)
                        if hasattr(subpackage, "__path__"):
                            walk_packages(subpackage.__path__, modname + ".")
                    except Exception as e:
                        logger.error(f"Failed to import subpackage '{modname}'", error=str(e))
                        continue
                else:
                    try:
                        module = importlib.import_module(modname)
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if obj.__module__ != modname:
                                continue
                            if issubclass(obj, (ProducerNode, BlockingNode, NonBlockingNode)):
                                if obj not in cls._abstract_base_classes:
                                    discovered_classes.append(obj)
                    except Exception as e:
                        logger.error(f"Failed to import module '{modname}'", error=str(e))
                        continue

        walk_packages(Nodes.__path__, Nodes.__name__ + ".")

        mapping = {}
        for node_class in discovered_classes:
            try:
                identifier = node_class.identifier()
                mapping[identifier] = node_class
            except Exception:
                continue

        logger.info(f"Auto-discovered {len(mapping)} node Types in Nodes Package")
        return mapping

    @classmethod
    def _ensure_registry_loaded(cls) -> None:
        if cls._node_registry is None:
            cls._node_registry = cls._discover_node_classes()

    @classmethod
    def create_node(cls, nodeConfig: NodeConfig) -> BaseNode:
        cls._ensure_registry_loaded()
        node_cls = cls._node_registry.get(nodeConfig.type)
        if node_cls:
            instance = node_cls(nodeConfig)
            logger.info(f"Initialized BaseNode Instance", base_node_type=node_type(instance), node_id=nodeConfig.id)
            return instance
        
        available_types = list(cls._node_registry.keys())
        raise ValueError(
            f"Unknown node type '{nodeConfig.type}' for node id '{nodeConfig.id}'. "
            f"Available types: {available_types}"
        )
