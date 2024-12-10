import json
import re
import logging
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
import networkx as nx
# With these
from openai import AzureOpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeGraphExtractor:
    # Predefined Fixed Schema
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

    def __init__(self, model="gpt-35-turbo", similarity_threshold=0.8):
        """
        Initialize Knowledge Graph Extractor with fixed schema support.
        
        :param model: Azure OpenAI model to use
        :param similarity_threshold: Threshold for entity/relationship matching
        """
        load_dotenv()
        
        # Azure OpenAI Client Configuration
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01"
        )
        self.model = model
        
        # Configuration
        self.similarity_threshold = similarity_threshold
        
        # Graph Storage
        self.entity_map: Dict[str, Dict] = {}
        self.relationship_map: Dict[str, Dict] = {}

    def _generate_id(self, name: str, entity_type: str) -> str:
        """
        Generate a consistent, unique ID for an entity.
        
        :param name: Entity name
        :param entity_type: Entity type
        :return: Unique identifier
        """
        import hashlib
        return hashlib.md5(f"{name}_{entity_type}".encode()).hexdigest()

    def R(self, text: str) -> Dict[str, List[Dict]]:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system", 
                        "content": "Extract entities and relationships using the predefined schema, with intelligent attribute generation."
                    },
                    {
                        "role": "user", 
                        "content": f"""
                        Extract knowledge graph from text:
                        
                        {text}
                        
                        Output JSON with:
                        - Unique, descriptive entities
                        - Clear inter-entity relationships
                        - Rich, context-driven attributes for both entities and relationships
                        
                        JSON Structure (UNCHANGED):
                        {{
                            "entities": [{{
                                "name": "Exact Name",
                                "type": "ENTITY_TYPE",
                                "aliases": ["Alternative Names"],
                                "description": "Contextual Description",
                                "attributes": "Dynamically derived, meaningful metadata"
                            }}],
                            "relationships": [{{
                                "source_name": "Source Entity",
                                "target_name": "Target Entity",
                                "types": ["Relationship Types"],
                                "strength": 0-1,
                                "description": "Relationship Context"
                            }}]
                        }}

                        Attribute Generation Guidelines:
                        1. Derive attributes directly from text context
                        2. Provide unique, information-rich metadata
                        3. Use domain-specific insights
                        4. Ensure attributes enhance understanding
                        """
                    }
                ],
                temperature=0.4,
                max_tokens=1024
            )
            
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return {"entities": [], "relationships": []}

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
        Comprehensive knowledge graph extraction pipeline
        
        :param texts: List of input texts
        :return: Comprehensive knowledge graph
        """
        comprehensive_graph = {
            "entities": [],
            "relationships": []
        }
        
        for text in texts:
            # Full extraction pipeline
            raw_graph = self.R(text)
            processed_graph = self.P(raw_graph)
            deduped_graph = self.D(processed_graph)
            
            # Merge with comprehensive graph
            comprehensive_graph["entities"].extend(deduped_graph["entities"])
            comprehensive_graph["relationships"].extend(deduped_graph["relationships"])
        
        return comprehensive_graph

def main():
    extractor = KnowledgeGraphExtractor()
    
    texts = [
            "Analyze the role of insulin therapy in managing type 2 diabetes in patients with cardiovascular complications."
            ]
    
    kg = extractor.extract_knowledge_graph(texts)
    print(json.dumps(kg, indent=2))

if __name__ == "__main__":
    main()