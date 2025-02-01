from pyvis.network import Network
import networkx as nx

def visualize_graph(graph: nx.MultiDiGraph, output_path: str = "KG_Visualized.html", 
                   height: str = "750px", width: str = "100%"):
    """
    Visualizes the knowledge graph and saves it to an HTML file.
    """
    net = Network(height=height, width=width, directed=True)
    
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
        
        metadata_str = "\n".join([f"  {k}: {v}" for k, v in data['metadata'].items()])
        title = f"""
        Type: {data.get('type', 'NA')}
        ID: {data['id']}
        Metadata:
{metadata_str}
        """
        net.add_edge(source, target, 
                    title=title,
                    color=target_color)
    
    # Add legend and set options
    legend_html = create_legend(entity_colors)
    
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

def create_legend(entity_colors: dict) -> str:
    """Creates HTML legend for entity types."""
    legend_html = "<div style='padding: 10px; background-color: white; border: 1px solid #ccc;'>"
    legend_html += "<h3>Entity Types</h3>"
    for etype, color in entity_colors.items():
        legend_html += f"<div><span style='color: {color}'>●</span> {etype}</div>"
    legend_html += "</div>"
    return legend_html

