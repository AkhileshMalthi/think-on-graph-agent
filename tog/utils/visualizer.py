import os
import networkx as nx
from pyvis.network import Network
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any, Union

class Visualizer(ABC):
    """
    Base class for graph visualizers.
    """
    def __init__(self, height: str = "750px", width: str = "100%"):
        self.height = height
        self.width = width
    
    @abstractmethod
    def load_data(self, file_path: str) -> Any:
        """Load data from the specified file path."""
        pass
    
    @abstractmethod
    def build_graph(self, data: Any) -> nx.MultiDiGraph:
        """Build a networkx graph from the loaded data."""
        pass
    
    def visualize(self, graph: nx.MultiDiGraph, output_path: str) -> None:
        """Visualize the graph and save to output_path."""
        net = Network(height=self.height, width=self.width, directed=True)
        
        # Define base colors for entity types
        base_colors = [
            '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f',
            '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'
        ]
        
        # Create color mappings for entity types
        entity_types = list(set([data.get('type', 'NA') for _, data in graph.nodes(data=True)]))
        entity_colors = {
            entity_type: base_colors[i % len(base_colors)] 
            for i, entity_type in enumerate(entity_types)
        }
        
        # Add nodes and edges
        for node, data in graph.nodes(data=True):
            metadata_str = "\n".join([f"  {k}: {v}" for k, v in data.get('metadata', {}).items()])
            title = f"""
            Type: {data.get('type', 'NA')}
            Name: {data.get('name', 'NA')}
            Metadata:
{metadata_str}
            """
            net.add_node(node, 
                        title=title, 
                        label=data.get('name', 'NA'),
                        color=entity_colors[data.get('type', 'NA')])
        
        for source, target, key, data in graph.edges(keys=True, data=True):
            target_type = graph.nodes[target].get('type', 'NA')
            target_color = entity_colors[target_type]
            
            metadata_str = "\n".join([f"  {k}: {v}" for k, v in data.get('metadata', {}).items()])
            title = f"""
            Type: {data.get('type', 'NA')}
            ID: {data.get('id', 'NA')}
            Metadata:
{metadata_str}
            """
            net.add_edge(source, target, 
                        title=title,
                        color=target_color)
        
        # Add legend and set options
        legend_html = self._create_legend(entity_colors)
        
        net.set_options("""
        {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -2000,
              "centralGravity": 0.3,
              "springLength": 95
            },
            "minVelocity": 0.75
          },
          "nodes": {
            "font": {
              "size": 14
            }
          }
        }
        """)
        
        net.save_graph(output_path)
        
        # Add legend to HTML
        with open(output_path, 'r') as f:
            html_content = f.read()
        html_content = html_content.replace('</body>', f'{legend_html}</body>')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _create_legend(self, entity_colors: Dict[str, str]) -> str:
        """Creates HTML legend for entity types."""
        legend_html = "<div style='padding: 10px; background-color: white; border: 1px solid #ccc;'>"
        legend_html += "<h3>Entity Types</h3>"
        for etype, color in entity_colors.items():
            legend_html += f"<div><span style='color: {color}'>●</span> {etype}</div>"
        legend_html += "</div>"
        return legend_html
    
    def process_and_visualize(self, input_file: str, output_path: str) -> None:
        """
        End-to-end process to load, build, and visualize the graph.
        """
        data = self.load_data(input_file)
        graph = self.build_graph(data)
        self.visualize(graph, output_path)


class NTVisualizer(Visualizer):
    """
    Visualizer for N-Triple (.nt) RDF files.
    """
    def __init__(self, height: str = "750px", width: str = "100%"):
        super().__init__(height, width)
    
    def load_data(self, file_path: str) -> List[tuple]:
        """Load data from N-Triple file."""
        triples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Basic parsing for N-Triples format
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        subject = parts[0].strip('<>')
                        predicate = parts[1].strip('<>')
                        # Handle the object part which might contain spaces
                        object_part = parts[2].rsplit(' .', 1)[0]
                        if object_part.startswith('<'):
                            object_val = object_part.strip('<>')
                        else:
                            # Handle literal values
                            object_val = object_part.strip('"')
                        triples.append((subject, predicate, object_val))
        return triples
    
    def build_graph(self, data: List[tuple]) -> nx.MultiDiGraph:
        """Build a graph from N-Triple data."""
        G = nx.MultiDiGraph()
        
        # Track entity types and properties
        entity_metadata = {}
        
        # First pass: identify entities and their types
        for subject, predicate, obj in data:
            if 'type' in predicate.lower() and not predicate.endswith('type'):
                # Save entity type
                entity_metadata.setdefault(subject, {}).setdefault('type', obj.split('/')[-1])
            elif 'name' in predicate.lower() or 'label' in predicate.lower():
                # Save entity name
                entity_metadata.setdefault(subject, {}).setdefault('name', obj)
            else:
                # Other metadata properties
                entity_metadata.setdefault(subject, {}).setdefault('metadata', {})
                pred_name = predicate.split('/')[-1]
                entity_metadata[subject]['metadata'][pred_name] = obj
        
        # Add nodes with their metadata
        for entity, metadata in entity_metadata.items():
            G.add_node(
                entity, 
                name=metadata.get('name', entity.split('/')[-1]),
                type=metadata.get('type', 'Unknown'),
                metadata=metadata.get('metadata', {})
            )
        
        # Second pass: add edges
        edge_id = 0
        for subject, predicate, obj in data:
            # Only add edges between entities, not properties
            if obj in entity_metadata:
                pred_name = predicate.split('/')[-1]
                G.add_edge(
                    subject, 
                    obj, 
                    id=f"e{edge_id}",
                    type=pred_name,
                    metadata={'predicate': predicate}
                )
                edge_id += 1
        
        return G


def visualize_knowledge_graph(file_path: str, output_path: str = "kg_visualization.html",
                             height: str = "750px", width: str = "100%"):
    """
    Convenience function to visualize a knowledge graph from an NT file.
    """
    visualizer = NTVisualizer(height=height, width=width)
    visualizer.process_and_visualize(file_path, output_path)

if __name__ == "__main__":
    # Example usage of the knowledge graph visualizer
    nt_file_path = "tog\data\kg.nt"
    output_path = "cannabidiol_knowledge_graph.html"
    
    # # Visualize the knowledge graph
    # visualize_knowledge_graph(nt_file_path, output_path)
    
    # print(f"Knowledge graph visualization saved to {output_path}")
    
    # For more customization
    custom_visualizer = NTVisualizer(height="900px", width="1200px")
    custom_output = "custom_cannabidiol_kg.html"
    custom_visualizer.process_and_visualize(nt_file_path, custom_output)
    
    print(f"Custom knowledge graph visualization saved to {custom_output}")