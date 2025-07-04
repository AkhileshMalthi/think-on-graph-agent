from typing import List, Optional

from tog.llms import BaseLLM
from tog.kgs import KnowledgeGraph
from tog.models.entity import Entity
from tog.models.path import Path
from tog.pipeline.entity_explorer import Neo4jEntityExplorer
from tog.pipeline.relation_explorer import Neo4jRelationExplorer
from tog.pipeline.exploration_loop import ExplorationLoop
from tog.pipeline.entity_extractor import LLMExtractor, GroqEntityExtractor, AzureOpenAIEntityExtractor
from tog.pipeline.entity_mapper import EntityMapper
from tog.pipeline.mapping_handler import Neo4jMappingHandler
from tog.utils.logger import setup_default_logging
from tog.config import (
    DEFAULT_MODEL,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_PATHS,
    DEFAULT_MAX_ENTITIES_PER_ROUND,
    DEFAULT_MAX_RELATIONS
)

setup_default_logging()

class ToG:
    """
    Main class for integrating and using the knowledge graph exploration components.
    """
    
    def __init__(self, 
                llm: BaseLLM, 
                kg: KnowledgeGraph,
                entity_extractor: Optional[LLMExtractor] = None,
                entity_mapper: Optional[EntityMapper] = None):
        """
        Initialize the knowledge graph explorer.
        
        Args:
            llm: Language model for exploration and answer generation
            kg: Knowledge graph to explore
            entity_extractor: Optional entity extractor (will be created if not provided)
            entity_mapper: Optional entity mapper (will be created if not provided)
        """
        self.llm = llm
        self.kg = kg
        
        # Set up entity extractor
        self.entity_extractor = entity_extractor or self._create_default_entity_extractor()
        
        # Set up entity mapper
        self.entity_mapper = entity_mapper or self._create_default_entity_mapper()
    
    def _create_default_entity_extractor(self) -> LLMExtractor:
        """
        Create a default entity extractor using the same LLM.
        """
        # Determine the type of LLM and create the corresponding extractor
        if hasattr(self.llm, 'model_name'):
            model_name = self.llm.model_name
            
            # This is a simple detection approach - might need refinement based on your LLM classes
            if 'gpt' in model_name.lower():
                return AzureOpenAIEntityExtractor(model_name=model_name)
            elif 'llama' in model_name.lower():
                return GroqEntityExtractor(model_name=model_name)
        
        # Default to using the same LLM type with a basic wrapper
        return AzureOpenAIEntityExtractor(model_name=DEFAULT_MODEL)
    
    def _create_default_entity_mapper(self) -> EntityMapper:
        """
        Create a default entity mapper using the knowledge graph.
        """
        mapping_handler = Neo4jMappingHandler(kg=self.kg)
        return EntityMapper(kg=self.kg, mapping_handler=mapping_handler)
        
    def explore_and_answer(self, 
                          query: str, 
                          initial_entities: Optional[List[Entity]] = None,
                          max_iterations: int = DEFAULT_MAX_ITERATIONS,
                          max_paths: int = DEFAULT_MAX_PATHS) -> dict:
        """
        Explore the knowledge graph and generate an answer for the query.
        
        Args:
            query: The query to explore and answer
            initial_entities: Optional list of initial entities to start exploration from
            max_iterations: Maximum number of exploration iterations
            max_paths: Maximum number of paths to maintain
            
        Returns:
            A dictionary containing the answer and the explored paths
        """
        
        # Step 1: Extract entities from query if not provided
        if not initial_entities:
            # Extract entity names using the entity extractor
            extracted_entity_names = self.entity_extractor.extract_entities(query)
            
            if not extracted_entity_names:
                return {
                    "success": False,
                    "answer": "I couldn't identify any entities to explore in your query.",
                    "paths": []
                }
            
            # Map extracted entities to knowledge graph entities
            initial_entities = self.entity_mapper.map_entities(extracted_entity_names)
        
        if not initial_entities:
            return {
                "success": False,
                "answer": "I couldn't find any entities in your query that match our knowledge graph.",
                "paths": []
            }
        print(initial_entities)
        # Step 2: Initialize explorers
        entity_explorer = Neo4jEntityExplorer(
            llm=self.llm,
            kg=self.kg,
            query=query,
            max_entities_per_round=DEFAULT_MAX_ENTITIES_PER_ROUND
        )
        
        relation_explorer = Neo4jRelationExplorer(
            llm=self.llm,
            kg=self.kg,
            query=query,
            max_relations=DEFAULT_MAX_RELATIONS
        )
        
        # Step 3: Initialize exploration loop
        exploration_loop = ExplorationLoop(
            llm=self.llm,
            kg=self.kg,
            entity_explorer=entity_explorer,
            relation_explorer=relation_explorer,
            query=query,
            max_iterations=max_iterations,
            max_paths=max_paths
        )
        
        # Step 4: Execute exploration
        best_paths = exploration_loop.explore(initial_entities)
        
        if not best_paths:
            return {
                "success": False,
                "answer": "I couldn't find relevant information to answer your query.",
                "paths": []
            }
        
        # Step 5: Generate answer from explored paths
        answer = self._generate_answer(query, best_paths)
        
        return {
            "success": True,
            "answer": answer,
            "paths": [self._format_path(path) for path in best_paths]
        }
    
    def _generate_answer(self, query: str, paths: List[Path]) -> str:
        """
        Generate an answer to the query based on the explored paths.
        
        Args:
            query: The original query
            paths: The list of explored paths
            
        Returns:
            An answer string
        """
        # Format paths for the LLM
        paths_text = ""
        for i, path in enumerate(paths, 1):
            path_str = " → ".join([
                f"{triple.subject.name}" + 
                (f" -{triple.predicate.type}→ {triple.object.name}" if triple.predicate and triple.object else "")
                for triple in path.path
            ])
            paths_text += f"{i}. {path_str} (Confidence: {path.confidence_score:.2f})\n"
        
        # Generate answer using LLM
        prompt = f"""
        Based on the following knowledge graph paths, please provide a comprehensive answer to the query.
        
        QUERY: {query}
        
        KNOWLEDGE PATHS:
        {paths_text}
        
        Your answer should synthesize the information from these paths to provide a clear explanation.
        """
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that provides informative answers based on knowledge graph data."},
            {"role": "user", "content": prompt}
        ]
        
        answer = self.llm.generate(messages, temperature=0.7)
        return answer
    
    def _format_path(self, path: Path) -> dict:
        """
        Format a path for API response.
        
        Args:
            path: The path to format
            
        Returns:
            A dictionary representation of the path
        """
        return {
            "triples": [
                {
                    "subject": {
                        "id": triple.subject.id,
                        "name": triple.subject.name,
                        "type": triple.subject.type
                    },
                    "predicate": {
                        "id": triple.predicate.id,
                        "type": triple.predicate.type
                    } if triple.predicate else None,
                    "object": {
                        "id": triple.object.id,
                        "name": triple.object.name,
                        "type": triple.object.type
                    } if triple.object else None
                }
                for triple in path.path
            ],
            "confidence_score": path.confidence_score
        }


