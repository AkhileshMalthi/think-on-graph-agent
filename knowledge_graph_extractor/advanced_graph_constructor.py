import json
import re
import logging
import os
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from fuzzywuzzy import fuzz
import hashlib
from dotenv import load_dotenv
from openai import AzureOpenAI

# LangChain imports
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv()
@dataclass
class Entity:
    """
    Enhanced Entity class with flexible metadata
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
    Enhanced Relationship class with flexible metadata
    """
    id: str
    source_id: str
    target_id: str
    type: str = "RELATED_TO"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any):
        """
        Add or update metadata flexibly
        """
        self.metadata[key] = value

class KnowledgeGraphExtractor:
    def __init__(self, model="gpt-35-turbo", similarity_threshold=0.8, allowed_nodes=None, allowed_relationships=None):
        """
        Initialize Enhanced Knowledge Graph Extractor
        """
        load_dotenv()
        
        # Azure OpenAI Client Configuration
        self.azure_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-01-01-preview",
            azure_deployment=model
        )
        self.model = model
        self.similarity_threshold = similarity_threshold
        
        # Initialize LangChain Azure OpenAI for LLMGraphTransformer
        self.langchain_llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-01-01-preview",
            azure_deployment=model,
            temperature=0
        )
        
        # Initialize LLMGraphTransformer with optional constraints
        if allowed_nodes and allowed_relationships:
            self.graph_transformer = LLMGraphTransformer(
                llm=self.langchain_llm,
                allowed_nodes=allowed_nodes,
                allowed_relationships=allowed_relationships
            )
        elif allowed_nodes:
            self.graph_transformer = LLMGraphTransformer(
                llm=self.langchain_llm,
                allowed_nodes=allowed_nodes
            )
        else:
            self.graph_transformer = LLMGraphTransformer(llm=self.langchain_llm)

    def _generate_id(self, name: str, entity_type: str) -> str:
        """
        Generate a consistent, unique ID that is stable across runs
        """
        normalized_name = name.lower().strip()
        normalized_type = entity_type.lower().strip()
        hash_input = f"{normalized_name}_{normalized_type}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    async def extract_entities_and_relationships(self, text: str) -> Dict[str, List]:
        """
        Extract entities and relationships using LLMGraphTransformer
        """
        try:
            documents = [Document(page_content=text)]
            graph_documents = await self.graph_transformer.aconvert_to_graph_documents(documents)
            
            if not graph_documents:
                return {"entities": [], "relationships": []}
            
            graph_doc = graph_documents[0]
            
            # Convert to our format
            entities = []
            for node in graph_doc.nodes:
                entities.append({
                    "name": node.id,
                    "type": node.type if hasattr(node, 'type') else "UNKNOWN"
                })
            
            relationships = []
            for rel in graph_doc.relationships:
                relationships.append({
                    "source_name": rel.source.id,
                    "target_name": rel.target.id,
                    "type": rel.type
                })
            
            return {
                "entities": entities,
                "relationships": relationships
            }
        
        except Exception as e:
            logger.error(f"Entity/Relationship extraction error: {e}")
            return {"entities": [], "relationships": []}

    def enhance_entities_with_descriptions(self, text: str, entities: List[Dict]) -> List[Dict]:
        """
        Enhance entities with descriptions and attributes using Azure OpenAI
        """
        if not entities:
            return entities
        
        try:
            entities_str = "\n".join([
                f"- {entity['name']} (Type: {entity['type']})" 
                for entity in entities
            ])
            
            response = self.azure_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at analyzing text and providing comprehensive descriptions and attributes for entities.
                        Your task is to enhance the given entities with detailed descriptions and extract any numerical or important attributes."""
                    },
                    {
                        "role": "user",
                        "content": f"""Given the following text and extracted entities, provide enhanced descriptions and attributes for each entity.

TEXT:
{text}

ENTITIES TO ENHANCE:
{entities_str}

ENHANCEMENT GUIDELINES:
1. Provide a comprehensive description for each entity based on the context in the text
2. Extract any numerical attributes (dates, quantities, measurements, etc.)
3. Include other important attributes that add context
4. If an entity is not mentioned in the text, provide a brief description based on the entity type
5. Focus on information that would be valuable for database queries and knowledge representation

JSON FORMAT:
{{
    "enhanced_entities": [{{
        "name": "Entity Name",
        "type": "Entity Type",
        "description": "Comprehensive description based on the text context",
        "attributes": {{
            "key1": "value1",
            "key2": numeric_value,
            "key3": "value3"
        }}
    }}]
}}

