import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from fuzzywuzzy import fuzz

import hashlib
from dotenv import load_dotenv
import asyncio
import spacy

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """
    Minimalist Entity class with flexible metadata including chunk tracking
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

    def add_chunk_info(self, chunk_id: str, section_id: str):
        """
        Add chunk and section information to metadata
        """
        if "chunk_ids" not in self.metadata:
            self.metadata["chunk_ids"] = []
        if "section_ids" not in self.metadata:
            self.metadata["section_ids"] = []

        if chunk_id not in self.metadata["chunk_ids"]:
            self.metadata["chunk_ids"].append(chunk_id)
        if section_id not in self.metadata["section_ids"]:
            self.metadata["section_ids"].append(section_id)


@dataclass
class Relationship:
    """
    Minimalist Relationship class with flexible metadata including chunk tracking
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

    def add_chunk_info(self, chunk_id: str, section_id: str):
        """
        Add chunk and section information to metadata
        """
        if "chunk_ids" not in self.metadata:
            self.metadata["chunk_ids"] = []
        if "section_ids" not in self.metadata:
            self.metadata["section_ids"] = []

        if chunk_id not in self.metadata["chunk_ids"]:
            self.metadata["chunk_ids"].append(chunk_id)
        if section_id not in self.metadata["section_ids"]:
            self.metadata["section_ids"].append(section_id)


@dataclass
class ChunkData:
    """
    Data class to represent chunk information
    """

    id: str
    text: str
    section_id: str
    section_heading: str
    source_pdf: str
    has_table: bool
    has_image: bool
    char_count: int
    word_count: int


