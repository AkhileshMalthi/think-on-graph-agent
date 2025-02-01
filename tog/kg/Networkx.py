import networkx as nx
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, Any
from .models.entity import Entity
from .models.relationship import Relationship
from .visualization import visualize_graph
from .BaseKG import BaseKG

class NetworkxKG(BaseKG):
    def __init__(self, graph_endpoint: str):
        """
        Initializes the NetworkxKG instance.

        Args:
            graph_endpoint (str): The file path to the graph data.
        """
        super().__init__(graph_endpoint)
        self.graph = nx.MultiDiGraph()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.load_graph()

    def _generate_embeddings(self, text: str) -> np.ndarray:
        """
        Generates embeddings for the given text.

        Args:
            text (str): Input text to generate embeddings for.

        Returns:
            np.ndarray: The generated embedding vector.
        """
        return self.model.encode(text, convert_to_tensor=False)

    @property
    def entities_size(self):
        """
        Returns the number of entities in the graph.
        """
        return len(self.graph.nodes)
    
    @property
    def relationships_size(self):
        """
        Returns the number of relationships in the graph.
        """
        return len(self.graph.edges)
    
    @property
    def entity_types(self):
        """
        Returns a set of unique entity types in the graph.
        """
        return set([data.get('type', 'NA') for _, data in self.graph.nodes(data=True)])
    
    @property
    def relation_types(self):
        """
        Returns a set of unique relationship types in the graph.
        """
        return set([data.get('type', 'NA') for _, _, data in self.graph.edges(data=True)])
    
    def load_graph(self):
        """
        Loads the graph data from the specified endpoint and generates embeddings.
        """
        with open(self.graph_endpoint, 'r') as f:
            data = json.load(f) 
        
        # Load entities with embeddings
        for entity_data in data.get("entities", []):
            metadata = {k: v for k, v in entity_data.items() 
                   if k not in ["id", "name", "type"]}
            entity = Entity(
            id=entity_data["id"],
            name=entity_data["name"],
            type=entity_data["type"],
            metadata=metadata
            )
            # Generate embeddings for each field separately
            embeddings = {
            "name": self._generate_embeddings(entity.name),
            "type": self._generate_embeddings(entity.type)
            }
            
            # Add embeddings for metadata fields if they are strings
            for key, value in metadata.items():
                if isinstance(value, str):
                    embeddings[key] = self._generate_embeddings(value)
            
            entity_dict = entity.to_dict()
            entity_dict["embeddings"] = embeddings
            self.graph.add_node(entity.id, **entity_dict)

        # Load relationships
        for rel_data in data.get("relationships", []):
            metadata = {k: v for k, v in rel_data.items() 
                       if k not in ["id", "source_id", "target_id", "type"]}
            relationship = Relationship(
                id=rel_data["id"],
                source_id=rel_data["source_id"],
                target_id=rel_data["target_id"],
                type=rel_data.get("type", "NA"),
                metadata=metadata
            )
            self.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                key=relationship.id,
                **relationship.to_dict()
            )

    def create_entity(self, entity_data: Dict[str, Any]):
        """
        Creates a new entity in the graph.

        Args:
            entity_data (Dict[str, Any]): The entity data.
        """
        metadata = {k: v for k, v in entity_data.items() 
                   if k not in ["id", "name", "type"]}
        entity = Entity(
            id=entity_data["id"],
            name=entity_data["name"],
            type=entity_data["type"],
            metadata=metadata
        )
        self.graph.add_node(entity.id, **entity.to_dict())

    def create_relationship(self, relationship_data: Dict[str, Any]):
        """
        Creates a new relationship in the graph.

        Args:
            relationship_data (Dict[str, Any]): The relationship data.
        """
        metadata = {k: v for k, v in relationship_data.items() 
                   if k not in ["id", "source_id", "target_id", "type"]}
        relationship = Relationship(
            id=relationship_data["id"],
            source_id=relationship_data["source_id"],
            target_id=relationship_data["target_id"],
            type=relationship_data["type"],
            metadata=metadata
        )
        self.graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            key=relationship.id,
            **relationship.to_dict()
        )

    def update_entity(self, entity_id: str, updated_data: Dict[str, Any]):
        """
        Updates an existing entity in the graph.

        Args:
            entity_id (str): The entity ID.
            updated_data (Dict[str, Any]): The updated data.
        """
        if entity_id in self.graph:
            for key, value in updated_data.items():
                self.graph.nodes[entity_id][key] = value

    def update_relationship(self, relation_id: str, updated_data: Dict[str, Any]):
        """
        Updates an existing relationship in the graph.

        Args:
            relation_id (str): The relationship ID.
            updated_data (Dict[str, Any]): The updated data.
        """
        for source, target, key, data in self.graph.edges(keys=True, data=True):
            if key == relation_id:
                for k, v in updated_data.items():
                    data[k] = v
                break

    def delete_entity(self, entity_id: str):
        """
        Deletes an entity from the graph.

        Args:
            entity_id (str): The entity ID.
        """
        if entity_id in self.graph:
            self.graph.remove_node(entity_id)

    def delete_relationship(self, relation_id: str):
        """
        Deletes a relationship from the graph.

        Args:
            relation_id (str): The relationship ID.
        """
        for source, target, key in self.graph.edges(keys=True):
            if key == relation_id:
                self.graph.remove_edge(source, target, key=key)
                break

    def save_graph(self):
        """
        Saves the current state of the graph to the specified endpoint.
        """
        data = {
            "entities": [],
            "relationships": []
        }
        
        # Save entities
        for node, node_data in self.graph.nodes(data=True):
            data["entities"].append(node_data)
        
        # Save relationships
        for source, target, key, edge_data in self.graph.edges(keys=True, data=True):
            data["relationships"].append(edge_data)
            
        with open(self.graph_endpoint, 'w') as f:
            json.dump(data, f, indent=2)

    def visualize(self, output_path: str = "kg_visualization.html", height: str = "750px", width: str = "100%"):
        """
        Visualizes the knowledge graph using the visualization module.
        """
        visualize_graph(self.graph, output_path, height, width)