IMPORTANT:
- Include ALL entities from the input list
- Place numerical values directly in attributes (not as strings unless they represent text)
- Make descriptions contextual and informative
- If no specific attributes are found, you can omit the attributes field for that entity
"""
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048
            )

            content = response.choices[0].message.content
            enhanced_data = json.loads(content)
            return enhanced_data.get("enhanced_entities", entities)

        except Exception as e:
            logger.error(f"Entity enhancement error: {e}")
            return entities

    def enhance_relationships_with_descriptions(self, text: str, relationships: List[Dict], entities: List[Dict]) -> List[Dict]:
        """
        Enhance relationships with descriptions and metadata using Azure OpenAI
        """
        if not relationships:
            return relationships
        
        try:
            relationships_str = "\n".join([
                f"- {rel['source_name']} --[{rel['type']}]--> {rel['target_name']}" 
                for rel in relationships
            ])
            
            entities_context = "\n".join([
                f"- {entity['name']} (Type: {entity['type']})" 
                for entity in entities
            ])
            
            response = self.azure_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at analyzing relationships between entities and providing meaningful descriptions.
                        Your task is to enhance relationships with contextual descriptions and metadata."""
                    },
                    {
                        "role": "user",
                        "content": f"""Given the following text, entities, and relationships, provide enhanced descriptions for each relationship.

TEXT:
{text}

ENTITIES:
{entities_context}

RELATIONSHIPS TO ENHANCE:
{relationships_str}

ENHANCEMENT GUIDELINES:
1. Provide a description explaining the relationship in the context of the text
2. Include a confidence/strength score (0-1) if applicable
3. Add any relevant metadata that provides context
4. Make descriptions specific to the text content

JSON FORMAT:
{{
    "enhanced_relationships": [{{
        "source_name": "Source Entity",
        "target_name": "Target Entity",
        "type": "Relationship Type",
        "description": "Contextual description of the relationship",
        "strength": 0.8,
        "metadata": {{
            "context": "additional context",
            "evidence": "text evidence for this relationship"
        }}
    }}]
}}

IMPORTANT:
- Include ALL relationships from the input list
- Make descriptions contextual and informative
- Strength should be between 0 and 1
- If no specific metadata is found, you can omit the metadata field
"""
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2048
            )

            content = response.choices[0].message.content
            enhanced_data = json.loads(content)
            return enhanced_data.get("enhanced_relationships", relationships)

        except Exception as e:
            logger.error(f"Relationship enhancement error: {e}")
            return relationships

    def process_enhanced_data(self, enhanced_entities: List[Dict], enhanced_relationships: List[Dict]) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Process enhanced data into our standard format
        """
        processed = {
            "entities": [],
            "relationships": []
        }
        
        # Create entity mapping for relationship processing
        entity_map = {}
        
        # Process Enhanced Entities
        for entity_data in enhanced_entities:
            entity_id = self._generate_id(
                entity_data.get("name", ""), 
                entity_data.get("type", "UNKNOWN")
            )
            
            # Prepare metadata
            metadata = {}
            if "description" in entity_data:
                metadata["description"] = entity_data["description"]
            if "attributes" in entity_data:
                metadata["attributes"] = entity_data["attributes"]
            
            entity = Entity(
                id=entity_id,
                name=entity_data.get("name", ""),
                type=entity_data.get("type", "UNKNOWN"),
                metadata=metadata
            )
            processed["entities"].append(entity)
            entity_map[entity.name] = entity
        
        # Process Enhanced Relationships
        for rel_data in enhanced_relationships:
            source_entity = entity_map.get(rel_data.get("source_name"))
            target_entity = entity_map.get(rel_data.get("target_name"))
            
            if source_entity and target_entity:
                # Prepare metadata
                metadata = {}
                if "description" in rel_data:
                    metadata["description"] = rel_data["description"]
                if "strength" in rel_data:
                    metadata["strength"] = rel_data["strength"]
                if "metadata" in rel_data:
                    metadata.update(rel_data["metadata"])
                
                relationship = Relationship(
                    id=self._generate_id(
                        f"{source_entity.name}_{target_entity.name}", 
                        "RELATIONSHIP"
                    ),
                    source_id=source_entity.id,
                    target_id=target_entity.id,
                    type=rel_data.get("type", "RELATED_TO"),
                    metadata=metadata
                )
                processed["relationships"].append(relationship)
        
        return processed

    def deduplicate_graph(self, processed_data: Dict) -> Dict[str, List[Union[Entity, Relationship]]]:
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
            "relationships": list(relationship_map.values())
        }

    def _find_similar_entity(self, entity: Entity, existing_entities: List[Entity]) -> Optional[Entity]:
        """Find a similar entity using fuzzy matching"""
        for existing in existing_entities:
            name_similarity = fuzz.ratio(entity.name.lower(), existing.name.lower())
            type_match = entity.type == existing.type
            
            if name_similarity >= self.similarity_threshold * 100 and type_match:
                return existing
        return None

    def _find_similar_relationship(self, relationship: Relationship, existing_relationships: List[Relationship]) -> Optional[Relationship]:
        """Find a similar relationship"""
        for existing in existing_relationships:
            source_match = relationship.source_id == existing.source_id
            target_match = relationship.target_id == existing.target_id
            type_match = relationship.type == existing.type
            
            if source_match and target_match and type_match:
                return existing
        return None

    def _merge_entities(self, entity1: Entity, entity2: Entity) -> Entity:
        """Merge two similar entities"""
        merged_metadata = {**entity1.metadata, **entity2.metadata}
        
        # If both have attributes, merge them
        if "attributes" in entity1.metadata and "attributes" in entity2.metadata:
            merged_metadata["attributes"] = {**entity1.metadata["attributes"], **entity2.metadata["attributes"]}
        
        return Entity(
            id=entity1.id,
            name=entity1.name,
            type=entity1.type,
            metadata=merged_metadata
        )

    def _merge_relationships(self, rel1: Relationship, rel2: Relationship) -> Relationship:
        """Merge two similar relationships"""
        merged_metadata = {**rel1.metadata, **rel2.metadata}
        
        return Relationship(
            id=rel1.id,
            source_id=rel1.source_id,
            target_id=rel1.target_id,
            type=rel1.type,
            metadata=merged_metadata
        )

    async def extract_knowledge_graph(self, texts: List[str]) -> Dict:
        """
        Comprehensive knowledge graph extraction pipeline using LLMGraphTransformer + Azure OpenAI enhancement
        """
        comprehensive_graph = {
            "entities": [],
            "relationships": []
        }
        
        for text in texts:
            logger.info(f"Processing text chunk of length: {len(text)}")
            
            # Step 1: Extract entities and relationships using LLMGraphTransformer
            extracted_data = await self.extract_entities_and_relationships(text)
            
            # Step 2: Enhance entities with descriptions and attributes
            enhanced_entities = self.enhance_entities_with_descriptions(
                text, extracted_data["entities"]
            )
            
            # Step 3: Enhance relationships with descriptions and metadata
            enhanced_relationships = self.enhance_relationships_with_descriptions(
                text, extracted_data["relationships"], enhanced_entities
            )
            
            # Step 4: Process enhanced data
            processed_graph = self.process_enhanced_data(enhanced_entities, enhanced_relationships)
            
            # Step 5: Deduplicate within this chunk
            deduped_graph = self.deduplicate_graph(processed_graph)
            
            comprehensive_graph["entities"].extend(deduped_graph["entities"])
            comprehensive_graph["relationships"].extend(deduped_graph["relationships"])
        
        # Final deduplication across all texts
        final_deduped_graph = self.deduplicate_graph(comprehensive_graph)
        return final_deduped_graph

    def to_dict(self, graph):
        """Convert graph to a serializable dictionary"""
        return {
            "entities": [asdict(entity) for entity in graph["entities"]],
            "relationships": [asdict(relationship) for relationship in graph["relationships"]]
        }

# Example usage
async def main():
    # Optional: Define allowed nodes and relationships for more structured extraction
    allowed_nodes = ["Person", "Organization", "Location", "Award", "ResearchField", "Theory", "Concept"]
    allowed_relationships = [
        ("Person", "WORKS_AT", "Organization"),
        ("Person", "LOCATED_IN", "Location"),
        ("Person", "RECEIVED", "Award"),
        ("Person", "RESEARCHES", "ResearchField"),
        ("Person", "DEVELOPED", "Theory"),
        ("Organization", "LOCATED_IN", "Location"),
        ("Theory", "RELATES_TO", "Concept")
    ]
    
    extractor = KnowledgeGraphExtractor(
        allowed_nodes=allowed_nodes,
        allowed_relationships=allowed_relationships
    )
    
    texts = [
        """Although large language models (LLMs) have achieved significant success in various tasks, they often struggle with hallucination problems, especially in scenarios requiring deep and responsible reasoning. These issues could be partially addressed by introducing external knowledge graphs (KG) in LLM reasoning. In this paper, we propose a new LLM-KG integrating paradigm 'LLM ⊗ KG' which treats the LLM as an agent to interactively explore related entities and relations on KGs and perform reasoning based on the retrieved knowledge. We further implement this paradigm by introducing a new approach called Think-on-Graph (ToG), in which the LLM agent iteratively executes beam search on KG, discovers the most promising reasoning paths, and returns the most likely reasoning results. We use a number of well-designed experiments to examine and illustrate the following advantages of ToG: 1) compared with LLMs, ToG has better deep reasoning power; 2) ToG has the ability of knowledge traceability and knowledge correctability by leveraging LLMs reasoning and expert feedback; 3) ToG provides a flexible plugand-play framework for different LLMs, KGs and prompting strategies without any additional training cost; 4) the performance of ToG with small LLM models could exceed large LLM such as GPT-4 in certain scenarios and this reduces the cost of LLM deployment and application. As a training-free method with lower computational cost and better generality, ToG achieves overall SOTA in 6 out of 9 datasets where most previous SOTAs rely on additional training. Our code is publicly available at https://github.com/IDEA-FinAI/ToG ."""
    ]
    
    kg = await extractor.extract_knowledge_graph(texts)
    
    # Save to file
    with open("enhanced_knowledge_graph.json", "w") as f:
        json.dump(extractor.to_dict(kg), indent=2, fp=f)
    
    print(json.dumps(extractor.to_dict(kg), indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())