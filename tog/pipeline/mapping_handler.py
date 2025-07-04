from abc import ABC, abstractmethod
from typing import Optional
from tog.models.entity import Entity
from tog.kgs import KnowledgeGraph
from fuzzywuzzy import process
from tog.utils.logger import setup_logger

class MappingHandler(ABC):
    
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.logger = setup_logger(name="mapping_handler", log_filename="mapping_handler.log")
        self.logger.info(f"MappingHandler initialized with kg: {kg}")

    @abstractmethod
    def fuzzy_match(self, entity: str) -> Optional[Entity]:
        """ Perform fuzzy matching on the entity against the knowledge graph. """
        pass

    @abstractmethod
    def semantic_match(self, entity: str) -> Optional[Entity]:
        """ Perform semantic matching on the entity against the knowledge graph. """
        pass

    @abstractmethod
    def levanstein_match(self, entity: str) -> Optional[Entity]:
        """ Perform Levenshtein matching on the entity against the knowledge graph. """
        pass

class Neo4jMappingHandler(MappingHandler):
    
    def fuzzy_match(self, entity_name: str) -> Optional[Entity]:
        """
        Match entity using fuzzy matching against Neo4j database.
        """
        try:
            with self.kg.driver.session() as session:
                # Improved query to fetch metadata as well
                query = """
                MATCH (e)
                WHERE toLower(e.name) CONTAINS toLower($entity_name)
                WITH e, 
                     apoc.text.levenshteinSimilarity(toLower(e.name), toLower($entity_name)) AS score
                ORDER BY score DESC
                LIMIT 10
                RETURN e.name AS name, labels(e) AS types, e.id AS id, e.metadata AS metadata, score
                """
                
                results = session.run(query, entity_name=entity_name).data()
                
                if not results:
                    self.logger.debug(f"No fuzzy matches found for entity: {entity_name}")
                    return None
                
                # Extract entity names for fuzzy matching
                entity_names = [result['name'] for result in results]
                best_match, score = process.extractOne(entity_name, entity_names)
                
                if score < 70:  # Acceptable threshold for a good match
                    self.logger.debug(f"Best fuzzy match for '{entity_name}' was '{best_match}' with score {score}, below threshold")
                    return None
                
                # Find the corresponding entity in the query results
                for result in results:
                    if result['name'] == best_match:
                        self.logger.info(f"Fuzzy matched '{entity_name}' to '{best_match}' with score {score}")
                        entity = Entity(
                            id=str(result['id']),
                            name=result['name'],
                            type=result['types'][0] if result['types'] else 'Unknown',
                            metadata=result.get("metadata", {})  # Ensure metadata retrieval
                        )
                        # Add mapping type and score to metadata
                        # entity.metadata["mapping_type"] = "fuzzy_match"
                        # entity.metadata["match_score"] = score
                        return entity
                        
                return None
        except Exception as e:
            self.logger.error(f"Error in fuzzy matching for entity '{entity_name}': {str(e)}")
            return None

    def semantic_match(self, entity: str) -> Optional[Entity]:
        """
        Perform semantic matching using NLP techniques (to be implemented).
        """
        pass

    def levanstein_match(self, entity: str) -> Optional[Entity]:
        """
        Perform Levenshtein matching on the entity against Neo4j.
        """
        pass
