from dataclasses import dataclass, field

@dataclass
class Entity:
    """A class representing an entity."""
    id: str
    name: str
    type: str
    metadata: dict = field(default_factory=dict)
