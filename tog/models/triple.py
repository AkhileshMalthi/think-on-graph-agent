from dataclasses import dataclass
from tog.models.entity import Entity
from tog.models.relation import Relation

@dataclass
class Triple:
    """
    A class representing a triple consisting of a subject, predicate, and object.
    """
    subject: Entity
    predicate: Relation
    object: Entity
    metadata: dict = None

