from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Entity:
    """
    Represents an entity in the knowledge graph.
    """
    id: str
    name: str
    type: str
    metadata: Dict[str, Any] = None

    def to_dict(self):
        """
        Converts the Entity instance to a dictionary.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "metadata": self.metadata or {}
        }
