from typing import List, Dict, Any

def format_relations(relations: List[Dict[str, Any]]) -> str:
    """
    Formats a list of relation dictionaries into a human-readable string representation.
    Each relation is formatted as a bullet point with type, source, and target information.
    
    Args:
        relations (List[Dict[str, Any]]): List of relation dictionaries where each dictionary
            must contain 'type', 'source_id', and 'target_id' keys
    
    Returns:
        str: A formatted string with each relation on a new line
        
    Example:
        Input: [
            {'type': 'contains', 'source_id': 'A1', 'target_id': 'B2'},
            {'type': 'connects', 'source_id': 'B2', 'target_id': 'C3'}
        ]
        Output:
        "- contains from A1 to B2
         - connects from B2 to C3"
    """
    return "\n".join([
        f"- {rel['type']} from {rel['source_id']} to {rel['target_id']}"
        for rel in relations
    ])

def format_path(path):
    """
    Formats a single path (either a dictionary or list of dictionaries).
    """
    if isinstance(path, dict):
        return f"{path['subject']} -[{path['predicate']}]-> {path['object']}"
    else:
        return " -> ".join([step['predicate'] for step in path])

def format_paths(paths):
    """
    Formats multiple paths for display.
    """
    if not paths:
        return "No paths found"
    
    formatted = []
    for i, path in enumerate(paths):
        if isinstance(path, dict):
            formatted.append(f"Path {i+1}: {format_path(path)}")
        elif isinstance(path, list):
            formatted.append(f"Path {i+1}: {format_path(path)}")
        else:
            formatted.append(f"Path {i+1}: Invalid path format")
            
    return "\n".join(formatted)

def format_relations_for_pruning(relations: List[Dict[str, Any]]) -> str:
    """
    Formats relations specifically for the pruning evaluation process.
    Creates a simplified view focusing on relation type and target.
    
    Args:
        relations (List[Dict[str, Any]]): List of relation dictionaries where each dictionary
            must contain 'type' and 'target_id' keys
    
    Returns:
        str: A formatted string with simplified relation representation
        
    Example:
        Input: [
            {'type': 'contains', 'target_id': 'B2'},
            {'type': 'connects', 'target_id': 'C3'}
        ]
        Output:
        "- contains to B2
         - connects to C3"
    """
    return "\n".join([
        f"- {rel['type']} to {rel['target_id']}" for rel in relations
    ])

def format_triple(triple):
    """Format a single triple into a string."""
    return f"{triple['subject']} -[{triple['predicate']}]-> {triple['object']}"

def format_path_string(path):
    """
    Formats a path or triple into a string representation.
    
    Args:
        path: Either a single triple dict or a list of triples
    
    Returns:
        str: Formatted string representation of the path
    """
    if isinstance(path, dict):
        # Single triple
        return format_triple(path)
    elif isinstance(path, list):
        # List of triples
        return " -> ".join([format_triple(triple) for triple in path])
    else:
        raise ValueError("Path must be either a triple dict or a list of triples")

def format_relations_string(relations):
    """
    Formats a list of relations into a string representation.
    
    Args:
        relations: List of relation dictionaries
        
    Returns:
        str: Formatted string representation of relations
    """
    formatted_relations = []
    for rel in relations:
        rel_str = f"ID: {rel['id']}\n"
        rel_str += f"Type: {rel['type']}\n"
        rel_str += f"Target: {rel.get('target_name', 'Unknown')}\n"
        if rel.get('metadata'):
            rel_str += "Metadata:\n"
            rel_str += "\n".join([f"  {k}: {v}" for k, v in rel['metadata'].items()])
        formatted_relations.append(rel_str)
    return "\n\n".join(formatted_relations)
