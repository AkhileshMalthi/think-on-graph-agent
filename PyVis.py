from pyvis.network import Network
import networkx as nx
from jinja2 import Template
import json

def visualize_graph_interactively(G):
    net = Network(notebook=False)
    net.from_nx(G)

    nodes, edges = net.get_nodes(), net.get_edges()
    
    net.template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>PyVis Graph</title>
      <style type="text/css"> #mynetwork { width: 100%; height: 95vh; border: 1px solid lightgray; } </style>
    </head>
    <body>
      <div id="mynetwork"></div>
      <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
      <script type="text/javascript">
        var container = document.getElementById('mynetwork');
        var options = {{ options }};
        var data = {
            nodes: {{ nodes | safe }},
            edges: {{ edges | safe }}
        };
        var network = new vis.Network(container, data, options);
      </script>
    </body>
    </html>
    """)

    net.show_buttons(filter_=['physics'])  # Enable physics options if needed
    net.show("graph.html")

if __name__ =='__main__':
    # Example usage
    G = nx.Graph()
    G.add_edge("Barack Obama", "United States")
    G.add_edge("Barack Obama", "President")
    visualize_graph_interactively(G)
