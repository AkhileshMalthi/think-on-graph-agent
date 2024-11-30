GRAPH_FIELD_SEP = "<SEP>"

# Dictionary to hold all the prompts required for the KG
PROMPTS = {}

# System prompt for extracting entities and relationships among them
PROMPTS['system_prompt'] = """
You are an expert entity and relationship extraction assistant. 
Extract structured information from text with precision:
- Identify clear, distinct entities
- Classify entities by type
- Describe relationships between entities
- Provide a JSON response following this exact structure:
  {
    "entities": [
      {
        "name": "Complete Entity Name",
        "type": "Entity Type (Person/Organization/Location/etc)",
        "description": "Concise entity description"
      }
    ],
    "relationships": [
      {
        "source": "Source Entity Name",
        "target": "Target Entity Name",
        "description": "Relationship explanation", 
        "relationship_types": ["list", "of", "relationship", "types"],
        "strength": "weak/medium/strong"
      }
    ]
  }
"""
# Define types of entities for extraction
PROMPTS["entitiy_types"] = ["organization", "person", "geo", "event"]

# Extraction prompt to extract entities 
PROMPTS["entity_extraction"] = """
Task: Extract detailed entities and relationships from the text.

Text: {input_text}

Instructions:
1. Identify all named entities
2. Classify each entity's type
3. Describe inter-entity relationships
4. Return a well-structured JSON response
5. If no clear entities/relationships exist, return empty lists
"""

PROMPTS['extraction_test_prompts'] = [
        "Barack Obama was the 44th President of the United States and Michelle Obama is an author.",
        "The company Google was founded by Larry Page and Sergey Brin in California.",
        "Some texts might not have clear entities."
    ]