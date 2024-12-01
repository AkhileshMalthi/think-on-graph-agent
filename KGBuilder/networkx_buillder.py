import networkx as nx
from pyvis.network import Network

class NxKG:
    def __init__(self):
        """
        Initialize a new knowledge graph using NetworkX.
        """
        self.graph = nx.MultiDiGraph()

    def add_entity(self, name, entity_type, description=None):
        """
        Add an entity to the knowledge graph.
        
        Args:
            name (str): Unique identifier for the entity
            entity_type (str): Type of the entity (e.g., Person, Organization, Location)
            description (str, optional): Description of the entity
        """
        # Check if entity already exists
        if name not in self.graph:
            self.graph.add_node(
                name, 
                type=entity_type, 
                description=description
            )
        return self

    def add_relationship(self, source, target, relationship_types=None, description=None, strength=None):
        """
        Add a relationship between two entities in the knowledge graph.
        
        Args:
            source (str): Name of the source entity
            target (str): Name of the target entity
            relationship_types (list, optional): Types of relationships
            description (str, optional): Description of the relationship
            strength (str, optional): Strength of the relationship
        """
        # Ensure both entities exist
        if source not in self.graph:
            raise ValueError(f"Source entity '{source}' does not exist.")
        if target not in self.graph:
            raise ValueError(f"Target entity '{target}' does not exist.")
        
        # Add edge with relationship details
        self.graph.add_edge(
            source, 
            target, 
            relationship_types=relationship_types or [],
            description=description,
            strength=strength
        )
        return self

    def load_from_json(self, json_data):
        """
        Load a knowledge graph from a JSON dictionary.
        
        Args:
            json_data (dict): JSON dictionary containing entities and relationships
        """
        # Add entities
        for entity in json_data.get('entities', []):
            self.add_entity(
                name=entity['name'], 
                entity_type=entity['type'], 
                description=entity.get('description')
            )
        
        # Add relationships
        for relationship in json_data.get('relationships', []):
            self.add_relationship(
                source=relationship['source'],
                target=relationship['target'],
                relationship_types=relationship.get('relationship_types', []),
                description=relationship.get('description'),
                strength=relationship.get('strength')
            )
        return self

    def visualize(self, output_file='knowledge_graph.html', node_color_map=None):
        """
        Visualize the knowledge graph using PyVis.
        
        Args:
            output_file (str, optional): Path to save the HTML visualization
            node_color_map (dict, optional): Mapping of entity types to colors
        """
        # Default color map if not provided
        if node_color_map is None:
            node_color_map = {
                'Person': '#87CEFA',  # Light Sky Blue
                'Organization': '#90EE90',  # Light Green
                'Location': '#FFA07A'  # Light Salmon
            }
        
        # Create PyVis network
        net = Network(
            height='600px', 
            width='100%', 
            bgcolor='#ffffff', 
            font_color='black',
            notebook=False
        )
        
        # Add nodes with colors based on entity type
        for node, data in self.graph.nodes(data=True):
            color = node_color_map.get(data['type'], '#D3D3D3')  # Default to light gray
            net.add_node(
                node, 
                label=node, 
                title=data.get('description', ''),
                color=color
            )
        
        # Add edges with relationship types as labels
        for source, target, data in self.graph.edges(data=True):
            # Combine relationship types into a single label
            edge_label = ', '.join(data.get('relationship_types', []))
            
            # Determine edge color based on strength
            strength_color_map = {
                'strong': '#000000',  # Black
                'medium': '#808080',  # Gray
                'weak': '#C0C0C0'     # Light Gray
            }
            edge_color = strength_color_map.get(data.get('strength'), '#808080')
            
            net.add_edge(
                source, 
                target, 
                label=edge_label,
                title=data.get('description', ''),
                color=edge_color
            )
        
        # Configure physics and interaction
        net.set_options('''
        var options = {
            "nodes": {
                "font": {
                    "size": 12
                },
                "scaling": {
                    "min": 10,
                    "max": 30
                }
            },
            "edges": {
                "color": {
                    "inherit": false
                },
                "smooth": false
            },
            "physics": {
                "barnesHut": {
                    "gravitationalConstant": -3000,
                    "springLength": 200,
                    "springConstant": 0.01
                },
                "minVelocity": 0.75
            }
        }
        ''')
        
        # Save or show the network
        net.save_graph(output_file)
        print(f"Check out the visualization in {output_file}")
        return self

    def get_entities_by_type(self, entity_type):
        """
        Retrieve all entities of a specific type.
        
        Args:
            entity_type (str): Type of entities to retrieve
        
        Returns:
            list: Entities of the specified type
        """
        return [
            node for node, data in self.graph.nodes(data=True) 
            if data['type'] == entity_type
        ]

    def get_relationships_for_entity(self, entity_name):
        """
        Get all relationships for a specific entity.
        
        Args:
            entity_name (str): Name of the entity
        
        Returns:
            dict: Outgoing and incoming relationships
        """
        return {
            'outgoing': list(self.graph.out_edges(entity_name, data=True)),
            'incoming': list(self.graph.in_edges(entity_name, data=True))
        }

    def export_to_json(self):
        """
        Export the knowledge graph to a JSON format.
        
        Returns:
            dict: JSON representation of the knowledge graph
        """
        entities = [
            {
                'name': node,
                'type': data['type'],
                'description': data.get('description')
            } for node, data in self.graph.nodes(data=True)
        ]
        
        relationships = [
            {
                'source': u,
                'target': v,
                'relationship_types': data.get('relationship_types', []),
                'description': data.get('description'),
                'strength': data.get('strength')
            } for (u, v, data) in self.graph.edges(data=True)
        ]
        
        return {
            'entities': entities,
            'relationships': relationships
        }

# Example usage
# if __name__ == "__main__":
#     # Sample JSON data
#     sample_data = {
#         "entities": [
#             {
#                 "name": "Google",
#                 "type": "Organization",
#                 "description": "A multinational technology company specializing in Internet-related services and products."
#             },
#             {
#                 "name": "Larry Page",
#                 "type": "Person",
#                 "description": "Co-founder of Google."
#             },
#             {
#                 "name": "Sergey Brin",
#                 "type": "Person",
#                 "description": "Co-founder of Google."
#             },
#             {
#                 "name": "California",
#                 "type": "Location",
#                 "description": "A state in the United States where Google was founded."
#             }
#         ],
#         "relationships": [
#             {
#                 "source": "Google",
#                 "target": "Larry Page",
#                 "description": "Larry Page co-founded Google.",
#                 "relationship_types": ["founder", "co-founder"],
#                 "strength": "strong"
#             },
#             {
#                 "source": "Google",
#                 "target": "Sergey Brin",
#                 "description": "Sergey Brin co-founded Google.",
#                 "relationship_types": ["founder", "co-founder"],
#                 "strength": "strong"
#             },
#             {
#                 "source": "Google",
#                 "target": "California",
#                 "description": "Google was founded in California.",
#                 "relationship_types": ["location", "founded in"],
#                 "strength": "medium"
#             }
#         ]
#     }

#     # Create a knowledge graph
#     kg = NxKG()
#     kg.load_from_json(sample_data)
#     kg.visualize()