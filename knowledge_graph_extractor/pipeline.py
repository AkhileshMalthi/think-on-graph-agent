import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from dataclasses import dataclass
import time

# Import your existing classes
from kg_extractor import KnowledgeGraphExtractor, Entity, Relationship
from neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ChunkData:
    """
    Data class to hold chunk information
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

class KnowledgeGraphPipeline:
    """
    Pipeline to process chunks and build knowledge graph in Neo4j
    """
    
    def __init__(self, chunks_folder: str = "chunks", similarity_threshold: float = 0.8):
        """
        Initialize the pipeline
        
        Args:
            chunks_folder (str): Path to folder containing chunk JSON files
            similarity_threshold (float): Threshold for entity similarity matching
        """
        self.chunks_folder = Path(chunks_folder)
        self.extractor = KnowledgeGraphExtractor(similarity_threshold=similarity_threshold)
        self.neo4j_connector = Neo4jConnector()
        
        # Ensure chunks folder exists
        if not self.chunks_folder.exists():
            raise FileNotFoundError(f"Chunks folder not found: {chunks_folder}")
    
    def load_chunks(self) -> List[ChunkData]:
        """
        Load all chunk JSON files from the chunks folder
        
        Returns:
            List[ChunkData]: List of loaded chunk data
        """
        chunks = []
        json_files = list(self.chunks_folder.glob("*.json"))
        
        logger.info(f"Found {len(json_files)} JSON files in {self.chunks_folder}")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    
                    # Handle both single chunk and list of chunks
                    if isinstance(chunk_data, list):
                        for chunk in chunk_data:
                            chunks.append(ChunkData(**chunk))
                    else:
                        chunks.append(ChunkData(**chunk_data))
                        
            except Exception as e:
                logger.error(f"Failed to load chunk file {json_file}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(chunks)} chunks")
        return chunks
    
    def enhance_entities_with_chunk_info(self, entities: List[Entity], chunk: ChunkData) -> List[Entity]:
        """
        Add chunk information to entity metadata
        
        Args:
            entities (List[Entity]): List of entities to enhance
            chunk (ChunkData): Chunk data to add to metadata
            
        Returns:
            List[Entity]: Enhanced entities with chunk information
        """
        enhanced_entities = []
        
        for entity in entities:
            # Add chunk information to metadata
            entity.metadata.update({
                "chunk_id": chunk.id,
                "section_id": chunk.section_id,
                "section_heading": chunk.section_heading,
                "source_pdf": chunk.source_pdf,
                "chunk_char_count": chunk.char_count,
                "chunk_word_count": chunk.word_count
            })
            
            # Add chunk context flags if available
            if chunk.has_table:
                entity.metadata["from_table_context"] = True
            if chunk.has_image:
                entity.metadata["from_image_context"] = True
            
            enhanced_entities.append(entity)
        
        return enhanced_entities
    
    def enhance_relationships_with_chunk_info(self, relationships: List[Relationship], chunk: ChunkData) -> List[Relationship]:
        """
        Add chunk information to relationship metadata
        
        Args:
            relationships (List[Relationship]): List of relationships to enhance
            chunk (ChunkData): Chunk data to add to metadata
            
        Returns:
            List[Relationship]: Enhanced relationships with chunk information
        """
        enhanced_relationships = []
        
        for relationship in relationships:
            # Add chunk information to metadata
            relationship.metadata.update({
                "chunk_id": chunk.id,
                "section_id": chunk.section_id,
                "section_heading": chunk.section_heading,
                "source_pdf": chunk.source_pdf
            })
            
            enhanced_relationships.append(relationship)
        
        return enhanced_relationships
    
    def process_single_chunk(self, chunk: ChunkData) -> Dict[str, List]:
        """
        Process a single chunk and extract knowledge graph
        
        Args:
            chunk (ChunkData): Chunk to process
            
        Returns:
            Dict[str, List]: Extracted knowledge graph with entities and relationships
        """
        logger.info(f"Processing chunk {chunk.id[:8]}... from {chunk.source_pdf}")
        
        try:
            # Extract knowledge graph from chunk text
            spacy_entities = self.extractor.preprocess_entities(chunk.text)
            raw_graph = self.extractor.R(chunk.text, spacy_entities)
            processed_graph = self.extractor.P(raw_graph)
            deduped_graph = self.extractor.D(processed_graph)
            
            # Enhance entities and relationships with chunk information
            enhanced_entities = self.enhance_entities_with_chunk_info(
                deduped_graph["entities"], chunk
            )
            enhanced_relationships = self.enhance_relationships_with_chunk_info(
                deduped_graph["relationships"], chunk
            )
            
            return {
                "entities": enhanced_entities,
                "relationships": enhanced_relationships
            }
            
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk.id}: {e}")
            return {"entities": [], "relationships": []}
    
    def process_all_chunks(self) -> Dict[str, List]:
        """
        Process all chunks and build comprehensive knowledge graph
        
        Returns:
            Dict[str, List]: Complete knowledge graph
        """
        chunks = self.load_chunks()
        
        if not chunks:
            logger.warning("No chunks found to process")
            return {"entities": [], "relationships": []}
        
        comprehensive_graph = {
            "entities": [],
            "relationships": []
        }
        
        processed_count = 0
        
        for chunk in chunks:
            chunk_graph = self.process_single_chunk(chunk)
            
            comprehensive_graph["entities"].extend(chunk_graph["entities"])
            comprehensive_graph["relationships"].extend(chunk_graph["relationships"])
            
            processed_count += 1
            
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(chunks)} chunks")
        
        logger.info(f"Completed processing {processed_count} chunks")
        
        # Final deduplication across all chunks
        logger.info("Performing final deduplication...")
        final_graph = self.extractor.D(comprehensive_graph)
        
        logger.info(f"Final graph: {len(final_graph['entities'])} entities, {len(final_graph['relationships'])} relationships")
        
        return final_graph
    
    def save_to_neo4j(self, knowledge_graph: Dict[str, List], clear_first: bool = True):
        """
        Save the knowledge graph to Neo4j
        
        Args:
            knowledge_graph (Dict[str, List]): Knowledge graph to save
            clear_first (bool): Whether to clear the database first
        """
        logger.info("Saving knowledge graph to Neo4j...")
        
        try:
            # Convert to dictionary format expected by Neo4j connector
            graph_dict = self.extractor.to_dict(knowledge_graph)
            
            # Save to Neo4j
            self.neo4j_connector.save_knowledge_graph(graph_dict, clear_first=clear_first)
            
            logger.info("Successfully saved knowledge graph to Neo4j")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge graph to Neo4j: {e}")
            raise
    
    def save_to_file(self, knowledge_graph: Dict[str, List], filename: str = "complete_knowledge_graph.json"):
        """
        Save the knowledge graph to a JSON file
        
        Args:
            knowledge_graph (Dict[str, List]): Knowledge graph to save
            filename (str): Output filename
        """
        try:
            graph_dict = self.extractor.to_dict(knowledge_graph)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(graph_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Knowledge graph saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge graph to file: {e}")
    
    def run_pipeline(self, save_to_file: bool = True, save_to_neo4j: bool = True, 
                    clear_neo4j_first: bool = True, output_filename: str = "complete_knowledge_graph.json"):
        """
        Run the complete pipeline
        
        Args:
            save_to_file (bool): Whether to save to JSON file
            save_to_neo4j (bool): Whether to save to Neo4j
            clear_neo4j_first (bool): Whether to clear Neo4j database first
            output_filename (str): Output JSON filename
        """
        start_time = time.time()
        
        logger.info("Starting Knowledge Graph Pipeline...")
        
        try:
            # Process all chunks
            knowledge_graph = self.process_all_chunks()
            
            if not knowledge_graph["entities"] and not knowledge_graph["relationships"]:
                logger.warning("No knowledge graph extracted from chunks")
                return
            
            # Save to file if requested
            if save_to_file:
                self.save_to_file(knowledge_graph, output_filename)
            
            # Save to Neo4j if requested
            if save_to_neo4j:
                self.save_to_neo4j(knowledge_graph, clear_neo4j_first)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Pipeline completed successfully in {elapsed_time:.2f} seconds")
            
            # Print summary
            print(f"\n{'='*50}")
            print("PIPELINE SUMMARY")
            print(f"{'='*50}")
            print(f"Total Entities: {len(knowledge_graph['entities'])}")
            print(f"Total Relationships: {len(knowledge_graph['relationships'])}")
            print(f"Processing Time: {elapsed_time:.2f} seconds")
            
            if save_to_file:
                print(f"JSON Output: {output_filename}")
            if save_to_neo4j:
                print("Neo4j Database: Updated")
            print(f"{'='*50}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        finally:
            # Clean up Neo4j connection
            self.neo4j_connector.close()
    
    def get_chunk_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the chunks in the folder
        
        Returns:
            Dict[str, Any]: Statistics about chunks
        """
        chunks = self.load_chunks()
        
        if not chunks:
            return {"total_chunks": 0}
        
        total_chars = sum(chunk.char_count for chunk in chunks)
        total_words = sum(chunk.word_count for chunk in chunks)
        sources = set(chunk.source_pdf for chunk in chunks)
        sections = set(chunk.section_heading for chunk in chunks)
        chunks_with_tables = sum(1 for chunk in chunks if chunk.has_table)
        chunks_with_images = sum(1 for chunk in chunks if chunk.has_image)
        
        return {
            "total_chunks": len(chunks),
            "total_characters": total_chars,
            "total_words": total_words,
            "unique_sources": len(sources),
            "unique_sections": len(sections),
            "chunks_with_tables": chunks_with_tables,
            "chunks_with_images": chunks_with_images,
            "source_files": list(sources),
            "avg_chars_per_chunk": total_chars / len(chunks) if chunks else 0,
            "avg_words_per_chunk": total_words / len(chunks) if chunks else 0
        }

def main():
    """
    Main function to run the pipeline
    """
    # Configuration
    CHUNKS_FOLDER = r"knowledge_graph_extractor\chunks"  # Modify this path as needed
    OUTPUT_FILE = "complete_knowledge_graph.json"
    
    try:
        # Initialize pipeline
        pipeline = KnowledgeGraphPipeline(
            chunks_folder=CHUNKS_FOLDER,
            similarity_threshold=0.8
        )
        
        # Print chunk statistics
        stats = pipeline.get_chunk_statistics()
        print(f"\n{'='*50}")
        print("CHUNK STATISTICS")
        print(f"{'='*50}")
        for key, value in stats.items():
            if key != "source_files":
                print(f"{key.replace('_', ' ').title()}: {value}")
        print(f"{'='*50}\n")
        
        # Run the pipeline
        pipeline.run_pipeline(
            save_to_file=True,
            save_to_neo4j=True,
            clear_neo4j_first=True,
            output_filename=OUTPUT_FILE
        )
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise

if __name__ == "__main__":
    main()