from pprint import pprint
from dotenv import load_dotenv
from typing import List
from tog.pipeline.mapping_handler import MappingHandler, Neo4jMappingHandler
from tog.utils.logger import console_logger as logger
from tog.models.entity import Entity
from tog.kgs import KnowledgeGraph, Neo4jKnowledgeGraph

# Load environment variables
load_dotenv()

class EntityMapper:
    def __init__(self, kg: KnowledgeGraph, mapping_handler: MappingHandler):
        self.kg = kg
        self.mapping_handler = mapping_handler
        self.logger = logger  # Using the package-level console logger

    def map_entities(self, extracted_entities: List[str]) -> List[Entity]:
        """
        Map extracted entities to knowledge graph entities using Neo4j.
        """
        mapped_entities = []
        
        try:
            with self.kg.driver.session() as session:
                for entity_name in extracted_entities:
                    # Updated query to include metadata
                    query = """
                    MATCH (e)
                    WHERE toLower(e.name) = toLower($entity_name)
                    RETURN e.name AS name, labels(e) AS types, e.id AS id, 
                        e.metadata AS metadata  // Ensure metadata is fetched
                    LIMIT 1
                    """
                    
                    result = session.run(query, entity_name=entity_name)
                    record = result.single()
                    
                    if record:
                        self.logger.debug(f"Entity found in KG: {record}")
                        entity = Entity(
                            id=str(record["id"]),
                            name=record["name"],
                            type=record["types"][0] if record["types"] else None,
                            metadata=record.get("metadata", {})  # Ensure metadata retrieval
                        )
                        # entity.metadata["mapping_type"] = "exact_match"
                        mapped_entities.append(entity)
                        # mapped_entities.append(entity)
                    else:
                        self.logger.debug(f"Entity not found in KG, using mapping handler: {entity_name}")
                        mapped_entity = self._use_mapping_handler(entity_name)
                        if mapped_entity:
                            mapped_entities.append(mapped_entity)
                            
        except Exception as e:
            self.logger.error(f"Error mapping entities: {str(e)}")
            
        return mapped_entities


    def _use_mapping_handler(self, extracted_entity: str) -> Entity:
        """
        Use the mapping handler to map an entity to the knowledge graph.
        """
        try:
            # call the map method with the extracted entity
            mapped_entity = self.mapping_handler.fuzzy_match(extracted_entity)
            self.logger.debug(f"Mapped entity using mapping handler: {mapped_entity}")
            # # Add mapping type to metadata
            # if mapped_entity:
            #     mapped_entity.metadata["mapping_type"] = "fuzzy_match" # It is already added in the mapping handler.. thinking, which is better this one or the one in the mapping handler
            return mapped_entity
        except Exception as e:
            self.logger.error(f"Error using mapping handler for entity '{extracted_entity}': {str(e)}")
            return None
          
if __name__ == "__main__":
    # Example usage
    kg = Neo4jKnowledgeGraph()
    mapping_handler = Neo4jMappingHandler(kg=kg)
    
    entity_mapper = EntityMapper(kg, mapping_handler)
    
    # Example extracted entities
    extracted_entities = ["CBD", "anxiety"]
    
    mapped_entities = entity_mapper.map_entities(extracted_entities)
    print(mapped_entities)
    import json
    entities_dict = [
        {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "metadata": entity.metadata
        }
        for entity in mapped_entities
    ]
    
    print(json.dumps(entities_dict, indent=4))
    print("-" * 50)
    pprint("Mapped Entities:")
    for entity in mapped_entities:
        pprint(f"ID: {entity.id}, Name: {entity.name}, Type: {entity.type}")
        pprint(f"Metadata: {entity.metadata}")
