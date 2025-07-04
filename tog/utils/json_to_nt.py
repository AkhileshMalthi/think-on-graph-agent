import json
import hashlib
import re
import os
from typing import Dict, List, Any

def clean_text(text: str) -> str:
    """Clean text to make it suitable for URI/literal in N-Triples format."""
    if text is None:
        return ""
    # Remove special characters that might cause issues in URIs
    text = re.sub(r'[^\w\s\-]', '', text)
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    return text

def generate_uri(entity_id: str, base_uri: str = "http://example.org/entity/") -> str:
    """Generate a URI for an entity based on its ID."""
    return f"{base_uri}{entity_id}"

def json_to_nt(json_file_path: str, output_file_path: str = None) -> str:
    """
    Convert a knowledge graph JSON file to N-Triples format.
    
    Args:
        json_file_path: Path to the JSON file containing the knowledge graph.
        output_file_path: Path where the N-Triples file will be saved. If None, returns the N-Triples content.
        
    Returns:
        If output_file_path is None, returns the N-Triples content as a string.
        Otherwise, returns the path to the saved N-Triples file.
    """
    # Load the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        kg_data = json.load(f)
    
    # Create a dictionary to map entity IDs to their information
    entity_map = {entity["id"]: entity for entity in kg_data.get("entities", []) if "id" in entity}
    
    # Base URIs for different components
    base_entity_uri = "http://example.org/entity/"
    base_property_uri = "http://example.org/property/"
    
    triples = []
    
    # Process entities
    for entity in kg_data.get("entities", []):
        if "id" not in entity:
            continue
            
        entity_uri = generate_uri(entity["id"])
        
        # Add triples for entity properties
        if "name" in entity:
            triples.append(f'<{entity_uri}> <{base_property_uri}name> "{entity["name"]}" .')
        
        if "type" in entity:
            triples.append(f'<{entity_uri}> <{base_property_uri}type> "{entity["type"]}" .')
        
        if "description" in entity:
            # Escape quotes in description
            desc = entity["description"].replace('"', '\\"')
            triples.append(f'<{entity_uri}> <{base_property_uri}description> "{desc}" .')
        
        # Handle aliases
        if "aliases" in entity and isinstance(entity["aliases"], list):
            for alias in entity["aliases"]:
                if alias:  # Skip empty aliases
                    triples.append(f'<{entity_uri}> <{base_property_uri}alias> "{alias}" .')
    
    # Process relationships
    for i, rel in enumerate(kg_data.get("relationships", [])):
        if "description" not in rel:
            continue
            
        # Parse the relationship description to extract subject, predicate, and object
        desc = rel["description"]
        parts = desc.strip().split(' ', 2)
        
        if len(parts) < 3:
            continue
        
        subj_text, pred_text, obj_text = parts[0], ' '.join(parts[1:-1]), parts[-1].rstrip('.')
        
        # Find the entity with the matching name for subject
        subj_entity = next((e for e in kg_data.get("entities", []) 
                            if "name" in e and e["name"].lower() == subj_text.lower()), None)
        
        # Find the entity with the matching name for object
        obj_entity = next((e for e in kg_data.get("entities", []) 
                          if "name" in e and e["name"].lower() == obj_text.lower()), None)
        
        if subj_entity and obj_entity:
            subj_uri = generate_uri(subj_entity["id"])
            obj_uri = generate_uri(obj_entity["id"])
            pred_uri = f"{base_property_uri}{clean_text(pred_text)}"
            
            triples.append(f'<{subj_uri}> <{pred_uri}> <{obj_uri}> .')
    
    # Join all triples into a single string
    nt_content = '\n'.join(triples)
    
    # Save to file if output_file_path is provided
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(nt_content)
        return output_file_path
    
    # Otherwise return the content
    return nt_content

def main():
    """Main function to demonstrate usage."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kg_path = os.path.join(script_dir, '..', '..', 'knowledge_graph.json')
    output_path = os.path.join(script_dir, '..', '..', 'knowledge_graph.nt')
    
    result = json_to_nt(kg_path, output_path)
    print(f"N-Triples file created at: {result}")

# if __name__ == "__main__":
#     main()