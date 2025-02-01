from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Relationship:
    """
    Represents a relationship between entities in the knowledge graph.
    """
    id: str
    source_id: str
    target_id: str
    type: str
    metadata: Dict[str, Any] = None

    def to_dict(self):
        """
        Converts the Relationship instance to a dictionary.
        """
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "metadata": self.metadata or {}
        }
