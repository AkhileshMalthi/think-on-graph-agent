import json
import re
import logging
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
import networkx as nx
import spacy
from groq import Groq
from dotenv import load_dotenv
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGraphExtractor:
    # Predefined Fixed Schema (remains the same)
    ENTITY_SCHEMA = {
        "id": str,             # Unique identifier
        "name": str,           # Primary name
        "type": str,           # Entity type (e.g., PERSON, ORGANIZATION, LOCATION)
        "aliases": List[str],  # Alternative names
        "description": str,    # Descriptive context
        "attributes": Dict     # Additional metadata
    }

    RELATIONSHIP_SCHEMA = {
        "id": str,             # Unique relationship identifier
        "source_id": str,      # Source entity ID
        "target_id": str,      # Target entity ID
        "types": List[str],    # Relationship types (e.g., COLLABORATES_WITH, LOCATED_IN)
        "strength": float,     # Relationship strength (0-1)
        "description": str,    # Relationship context
    }

    def __init__(self, model="llama3-70b-8192", similarity_threshold=0.8):
        """
        Initialize Knowledge Graph Extractor with spaCy entity preprocessing
        
        :param model: Groq model to use
        :param similarity_threshold: Threshold for entity/relationship matching
        """
        load_dotenv()
        
        # Groq Client Configuration
        self.client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.model = model
        
        # Configuration
        self.similarity_threshold = similarity_threshold
        
        # Graph Storage
        self.entity_map: Dict[str, Dict] = {}
        self.relationship_map: Dict[str, Dict] = {}
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_sci_scibert")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Attempting to download spaCy biomedical model...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_sci_sm"])
            self.nlp = spacy.load("en_core_sci_sm")
    def preprocess_entities(self, text: str) -> List[Dict]:
        """
        Extract entities using spaCy biomedical model
        
        :param text: Input text
        :return: List of extracted entities
        """
        doc = self.nlp(text)
        
        # Extract unique entities
        spacy_entities = []
        seen_entities = set()
        
        for ent in doc.ents:
            # Remove duplicate entities
            if ent.text.lower() not in seen_entities:
                entity_dict = {
                    "name": ent.text,
                    "type": ent.label_,
                    "aliases": [],  # Can be populated later
                    "description": "",  # To be filled by LLM
                    "attributes": {}  # To be populated later
                }
                spacy_entities.append(entity_dict)
                seen_entities.add(ent.text.lower())
        
        return spacy_entities
    def _generate_id(self, name: str, entity_type: str) -> str:
        """
        Generate a consistent, unique ID for an entity.
        
        :param name: Entity name
        :param entity_type: Entity type
        :return: Unique identifier
        """
        return hashlib.md5(f"{name}_{entity_type}".encode()).hexdigest()
    def R(self, text: str, spacy_entities: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Modified extraction method to incorporate spaCy-extracted entities
        
        :param text: Input text
        :param spacy_entities: Entities extracted by spaCy
        :return: Knowledge graph data
        """
        try:
            # Prepare system message with spaCy entities
            entities_str = "\n".join([
                f"- {entity['name']} (Type: {entity['type']})" 
                for entity in spacy_entities
            ])
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"""You are an expert knowledge graph extractor. 
                        The following entities have been pre-extracted by spaCy:
                        {entities_str}
                        
                        Your task is to:
                        1. Validate and enrich these extracted entities keep only necessary entities and work on them 
                        2. Establish meaningful relationships between them
                        3. Add descriptions and attributes based on the text context"""
                    },
                    {
                        "role": "user", 
                        "content": f"""You are an expert knowledge graph extractor. From the pre-extracted spaCy entities, identify and work ONLY with the most contextually significant and meaningful entities.

PRE-EXTRACTED ENTITIES:
{entities_str}

SELECTION CRITERIA:
1. Choose ONLY entities that:
   - Have substantial context in the text
   - Are central to the main theme or narrative
   - Provide meaningful insights
2. Eliminate entities that are:
   - Vague or too generic
   - Lack significant context
   - Appear peripheral to the main discussion

TASK:
- Carefully select the most relevant entities
- Provide detailed descriptions
- Establish meaningful relationships between selected entities

TEXT:
{text}

JSON FORMAT:
{{
    "entities": [{{
        "name": "Contextually significant entity",
        "type": "Entity type",
        "aliases": ["Alternative mentions used in retreival stage"],
        "description": "Comprehensive description highlighting entity's importance",
        "attributes": {{
                "key": "value from text or inferred context"
        }}
    }}],
    "relationships": [{{
        "source_name": "Selected entity",
        "target_name": "Selected entity",
        "types": ["Relationship type"],
        "strength": 0-1,
        "description": "Meaningful relationship context"
    }}]
}}"""
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=1024
            )

            # Parse and validate the response
            content = response.choices[0].message.content
            print("Raw API Response Content:", content)

            parsed_data = json.loads(content)
            print("Raw API Response Content after json is:", parsed_data)


# Parse and validate the response
            content = response.choices[0].message.content
            print("Raw API Response Content (string):", content)

            # Add prints to see exact parsing
            print("Raw content type:", type(content))
            print("Raw content length:", len(content))

            # Try parsing with some extra checks
            try:
                parsed_data = json.loads(content)
                print("Parsing successful")
            except json.JSONDecodeError as e:
                print("JSON Parsing Error:", e)
                print("Problematic content around error:", content[max(0, e.pos-50):min(len(content), e.pos+50)])
                raise

            print("Raw API Response Content after json is:", parsed_data)

            return parsed_data

        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            # Fallback to spaCy entities if LLM extraction fails
            return {
                "entities": spacy_entities,
                "relationships": []
            }


    def P(self, raw_data: Dict) -> Dict:
        """
        Process and standardize extracted data to fixed schema
        
        :param raw_data: Raw extraction from R()
        :return: Processed data with fixed schema
        """
        processed = {
            "entities": [],
            "relationships": []
        }
        
        # Process Entities
        for entity in raw_data.get("entities", []):
            entity_id = self._generate_id(
                entity.get("name", ""), 
                entity.get("type", "UNKNOWN")
            )
            processed_entity = {
                "id": entity_id,
                "name": entity.get("name", ""),
                "type": entity.get("type", "UNKNOWN"),
                "aliases": entity.get("aliases", []),
                "description": entity.get("description", ""),
                "attributes": entity.get("attributes", {})
            }
            processed["entities"].append(processed_entity)
        
        # Process Relationships
        for rel in raw_data.get("relationships", []):
            source_entity = next(
                (e for e in processed["entities"] if e["name"] == rel.get("source_name")), 
                None
            )
            target_entity = next(
                (e for e in processed["entities"] if e["name"] == rel.get("target_name")), 
                None
            )
            
            if source_entity and target_entity:
                processed_rel = {
                    "id": self._generate_id(
                        f"{source_entity['name']}_{target_entity['name']}", 
                        "RELATIONSHIP"
                    ),
                    "source_id": source_entity["id"],
                    "target_id": target_entity["id"],
                    "types": rel.get("types", []),
                    "strength": float(rel.get("strength", 0.5)),
                    "description": rel.get("description", "")
                }
                processed["relationships"].append(processed_rel)
        
        return processed

    def D(self, processed_data: Dict) -> Dict:
        """
        Deduplicate and merge entities and relationships
        
        :param processed_data: Processed data from P()
        :return: Deduplicated graph data
        """
        # Entity Deduplication
        entity_map = {}
        for entity in processed_data.get("entities", []):
            # Use fuzzy matching for entity deduplication
            existing_entity = self._find_similar_entity(entity, entity_map.values())
            
            if existing_entity:
                # Merge entities if similar
                merged_entity = self._merge_entities(existing_entity, entity)
                entity_map[merged_entity["id"]] = merged_entity
            else:
                entity_map[entity["id"]] = entity
        
        # Relationship Deduplication
        relationship_map = {}
        for relationship in processed_data.get("relationships", []):
            # Deduplicate based on source, target, and relationship types
            existing_rel = self._find_similar_relationship(relationship, relationship_map.values())
            
            if existing_rel:
                # Merge relationships if similar
                merged_rel = self._merge_relationships(existing_rel, relationship)
                relationship_map[merged_rel["id"]] = merged_rel
            else:
                relationship_map[relationship["id"]] = relationship
        
        return {
            "entities": list(entity_map.values()),
            "relationships": list(relationship_map.values())
        }

    def _find_similar_entity(self, entity: Dict, existing_entities: List[Dict]) -> Optional[Dict]:
        """
        Find a similar entity using name and type similarity
        
        :param entity: Entity to match
        :param existing_entities: List of existing entities
        :return: Similar entity or None
        """
        for existing in existing_entities:
            name_similarity = fuzz.ratio(entity["name"].lower(), existing["name"].lower())
            type_match = entity["type"] == existing["type"]
            
            if name_similarity >= self.similarity_threshold * 100 and type_match:
                return existing
        return None

    def _find_similar_relationship(self, relationship: Dict, existing_relationships: List[Dict]) -> Optional[Dict]:
        """
        Find a similar relationship
        
        :param relationship: Relationship to match
        :param existing_relationships: List of existing relationships
        :return: Similar relationship or None
        """
        for existing in existing_relationships:
            source_match = relationship["source_id"] == existing["source_id"]
            target_match = relationship["target_id"] == existing["target_id"]
            type_overlap = bool(set(relationship["types"]) & set(existing["types"]))
            
            if source_match and target_match and type_overlap:
                return existing
        return None

    def _merge_entities(self, entity1: Dict, entity2: Dict) -> Dict:
        """
        Intelligently merge two similar entities
        
        :param entity1: First entity
        :param entity2: Second entity
        :return: Merged entity
        """
        return {
            "id": entity1["id"],
            "name": entity1["name"],
            "type": entity1["type"],
            "aliases": list(set(entity1.get("aliases", []) + entity2.get("aliases", []))),
            "description": entity1.get("description", "") or entity2.get("description", ""),
            "attributes": {**entity1.get("attributes", {}), **entity2.get("attributes", {})}
        }

    def _merge_relationships(self, rel1: Dict, rel2: Dict) -> Dict:
        """
        Intelligently merge two similar relationships
        
        :param rel1: First relationship
        :param rel2: Second relationship
        :return: Merged relationship
        """
        return {
            "id": rel1["id"],
            "source_id": rel1["source_id"],
            "target_id": rel1["target_id"],
            "types": list(set(rel1.get("types", []) + rel2.get("types", []))),
            "strength": max(rel1.get("strength", 0), rel2.get("strength", 0)),
            "description": f"{rel1.get('description', '')} | {rel2.get('description', '')}".strip(" |")
        }

    def extract_knowledge_graph(self, texts: List[str]) -> Dict:
        """
        Comprehensive knowledge graph extraction pipeline with spaCy preprocessing
        
        :param texts: List of input texts
        :return: Comprehensive knowledge graph
        """
        comprehensive_graph = {
            "entities": [],
            "relationships": []
        }
        
        for text in texts:
            # Preprocess with spaCy first
            spacy_entities = self.preprocess_entities(text)
            
            # Full extraction pipeline with spaCy entities
            raw_graph = self.R(text, spacy_entities)
            processed_graph = self.P(raw_graph)
            deduped_graph = self.D(processed_graph)
            
            # Merge with comprehensive graph
            comprehensive_graph["entities"].extend(deduped_graph["entities"])
            comprehensive_graph["relationships"].extend(deduped_graph["relationships"])
        
        return comprehensive_graph

def main():
    # Ensure spaCy model is installed
    try:
        import spacy
        spacy.load("en_core_sci_sm")
    except Exception:
        import subprocess
        # subprocess.run(["python", "-m", "spacy", "download", "en_core_sci_sm"])

    extractor = KnowledgeGraphExtractor()
    
    texts = ["Sarah is a professor at University A. University A is a leading institution in New York. Sarah specializes in Artificial Intelligence and collaborates with researchers at University B."
]
    kg = extractor.extract_knowledge_graph(texts)
    print(json.dumps(kg, indent=2))

if __name__ == "__main__":
    main()