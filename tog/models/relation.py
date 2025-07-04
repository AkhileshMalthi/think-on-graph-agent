from dataclasses import dataclass,field
from typing import List, Dict, Any
@dataclass
class Relation:
    """
    A class representing a relation between entities."""
    id: str
    source_id: str
    target_id: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
