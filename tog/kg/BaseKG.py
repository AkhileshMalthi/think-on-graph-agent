from abc import ABC, abstractmethod

class BaseKG(ABC):
    def __init__(self, graph_endpoint):
        self.graph_endpoint = graph_endpoint

    @abstractmethod
    def create_entity(self, entity_data):
        """Creates a new entity in the KG."""
        pass

    @abstractmethod
    def create_relationship(self, relationship_data):
        """Creates a new relationship in the KG."""
        pass

    @abstractmethod
    def update_entity(self, entity_id, updated_data):
        """Updates an existing entity in the KG."""
        pass

    @abstractmethod
    def update_relationship(self, relationship_id, updated_data):
        """Updates an existing relationship in the KG."""
        pass

    @abstractmethod
    def delete_entity(self, entity_id):
        """Deletes an entity from the KG."""
        pass

    @abstractmethod
    def delete_relationship(self, relationship_id):
        """Deletes a relationship from the KG."""
        pass

    @abstractmethod
    def save_graph(self):
        """Saves the current state of the graph."""
        pass

    @abstractmethod
    def load_graph(self):
        """Loads the graph from the specified endpoint."""
        pass
