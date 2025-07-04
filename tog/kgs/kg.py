from abc import ABC, abstractmethod
from typing import Any, Dict, List


class KnowledgeGraph(ABC):
    """
    Abstract base class for knowledge graph implementations.
    Provides a common interface for different knowledge graph backends.
    """
    
    @abstractmethod
    def __init__(self, source: Any, **kwargs):
        """Initialize a knowledge graph from a source"""
        pass
    
    @abstractmethod
    def query(self, query_str: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute a query against the knowledge graph"""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get the size of the knowledge graph"""
        pass
    