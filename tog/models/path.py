from dataclasses import dataclass, field
import heapq
from typing import List, Set
from tog.models.entity import Entity
from tog.models.relation import Relation
from tog.models.triple import Triple

@dataclass
class Path:
    path: List[Triple] = field(default_factory=list)
    confidence_score: float = None
    metadata: dict = field(default_factory=dict)
    visited_entities: Set[str] = field(default_factory=set)

    def add_triple(self, triple: Triple):
        """Add a triple to the path and track visited entities."""
        self.path.append(triple)
        # Track visited entities
        if triple.subject:
            self.visited_entities.add(triple.subject.id)
        if triple.object:
            self.visited_entities.add(triple.object.id)
    
    def set_confidence_score(self, score: float):
        """Set the confidence score for the path."""
        self.confidence_score = score
    
    def get_last_entity(self) -> Entity:
        """Get the last entity in the path."""
        if self.path:
            return self.path[-1].object
        return None
    
    def get_last_relation(self) -> Relation:
        """Get the last relation in the path."""
        if self.path:
            return self.path[-1].predicate
        return None

    def has_visited(self, entity_id: str) -> bool:
        """Check if an entity has been visited in this path."""
        return entity_id in self.visited_entities
    
    def copy_visited_entities(self) -> set:
        """Return a copy of visited entities for creating new paths."""
        return self.visited_entities.copy()

@dataclass
class TopNPaths:
    n: int
    heap: List = None
    _counter: int = 0  # Add a counter to break ties
    
    def __post_init__(self):
        if self.heap is None:
            self.heap = []
    
    def add_path(self, path: Path, confidence: float):
        # Use a counter to break ties when confidence values are equal
        self._counter += 1
        # Store as (priority, counter, path) to handle ties properly
        heapq.heappush(self.heap, (-confidence, self._counter, path))
        # Maintain only top n paths
        if len(self.heap) > self.n:
            heapq.heappop(self.heap)
    
    def get_paths(self):
        # Return paths sorted by confidence in descending order
        return [path for _, _, path in sorted(self.heap)]