import networkx as nx
from pyvis.network import Network
import json


class NxKG:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_entity(self, name, **properties):
        self.graph.add_node(name, **properties)

    def add_relationship(self, source, target, **properties):
        self.graph.add_edge(source, target, **properties)
        return self

    def visualize_simple(self, output_file="knowledge_graph.html"):
        import os
        from pyvis.network import Network
        net = Network(height="1200px", width="100%", directed=True, notebook=False, bgcolor="#222222", font_color="white")
        nodes = list(self.graph.nodes(data=True))
        edges = list(self.graph.edges(data=True))

        # Build lookup for valid nodes (by name)
        node_dict = {node: data for node, data in nodes}
        valid_edges = []
        valid_node_names = set()
        for source, target, data in edges:
            if source in node_dict and target in node_dict:
                valid_edges.append((source, target, data))
                valid_node_names.update([source, target])

        # Add valid nodes
        for node_name in valid_node_names:
            data = node_dict[node_name]
            try:
                net.add_node(node_name, label=node_name, title=str(data.get("type", "")), group=data.get("type", ""))
            except:
                continue

        # Add valid edges
        for source, target, data in valid_edges:
            try:
                net.add_edge(source, target, label=str(data.get("type", "")).lower())
            except:
                continue

        net.set_options("""
        {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -100,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08
                },
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based"
            }
        }
        """)
        net.save_graph(output_file)
        print(f"Graph saved to {os.path.abspath(output_file)}")
        try:
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(output_file)}")
        except:
            print("Could not open browser automatically")
        return self

    def load_from_pipeline_json(self, json_data):
        """
        Load a knowledge graph from the pipeline JSON format.

        Args:
            json_data (dict): JSON dictionary from the KG pipeline
        """
        # Clear existing graph
        self.graph.clear()
        
        # Create a mapping from entity IDs to names for relationships
        entity_id_to_name = {}
        
        # Add entities with all their properties
        for entity in json_data.get("entities", []):
            name = entity.get("name", "Unknown")
            entity_id = entity.get("id", "")
            entity_type = entity.get("type", "Unknown")
            metadata = entity.get("metadata", {})
            
            # Store mapping for relationships
            entity_id_to_name[entity_id] = name
            
            # Add entity with all properties
            self.add_entity(
                name,
                id=entity_id,
                type=entity_type,
                **metadata
            )

        # Add relationships with all their properties
        for relationship in json_data.get("relationships", []):
            source_id = relationship.get("source_id", "")
            target_id = relationship.get("target_id", "")
            rel_type = relationship.get("type", "RELATED_TO")
            metadata = relationship.get("metadata", {})
            
            # Get entity names from IDs
            source_name = entity_id_to_name.get(source_id, f"Unknown_{source_id}")
            target_name = entity_id_to_name.get(target_id, f"Unknown_{target_id}")
            
            # Add relationship with all properties
            self.add_relationship(
                source_name,
                target_name,
                type=rel_type,
                source_id=source_id,
                target_id=target_id,
                **metadata
            )
        
        return self

    def load_from_json_file(self, file_path):
        """
        Load a knowledge graph from a JSON file.

        Args:
            file_path (str): Path to the JSON file
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        return self.load_from_pipeline_json(json_data)

    def visualize(
        self,
        output_file="knowledge_graph.html",
        node_color_property="type",
        node_color_map=None,
        show_chunk_info=True,
        physics_enabled=True
    ):
        """
        Visualize the knowledge graph using PyVis.

        Args:
            output_file (str): Path to save the HTML visualization
            node_color_property (str): Node property to use for coloring
            node_color_map (dict): Mapping of property values to colors
            show_chunk_info (bool): Whether to show chunk information in tooltips
            physics_enabled (bool): Whether to enable physics simulation
        """
        if node_color_map is None:
            node_color_map = {
                "PERSON": "#87CEFA",
                "ORG": "#90EE90", 
                "ORGANIZATION": "#90EE90",
                "GPE": "#FFA07A",  # Geopolitical entities
                "LOCATION": "#FFA07A",
                "PRODUCT": "#FFB6C1",
                "WORK_OF_ART": "#DDA0DD",
                "EVENT": "#F0E68C",
                "LAW": "#B0C4DE",
                "LANGUAGE": "#98FB98",
                "NORP": "#F4A460",  # Nationalities or religious groups
                "FACILITY": "#DEB887",
                "MONEY": "#FFD700",
                "PERCENT": "#FFA500",
                "DATE": "#FF6347",
                "TIME": "#FF69B4",
                "CARDINAL": "#32CD32",
                "ORDINAL": "#FF1493"
            }

        net = Network(
            height="800px",
            width="100%",
            bgcolor="#ffffff",
            font_color="black",
            notebook=False,
        )

        # Add nodes
        for node, data in self.graph.nodes(data=True):
            # Get color based on the specified property if it exists
            node_type = data.get(node_color_property, "").upper()
            color = node_color_map.get(node_type, "#D3D3D3")  # Default color

            # Create tooltip content
            tooltip_parts = [f"Name: {node}"]
            
            # Add basic properties
            for key in ["type", "id"]:
                if key in data:
                    tooltip_parts.append(f"{key.title()}: {data[key]}")
            
            # Add chunk information if available and requested
            if show_chunk_info:
                for key in ["chunk_id", "section_id"]:
                    if key in data:
                        tooltip_parts.append(f"{key.replace('_', ' ').title()}: {data[key]}")
            
            # Add description if available
            if "description" in data:
                tooltip_parts.append(f"Description: {data['description']}")
            
            # Add attributes if available
            if "attributes" in data and data["attributes"]:
                tooltip_parts.append("Attributes:")
                for attr_key, attr_value in data["attributes"].items():
                    tooltip_parts.append(f"  {attr_key}: {attr_value}")
            
            tooltip = "\n".join(tooltip_parts)

            # Set node size based on number of connections
            node_degree = self.graph.degree(node)
            size = max(10, min(30, 10 + node_degree * 2))

            net.add_node(
                node, 
                label=node, 
                title=tooltip, 
                color=color,
                size=size
            )

        # Add edges
        for source, target, data in self.graph.edges(data=True):
            # Create tooltip content for edges
            tooltip_parts = [f"From: {source}", f"To: {target}"]
            
            # Add relationship type
            if "type" in data:
                tooltip_parts.append(f"Type: {data['type']}")
            
            # Add chunk information if available and requested
            if show_chunk_info:
                for key in ["chunk_id", "section_id"]:
                    if key in data:
                        tooltip_parts.append(f"{key.replace('_', ' ').title()}: {data[key]}")
            
            # Add description if available
            if "description" in data:
                tooltip_parts.append(f"Description: {data['description']}")
            
            # Add strength if available
            if "strength" in data:
                tooltip_parts.append(f"Strength: {data['strength']}")
            
            tooltip = "\n".join(tooltip_parts)

            # Set edge label
            label = data.get("type", "")

            # Set edge color based on strength or type
            edge_color = "#808080"  # Default
            if "strength" in data:
                strength_color_map = {
                    "strong": "#000000",
                    "medium": "#808080", 
                    "weak": "#C0C0C0",
                }
                edge_color = strength_color_map.get(str(data["strength"]), "#808080")

            net.add_edge(
                source, 
                target, 
                label=label, 
                title=tooltip, 
                color=edge_color,
                width=2
            )

        # Improved physics: less gap, less jumping, and better tooltips
        physics_options = '''
var options = {
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -80,
      "centralGravity": 0.01,
      "springLength": 200,
      "springConstant": 0.06,
      "avoidOverlap": 1
    },
    "minVelocity": 0.5,
    "solver": "forceAtlas2Based",
    "timestep": 0.3,
    "stabilization": {
      "enabled": true,
      "iterations": 300,
      "fit": true
    }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 100,
    "hideEdgesOnDrag": true,
    "hideNodesOnDrag": false,
    "navigationButtons": true,
    "keyboard": true
  }
}
'''



        # Use JSON-formatted tooltips for nodes and edges
        import json as _json
        for node, data in self.graph.nodes(data=True):
            tooltip = _json.dumps({"name": node, **data}, indent=2)
            node_id = node
            net.nodes = [n if n["id"] != node_id else {**n, "title": tooltip.replace('"', '\"').replace('\n', '<br>')} for n in net.nodes]

        for source, target, data in self.graph.edges(data=True):
            tooltip = _json.dumps({"source": source, "target": target, **data}, indent=2)
            # Find the edge in net.edges and update its title
            for edge in net.edges:
                if edge["from"] == source and edge["to"] == target:
                    edge["title"] = tooltip.replace('"', '\"').replace('\n', '<br>')

        net.set_options(physics_options)
        net.save_graph(output_file)
        print(f"Knowledge graph visualization saved to {output_file}")
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
            node
            for node, data in self.graph.nodes(data=True)
            if data.get(property_name) == property_value
        ]

    def get_entities_by_chunk(self, chunk_id):
        """
        Get all entities from a specific chunk.

        Args:
            chunk_id (str): ID of the chunk

        Returns:
            list: Entities from the specified chunk
        """
        return self.get_entities_by_property("chunk_id", chunk_id)

    def get_relationships_for_entity(self, entity_name):
        """
        Get all relationships for a specific entity.

        Args:
            entity_name (str): Name of the entity

        Returns:
            dict: Outgoing and incoming relationships
        """
        return {
            "outgoing": list(self.graph.out_edges(entity_name, data=True)),
            "incoming": list(self.graph.in_edges(entity_name, data=True)),
        }

    def get_graph_statistics(self):
        """
        Get basic statistics about the knowledge graph.

        Returns:
            dict: Graph statistics
        """
        entity_types = {}
        relationship_types = {}
        chunks = set()
        sections = set()
        
        # Count entity types and collect chunks/sections
        for node, data in self.graph.nodes(data=True):
            entity_type = data.get("type", "Unknown")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            if "chunk_id" in data:
                chunks.add(data["chunk_id"])
            if "section_id" in data:
                sections.add(data["section_id"])
        
        # Count relationship types
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get("type", "Unknown")
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        
        return {
            "total_entities": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            "unique_chunks": len(chunks),
            "unique_sections": len(sections),
            "average_degree": sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() if self.graph.number_of_nodes() > 0 else 0
        }

    def export_to_json(self):
        """
        Export the knowledge graph to a JSON format.

        Returns:
            dict: JSON representation of the knowledge graph
        """
        entities = [
            {"name": node, **data} for node, data in self.graph.nodes(data=True)
        ]

        relationships = [
            {"source": u, "target": v, **data}
            for (u, v, data) in self.graph.edges(data=True)
        ]

        return {"entities": entities, "relationships": relationships}


def main():
    """
    Example usage of the updated NxKG class
    """
    # Create a knowledge graph instance
    kg = NxKG()
    
    # Load from your pipeline JSON file
    kg.load_from_json_file(r"knowledge_graph2.json")
    
    # Print statistics
    stats = kg.get_graph_statistics()
    print("Knowledge Graph Statistics:")
    print(f"Total Entities: {stats['total_entities']}")
    print(f"Total Relationships: {stats['total_relationships']}")
    print(f"Unique Chunks: {stats['unique_chunks']}")
    print(f"Unique Sections: {stats['unique_sections']}")
    print(f"Average Degree: {stats['average_degree']:.2f}")
    
    print("\nEntity Types:")
    for entity_type, count in stats['entity_types'].items():
        print(f"  {entity_type}: {count}")
    
    print("\nRelationship Types:")
    for rel_type, count in stats['relationship_types'].items():
        print(f"  {rel_type}: {count}")
    
    # Create visualization
    kg.visualize(
        output_file="knowledge_graph_visualization2.html",
        show_chunk_info=True,
        physics_enabled=True
    )


if __name__ == "__main__":
    main()