class KnowledgeGraphExtractor:
    def __init__(self, similarity_threshold=0.8):
        """
        Initialize Legal Knowledge Graph Extractor with LangChain LLMGraphTransformer
        """
        load_dotenv()

        # Initialize Azure OpenAI for LangChain
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2025-01-01-preview",
            azure_deployment="gpt-4o",  # Your deployment name
            temperature=0,
        )

        # Initialize spaCy for preprocessing (compatibility with pipeline)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

        # Define allowed nodes and relationships for legal documents
        # Define allowed nodes and relationships for legal documents
        self.allowed_nodes = [
            "LegalDocument",
            "Clause",
            "LegalPerson",
            "NaturalPerson",
            "LegalEntity",
            "Organization",
            "Court",
            "Case",
            "Law",
            "Statute",
            "Regulation",
            "Obligation",
            "Right",
            "Duty",
            "Contract",
            "Agreement",
            "Jurisdiction",
            "Event",
            "Action",
            "Evidence",
            "LegalRole",
            "Verdict",
            "Penalty",
            "Date",
            "TimePeriod"
        ]

        self.allowed_relationships = [
            "hasClause",
            "refersToLaw",
            "hasJurisdiction",
            "isPartOf",
            "hasParty",
            "hasObligation",
            "hasRight",
            "hasDuty",
            "issuedBy",
            "appliesTo",
            "represents",
            "isRepresentedBy",
            "filedBy",
            "heardBy",
            "decidedBy",
            "cites",
            "amends",
            "enforces",
            "isSubjectTo",
            "hasVerdict",
            "hasPenalty",
            "occursOn",
            "validDuring"
        ]


        # Initialize graph transformer with legal-specific nodes and relationships
        self.graph_transformer = LLMGraphTransformer(
            llm=self.llm,
            allowed_nodes=self.allowed_nodes,
            allowed_relationships=self.allowed_relationships,
        )

        self.similarity_threshold = similarity_threshold

    def _generate_id(self, name: str, entity_type: str) -> str:
        """
        Generate a consistent, unique ID that is stable across runs
        """
        normalized_name = name.lower().strip()
        normalized_type = entity_type.lower().strip()
        hash_input = f"{normalized_name}_{normalized_type}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def preprocess_entities(self, text: str) -> List[Dict]:
        """
        Extract entities using spaCy with minimal preprocessing
        (Added for compatibility with pipeline.py)
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
        Synchronous wrapper for async extraction method
        (Added for compatibility with pipeline.py)
        """
        try:
            # Run the async extraction in a synchronous context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._async_extract(text, spacy_entities))
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in R method: {e}")
            return {"entities": spacy_entities, "relationships": []}

    async def _async_extract(self, text: str, spacy_entities: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Async extraction method using LangChain
        """
        try:
            # Create LangChain document
            document = Document(page_content=text)

            # Extract graph using LangChain transformer
            graph_documents = await self.graph_transformer.aconvert_to_graph_documents([document])

            if not graph_documents:
                return {"entities": spacy_entities, "relationships": []}

            graph_doc = graph_documents[0]

            # Convert LangChain nodes to our format
            entities = []
            for node in graph_doc.nodes:
                entity_dict = {
                    "name": node.id,
                    "type": node.type,
                    "metadata": {
                        "description": f"{node.type} entity: {node.id}",
                    }
                }
                entities.append(entity_dict)

            # Convert LangChain relationships to our format
            relationships = []
            entity_name_to_id = {entity["name"]: entity["name"] for entity in entities}
            
            for rel in graph_doc.relationships:
                source_name = rel.source.id
                target_name = rel.target.id
                
                if source_name in entity_name_to_id and target_name in entity_name_to_id:
                    relationship_dict = {
                        "source_name": source_name,
                        "target_name": target_name,
                        "type": [rel.type],  # Wrap in array for compatibility
                        "metadata": {
                            "description": f"{source_name} {rel.type} {target_name}",
                            "strength": 0.8
                        }
                    }
                    relationships.append(relationship_dict)

            return {"entities": entities, "relationships": relationships}

        except Exception as e:
            logger.error(f"Async extraction error: {e}")
            return {"entities": spacy_entities, "relationships": []}

    def P(self, raw_data: Dict) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Process and standardize extracted data
        (Added for compatibility with pipeline.py)
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

    async def extract_from_chunk(self, chunk: ChunkData) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Extract entities and relationships from a single chunk using LangChain
        """
        try:
            # Create LangChain document from chunk
            document = Document(
                page_content=chunk.text,
                metadata={
                    "chunk_id": chunk.id,
                    "section_id": chunk.section_id,
                    "section_heading": chunk.section_heading,
                    "source_pdf": chunk.source_pdf,
                },
            )

            # Extract graph using LangChain transformer
            graph_documents = await self.graph_transformer.aconvert_to_graph_documents([document])

            if not graph_documents:
                return {"entities": [], "relationships": []}

            graph_doc = graph_documents[0]

            # Convert LangChain nodes to our Entity format
            entities = []
            entity_name_to_id = {}

            for node in graph_doc.nodes:
                entity_id = self._generate_id(node.id, node.type)
                entity = Entity(id=entity_id, name=node.id, type=node.type, metadata={})
                # Add chunk information
                entity.add_chunk_info(chunk.id, chunk.section_id)
                entities.append(entity)
                entity_name_to_id[node.id] = entity_id

            # Convert LangChain relationships to our Relationship format
            relationships = []
            for rel in graph_doc.relationships:
                source_id = entity_name_to_id.get(rel.source.id)
                target_id = entity_name_to_id.get(rel.target.id)

                if source_id and target_id:
                    relationship = Relationship(
                        id=self._generate_id(f"{source_id}_{target_id}", rel.type),
                        source_id=source_id,
                        target_id=target_id,
                        type=rel.type,
                        metadata={},
                    )
                    # Add chunk information
                    relationship.add_chunk_info(chunk.id, chunk.section_id)
                    relationships.append(relationship)

            return {"entities": entities, "relationships": relationships}

        except Exception as e:
            logger.error(f"Extraction Error for chunk {chunk.id}: {e}")
            return {"entities": [], "relationships": []}

    def D(self, processed_data: Dict) -> Dict[str, List[Union[Entity, Relationship]]]:
        """
        Deduplicate and merge entities and relationships with chunk tracking
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
        Merge two similar entities, combining chunk and section information
        """
        merged_metadata = {**entity1.metadata}

        # Merge chunk_ids and section_ids
        if "chunk_ids" in entity2.metadata:
            for chunk_id in entity2.metadata["chunk_ids"]:
                if chunk_id not in merged_metadata.get("chunk_ids", []):
                    if "chunk_ids" not in merged_metadata:
                        merged_metadata["chunk_ids"] = []
                    merged_metadata["chunk_ids"].append(chunk_id)

        if "section_ids" in entity2.metadata:
            for section_id in entity2.metadata["section_ids"]:
                if section_id not in merged_metadata.get("section_ids", []):
                    if "section_ids" not in merged_metadata:
                        merged_metadata["section_ids"] = []
                    merged_metadata["section_ids"].append(section_id)

        # Merge other metadata
        for key, value in entity2.metadata.items():
            if key not in ["chunk_ids", "section_ids"]:
                merged_metadata[key] = value

        return Entity(
            id=entity1.id,
            name=entity1.name,
            type=entity1.type,
            metadata=merged_metadata,
        )

    def _merge_relationships(self, rel1: Relationship, rel2: Relationship) -> Relationship:
        """
        Merge two similar relationships, combining chunk and section information
        """
        merged_metadata = {**rel1.metadata}

        # Merge chunk_ids and section_ids
        if "chunk_ids" in rel2.metadata:
            for chunk_id in rel2.metadata["chunk_ids"]:
                if chunk_id not in merged_metadata.get("chunk_ids", []):
                    if "chunk_ids" not in merged_metadata:
                        merged_metadata["chunk_ids"] = []
                    merged_metadata["chunk_ids"].append(chunk_id)

        if "section_ids" in rel2.metadata:
            for section_id in rel2.metadata["section_ids"]:
                if section_id not in merged_metadata.get("section_ids", []):
                    if "section_ids" not in merged_metadata:
                        merged_metadata["section_ids"] = []
                    merged_metadata["section_ids"].append(section_id)

        # Merge other metadata
        for key, value in rel2.metadata.items():
            if key not in ["chunk_ids", "section_ids"]:
                merged_metadata[key] = value

        return Relationship(
            id=rel1.id,
            source_id=rel1.source_id,
            target_id=rel1.target_id,
            type=rel1.type,
            metadata=merged_metadata,
        )

    async def extract_knowledge_graph(self, chunks: List[ChunkData]) -> Dict:
        """
        Comprehensive knowledge graph extraction pipeline from chunks
        """
        comprehensive_graph = {"entities": [], "relationships": []}

        # Process chunks in batches to avoid overwhelming the API
        for chunk in chunks:
            logger.info(f"Processing chunk {chunk.id}")
            chunk_graph = await self.extract_from_chunk(chunk)

            comprehensive_graph["entities"].extend(chunk_graph["entities"])
            comprehensive_graph["relationships"].extend(chunk_graph["relationships"])

        # Final deduplication across all chunks
        logger.info("Starting final deduplication...")
        final_deduped_graph = self.D(comprehensive_graph)

        logger.info(
            f"Final graph: {len(final_deduped_graph['entities'])} entities, {len(final_deduped_graph['relationships'])} relationships"
        )
        return final_deduped_graph

    def to_dict(self, graph):
        """
        Convert graph to a serializable dictionary
        """
        return {
            "entities": [asdict(entity) for entity in graph["entities"]],
            "relationships": [asdict(relationship) for relationship in graph["relationships"]],
        }


async def main():
    """
    Example usage of the legal knowledge graph extractor with legal document content
    """
    extractor = KnowledgeGraphExtractor()
# Modified legal texts with overlapping entities for testing merging

    legal_text = """
    IN THE SUPREME COURT OF INDIA Civil Appeal No. 2345 of 2023 ABC Corporation Ltd. (Appellant)
    Represented by: Advocate Mr. Ramesh Iyer vs The State of Maharashtra (Respondent)
    Represented by: Government Counsel Ms. Priya Kulkarni Judgment delivered by: Justice Arvind Mehta
    Date of Judgment: 20th January 2024 This civil appeal arises out of the High Court's judgment
    dated 14th October 2022 in Writ Petition No. 9876/2021. ABC Corporation Ltd. challenged the constitutional
    validity of Section 12 of the Maharashtra Industrial Development Act, 1961, citing its inconsistency
    with Article 19(1)(g) of the Constitution of India. The Supreme Court of India has jurisdiction over
    this matter. Justice Arvind Mehta presided over the proceedings involving The State of Maharashtra.
    """

    legal_text_2 = """
    ABC Corporation Ltd. submitted several documents including the Affidavit filed on 5th March 2023,
    a Motion to Stay Proceedings, and a Contractual Agreement dated 12th June 2019. The State of Maharashtra
    filed counter-affidavits and placed reliance on Section 21 of the MID Act. A hearing was held
    on 15th December 2023 in Court Room No. 3 before Justice Arvind Mehta. After considering the arguments 
    and evidence submitted, the Supreme Court of India dismissed the appeal and upheld the validity of the statute. 
    The case cites previous judgments including XYZ Ltd. vs State of Gujarat (2011) and Rajeev Bhatia vs Union of India (2018).
    Advocate Mr. Ramesh Iyer represented ABC Corporation Ltd. throughout the proceedings.
    """

    chunks = [
        ChunkData(
            id="legal_chunk_1",
            text=legal_text,
            section_id="case_details",
            section_heading="Case Details and Parties",
            source_pdf="supreme_court_judgment_2023.pdf",
            has_table=False,
            has_image=False,
            char_count=len(legal_text),
            word_count=len(legal_text.split()),
        ),
        ChunkData(
            id="legal_chunk_2",
            text=legal_text_2,
            section_id="proceedings",
            section_heading="Proceedings and Judgment",
            source_pdf="supreme_court_judgment_2023.pdf",
            has_table=False,
            has_image=False,
            char_count=len(legal_text_2),
            word_count=len(legal_text_2.split()),
        ),
    ]


    # Extract knowledge graph
    kg = await extractor.extract_knowledge_graph(chunks)

    # Save to file
    with open("legal_knowledge_graph.json", "w") as f:
        json.dump(extractor.to_dict(kg), indent=2, fp=f)

    print("Legal Knowledge Graph Extraction Complete!")
    print(f"Entities: {len(kg['entities'])}")
    print(f"Relationships: {len(kg['relationships'])}")

    # Print entities organized by type
    entity_types = {}
    for entity in kg["entities"]:
        if entity.type not in entity_types:
            entity_types[entity.type] = []
        entity_types[entity.type].append(entity)

    print("\nEntities by Type:")
    for entity_type, entities in entity_types.items():
        print(f"\n{entity_type}:")
        for entity in entities:
            print(f"  - {entity.name} (Chunks: {entity.metadata.get('chunk_ids', [])})")

    # Print relationships organized by type
    relationship_types = {}
    for rel in kg["relationships"]:
        if rel.type not in relationship_types:
            relationship_types[rel.type] = []
        relationship_types[rel.type].append(rel)

    print("\nRelationships by Type:")
    for rel_type, relationships in relationship_types.items():
        print(f"\n{rel_type}:")
        for rel in relationships:
            source_entity = next((e for e in kg["entities"] if e.id == rel.source_id), None)
            target_entity = next((e for e in kg["entities"] if e.id == rel.target_id), None)
            if source_entity and target_entity:
                print(f"  - {source_entity.name} -> {target_entity.name}")


if __name__ == "__main__":
    asyncio.run(main())