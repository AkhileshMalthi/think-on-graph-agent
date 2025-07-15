import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field
import hashlib
from dotenv import load_dotenv
from openai import AzureOpenAI
import spacy
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """
    Minimalist Entity class with flexible metadata
    """

    id: str
    name: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any):
        """
        Add or update metadata flexibly
        """
        self.metadata[key] = value


@dataclass
class Relationship:
    """
    Minimalist Relationship class with flexible metadata
    """

    id: str
    source_id: str
    target_id: str
    type: str = "RELATED_TO"  # Default type
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any):
        """
        Add or update metadata flexibly
        """
        self.metadata[key] = value


class KnowledgeGraphExtractor:
    def __init__(self, model="gpt-35-turbo", similarity_threshold=0.8):
        """
        Initialize Knowledge Graph Extractor with enhanced configuration
        """
        load_dotenv()

        # Azure OpenAI Client Configuration
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
        )
        self.model = model
        self.similarity_threshold = similarity_threshold
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            import subprocess

            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

    def _generate_id(self, name: str, entity_type: str) -> str:
        """
        Generate a consistent, unique ID that is stable across runs

        This function ensures that the same entity name and type always
        produces the same ID, regardless of when or where the code runs.
        """
        # Create a normalized version of the name and type for consistent hashing
        normalized_name = name.lower().strip()
        normalized_type = entity_type.lower().strip()

        # Generate a hash that will be consistent across runs
        hash_input = f"{normalized_name}_{normalized_type}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def preprocess_entities(self, text: str) -> List[Dict]:
        """
        Extract entities using spaCy with minimal preprocessing
        """
        doc = self.nlp(text)

        spacy_entities = []
        seen_entities = set()

        for ent in doc.ents:
            # Skip purely numeric entities
            if ent.text.strip().isdigit():
                continue

            if ent.text.lower() not in seen_entities:
                entity_dict = {
                    "name": ent.text,
                    "type": ent.label_,
                    "metadata": {},
                }
                spacy_entities.append(entity_dict)
                seen_entities.add(ent.text.lower())

        return spacy_entities

    def R(self, text: str, spacy_entities: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Enhanced extraction method with focus on meaningful entities for Neo4j mapping
        Using the specified JSON schema
        """
        try:
            # Prepare system message with spaCy entities
            entities_str = "\n".join([f"- {entity['name']} (Type: {entity['type']})" for entity in spacy_entities])

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert knowledge graph extractor optimized for Neo4j database mapping.
                        Your task is to extract meaningful, well-defined entities and relationships that can be effectively
                        stored and queried in a Neo4j graph database.""",
                    },
                    {
                        "role": "user",
                        "content": f"""Extract a knowledge graph with database-friendly entities and relationships:

PRE-EXTRACTED ENTITIES:
{entities_str}

EXTRACTION GUIDELINES:
1. ENTITY EXTRACTION RULES:
   - Avoid extracting purely numeric values as standalone entities
   - Consolidate numeric information as attributes of entities
   - Ensure entity names are normalized for consistent database mapping
   - Extract domain-specific entities relevant to the context

2. RELATIONSHIP EXTRACTION RULES:
   - Ensure relationships are directional and semantically meaningful
   - Prefer specific relationship types over generic ones
   - Include relationship strength when possible

3. METADATA EXTRACTION RULES:
   - Include meaningful descriptions that add context
   - IMPORTANT: Store all numeric values in the "attributes" section of metadata
   - Focus on extracting quantitative attributes when available

- Include:
attributes (if applicable) otherwise dont include this key value

TEXT:
{text}

JSON FORMAT:
{{
    "entities": [{{
        "name": "Entity Name",
        "type": "Entity Type",
        "metadata": {{
            "description": "Comprehensive explanation",
            "attributes": {{"key": numeric_value}}
        }}
    }}],
    "relationships": [{{
        "source_name": "Source Entity",
        "target_name": "Target Entity",
        "type": ["Relationship Type"],
        "metadata": {{
            "description": "Relationship context and any relevant insights",
            "strength": 0-1
        }}
    }}]
}}

IMPORTANT:
- Focus on extracting meaningful entities for database queries
- Place ALL numeric values in the "attributes" section of entity metadata
- Return relationship types as an array with a single string element
- Avoid extracting standalone numbers as entities
- Ensure consistency in entity and relationship naming
""",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"Extraction Error: {e}")
            return {"entities": spacy_entities, "relationships": []}

    def P(self, raw_data: Dict) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Process and standardize extracted data
        """
        processed = {"entities": [], "relationships": []}

        # Process Entities
        for entity in raw_data.get("entities", []):
            # Skip purely numeric entities
            if entity.get("name", "").strip().isdigit():
                continue

            entity_id = self._generate_id(entity.get("name", ""), entity.get("type", "UNKNOWN"))
            processed_entity = Entity(
                id=entity_id,
                name=entity.get("name", ""),
                type=entity.get("type", "UNKNOWN"),
                metadata=entity.get("metadata", {}),
            )
            processed["entities"].append(processed_entity)

        # Process Relationships
        for rel in raw_data.get("relationships", []):
            source_entity = next(
                (e for e in processed["entities"] if e.name == rel.get("source_name")),
                None,
            )
            target_entity = next(
                (e for e in processed["entities"] if e.name == rel.get("target_name")),
                None,
            )

            if source_entity and target_entity:
                # Handle relationship type as a string
                rel_type = rel.get("type", ["RELATED_TO"])
                # Extract the first element if it's a list
                rel_type_str = rel_type[0] if isinstance(rel_type, list) and rel_type else "RELATED_TO"

                processed_rel = Relationship(
                    id=self._generate_id(
                        f"{source_entity.name}_{target_entity.name}",
                        "RELATIONSHIP",
                    ),
                    source_id=source_entity.id,
                    target_id=target_entity.id,
                    type=rel_type_str,
                    metadata=rel.get("metadata", {}),
                )
                processed["relationships"].append(processed_rel)

        return processed

    def D(self, processed_data: Dict) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Deduplicate and merge entities and relationships
        """
        entity_map = {}
        relationship_map = {}

        # Entity Deduplication
        for entity in processed_data.get("entities", []):
            existing_entity = self._find_similar_entity(entity, entity_map.values())

            if existing_entity:
                merged_entity = self._merge_entities(existing_entity, entity)
                entity_map[merged_entity.id] = merged_entity
            else:
                entity_map[entity.id] = entity

        # Relationship Deduplication
        for relationship in processed_data.get("relationships", []):
            existing_rel = self._find_similar_relationship(relationship, relationship_map.values())

            if existing_rel:
                merged_rel = self._merge_relationships(existing_rel, relationship)
                relationship_map[merged_rel.id] = merged_rel
            else:
                relationship_map[relationship.id] = relationship

        return {
            "entities": list(entity_map.values()),
            "relationships": list(relationship_map.values()),
        }

    def _find_similar_entity(self, entity: Entity, existing_entities: List[Entity]) -> Optional[Entity]:
        """
        Find a similar entity using fuzzy matching
        """
        for existing in existing_entities:
            name_similarity = fuzz.ratio(entity.name.lower(), existing.name.lower())
            type_match = entity.type == existing.type

            if name_similarity >= self.similarity_threshold * 100 and type_match:
                return existing
        return None

    def _find_similar_relationship(
        self,
        relationship: Relationship,
        existing_relationships: List[Relationship],
    ) -> Optional[Relationship]:
        """
        Find a similar relationship
        """
        for existing in existing_relationships:
            source_match = relationship.source_id == existing.source_id
            target_match = relationship.target_id == existing.target_id
            type_match = relationship.type == existing.type

            if source_match and target_match and type_match:
                return existing
        return None

    def _merge_entities(self, entity1: Entity, entity2: Entity) -> Entity:
        """
        Merge two similar entities
        """
        merged_metadata = {**entity1.metadata, **entity2.metadata}

        # If both have attributes, merge them
        if "attributes" in entity1.metadata and "attributes" in entity2.metadata:
            merged_metadata["attributes"] = {
                **entity1.metadata["attributes"],
                **entity2.metadata["attributes"],
            }

        return Entity(
            id=entity1.id,
            name=entity1.name,
            type=entity1.type,
            metadata=merged_metadata,
        )

    def _merge_relationships(self, rel1: Relationship, rel2: Relationship) -> Relationship:
        """
        Merge two similar relationships
        """
        merged_metadata = {**rel1.metadata, **rel2.metadata}

        return Relationship(
            id=rel1.id,
            source_id=rel1.source_id,
            target_id=rel1.target_id,
            type=rel1.type,
            metadata=merged_metadata,
        )

    def extract_knowledge_graph(self, texts: List[str]) -> Dict:
        """
        Comprehensive knowledge graph extraction pipeline
        """
        comprehensive_graph = {"entities": [], "relationships": []}

        for text in texts:
            spacy_entities = self.preprocess_entities(text)
            raw_graph = self.R(text, spacy_entities)
            processed_graph = self.P(raw_graph)
            deduped_graph = self.D(processed_graph)

            comprehensive_graph["entities"].extend(deduped_graph["entities"])
            comprehensive_graph["relationships"].extend(deduped_graph["relationships"])

        # Final deduplication across all texts
        final_deduped_graph = self.D(comprehensive_graph)
        return final_deduped_graph

    def to_dict(self, graph):
        """
        Convert graph to a serializable dictionary
        """
        return {
            "entities": [asdict(entity) for entity in graph["entities"]],
            "relationships": [asdict(relationship) for relationship in graph["relationships"]],
        }


def main():
    extractor = KnowledgeGraphExtractor()

    texts = [
        "Sarah is a professor at University A with 100000 students. University A is a leading institution in New York. Sarah specializes in Artificial Intelligence and collaborates with researchers at University B."
    ]
    kg = extractor.extract_knowledge_graph(texts)

    # Save to file
    with open("knowledge_graph2.json", "w") as f:
        json.dump(extractor.to_dict(kg), indent=2, fp=f)

    print(json.dumps(extractor.to_dict(kg), indent=2))


if __name__ == "__main__":
    main()