# Example usage
def main():
    # This is a demonstration - you'd need to implement or import the actual LLM and KG classes
    from tog.llms.azure_openai_llm import AzureOpenAILLM
    from tog.kgs.neo4j_kg import Neo4jKnowledgeGraph
    
    # Initialize components
    llm = AzureOpenAILLM(model_name="gpt-4o")
    kg = Neo4jKnowledgeGraph()
    
    # Initialize entity extractor and mapper
    entity_extractor = AzureOpenAIEntityExtractor(model_name="gpt-4o")
    mapping_handler = Neo4jMappingHandler(kg=kg)
    entity_mapper = EntityMapper(kg=kg, mapping_handler=mapping_handler)
    
    # Create explorer with the components
    explorer = ToG(
        llm=llm, 
        kg=kg,
        entity_extractor=entity_extractor,
        entity_mapper=entity_mapper
    )
    
    # Example query
    # query = "What are the key compliance and data protection responsibilities of the CONSULTANT under the agreement?"
    query="what is omnigon?"

    # Run exploration and get answer
    result = explorer.explore_and_answer(query)
    
    # Print result
    print(f"Query: {query}")
    print("\nAnswer:")
    print(result["answer"])
    print("\nExplored Paths:")
    for i, path in enumerate(result["paths"], 1):
        path_str = " → ".join([
            f"{triple['subject']['name']}" + 
            (f" -{triple['predicate']['type']}→ {triple['object']['name']}" if triple['predicate'] and triple['object'] else "")
            for triple in path["triples"]
        ])
        print(f"{i}. {path_str} (Confidence: {path['confidence_score']:.2f})")


if __name__ == "__main__":
    main()