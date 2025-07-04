from pathlib import Path
import rdflib
from typing import Optional

class KGManager:
    """
    A class to manage knowledge graphs stored in RDF format files.
    Supports loading graphs from various RDF serializations (.nt, .ttl, .rdf, etc.)
    """

    GRAPHS_DIR = Path(__file__).resolve().parent

    @classmethod
    def set_graphs_dir(cls, graphs_dir: str):
        """
        Set the directory where graph files are stored.

        Args:
            graphs_dir: Path to the directory containing graph files
        """
        cls.GRAPHS_DIR = Path(graphs_dir)

    @classmethod
    def get_graph(cls, filename: str, directory: Optional[str] = None) -> rdflib.Graph:
        """
        Load a graph from an RDF file.

        Args:
            filename: Name of the RDF file (with or without extension)
            directory: Optional directory path override

        Returns:
            rdflib.Graph object containing the loaded RDF data

        Raises:
            FileNotFoundError: If the RDF file doesn't exist
            ValueError: If the file format is not supported
        """
        # Use the default graphs directory if none is provided
        if directory is None:
            graphs_dir = cls.GRAPHS_DIR
        else:
            graphs_dir = Path(directory)

        # Check if filename has an extension
        file_path = Path(filename)
        if not file_path.suffix:
            # Try to find a file with common RDF extensions
            for ext in ['.nt', '.ttl', '.rdf', '.n3', '.jsonld']:
                candidate = graphs_dir / f"{filename}{ext}"
                if candidate.exists():
                    file_path = candidate
                    break
            else:
                raise FileNotFoundError(f"No graph file found for name: {filename}")
        else:
            file_path = graphs_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Graph file not found: {file_path}")

        # Load the graph
        graph = rdflib.Graph()
        try:
            # Use the file extension to determine the format
            fmt = file_path.suffix.lstrip('.')
            graph.parse(str(file_path), format=fmt)
            return graph
        except Exception as e:
            raise ValueError(f"Error loading graph from {file_path}: {e}")

    @classmethod
    def list_graphs(cls) -> list:
        """
        List all available graph files in the graphs directory.

        Returns:
            List of graph filenames (without extension)
        """
        graph_files = []
        rdf_extensions = ['.nt', '.ttl', '.rdf', '.n3', '.jsonld']
        
        for file_path in cls.GRAPHS_DIR.iterdir():
            if file_path.is_file() and file_path.suffix in rdf_extensions:
                graph_files.append(file_path.stem)  # stem is filename without extension
        
        return graph_files

    @classmethod
    def __repr__(cls):
        return f"KGManager(graphs_dir={cls.GRAPHS_DIR})"

    @classmethod
    def __str__(cls):
        return f"KGManager(graphs_dir={cls.GRAPHS_DIR})"

# Usage
if __name__ == "__main__":
    # Example usage
    graph = KGManager.get_graph("knowledge_graph.nt")
    # Example of querying the graph
    print(f"Graph contains {len(graph)} triples")

    # Simple SPARQL query to get all subjects and their types
    query = """
    SELECT ?subject ?predicate ?object
    WHERE {
        ?subject ?predicate ?object .
    }
    LIMIT 10
    """

    results = graph.query(query)
    print(results)