import networkx as nx
from pyvis.network import Network

class NxKG:
    def __init__(self):
        """
        Initialize a new knowledge graph using NetworkX.
        """
        self.graph = nx.MultiDiGraph()

    def add_entity(self, name, **properties):
        """
        Add an entity to the knowledge graph with arbitrary properties.
        
        Args:
            name (str): Unique identifier for the entity
            **properties: Arbitrary keyword arguments for entity properties
        """
        # if name not in self.graph:
        #     self.graph.add_node(name, **properties)
        # return self
        self.graph.add_node(name, **properties)


    def add_relationship(self, source, target, **properties):
        """
        Add a relationship between two entities with arbitrary properties.
        
        Args:
            source (str): Name of the source entity
            target (str): Name of the target entity
            **properties: Arbitrary keyword arguments for relationship properties
        """
        # if source not in self.graph:
        #     raise ValueError(f"Source entity '{source}' does not exist.")
        # if target not in self.graph:
        #     raise ValueError(f"Target entity '{target}' does not exist.")
        
        self.graph.add_edge(source, target, **properties)
        return self

    def load_from_json(self, json_data):
        """
        Load a knowledge graph from a JSON dictionary.
        
        Args:
            json_data (dict): JSON dictionary containing entities and relationships
        """
        # Add entities with all their properties
        for entity in json_data.get('entities', []):
            # Extract name and use remaining properties as is
            name = entity.pop('name')
            self.add_entity(name, **entity)
        
        # Add relationships with all their properties
        for relationship in json_data.get('relationships', []):
            # Extract source and target, use remaining properties as is
            source = relationship.pop('source')
            target = relationship.pop('target')
            self.add_relationship(source, target, **relationship)
        return self

    def visualize(self, output_file='knowledge_graph.html', node_color_property='type', node_color_map=None):
        """
        Visualize the knowledge graph using PyVis.
        
        Args:
            output_file (str): Path to save the HTML visualization
            node_color_property (str): Node property to use for coloring
            node_color_map (dict): Mapping of property values to colors
        """
        if node_color_map is None:
            node_color_map = {
                'Person': '#87CEFA',
                'Organization': '#90EE90',
                'Location': '#FFA07A'
            }
        
        net = Network(height='600px', width='100%', bgcolor='#ffffff', 
                     font_color='black', notebook=False)
        
        # Add nodes
        for node, data in self.graph.nodes(data=True):
            # Get color based on the specified property if it exists
            color = node_color_map.get(
                data.get(node_color_property, ''),
                '#D3D3D3'  # Default color
            )
            
            # Use all properties as tooltip content
            tooltip = '\n'.join(f"{k}: {v}" for k, v in data.items())
            
            net.add_node(node, label=node, title=tooltip, color=color)
        
        # Add edges
        for source, target, data in self.graph.edges(data=True):
            # Use all properties as tooltip content
            tooltip = '\n'.join(f"{k}: {v}" for k, v in data.items())
            
            # Use relationship_types as label if it exists, otherwise empty
            label = ', '.join(data.get('relationship_types', [])) if 'relationship_types' in data else ''
            
            # Use strength for color if it exists
            strength_color_map = {
                'strong': '#000000',
                'medium': '#808080',
                'weak': '#C0C0C0'
            }
            edge_color = strength_color_map.get(data.get('strength', ''), '#808080')
            
            net.add_edge(source, target, label=label, title=tooltip, color=edge_color)
        
        # Configure physics and interaction
        net.set_options('''
        var options = {
            "nodes": {
                "font": {"size": 12},
                "scaling": {"min": 10, "max": 30}
            },
            "edges": {
                "color": {"inherit": false},
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
        
        net.save_graph(output_file)
        print(f"Check out the visualization in {output_file}")
        return self

    def get_entities_by_property(self, property_name, property_value):
        """
        Retrieve all entities that have a specific property value.
        
        Args:
            property_name (str): Name of the property to filter by
            property_value: Value of the property to match
        
        Returns:
            list: Entities matching the property criteria
        """
        return [
            node for node, data in self.graph.nodes(data=True)
            if data.get(property_name) == property_value
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
            {'name': node, **data}
            for node, data in self.graph.nodes(data=True)
        ]
        
        relationships = [
            {'source': u, 'target': v, **data}
            for (u, v, data) in self.graph.edges(data=True)
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