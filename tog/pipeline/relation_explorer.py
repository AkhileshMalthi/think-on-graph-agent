import logging
from typing import Dict, List
from abc import ABC, abstractmethod

from tog.llms import BaseLLM
from tog.kgs import KnowledgeGraph
from tog.models.entity import Entity
from tog.models.relation import Relation
from tog.utils import prompt_utils

class RelationExplorer(ABC):
    """
    Abstract base class for relation explorers.
    This class defines the interface for exploring relations in a knowledge graph.
    """

    def __init__(self, 
                 llm: BaseLLM, 
                 kg: KnowledgeGraph, 
                 query: str,
                 max_relations: int = 3,
                 system_prompt: str = None):
        """
        Initialize the RelationExplorer with a language model, knowledge graph, and query.

        Args:
            llm: The language model to use for exploration.
            kg: The knowledge graph to explore.
            query: Query string for exploration guidance.
            max_relations: Maximum number of relations to return.
            system_prompt: System prompt for the LLM.
        """
        self.llm = llm
        self.kg = kg
        self.query = query
        self.max_relations = max_relations
        self.system_prompt = system_prompt or "You are an AI assistant specialized in analyzing semantic relations."
        self.logger = logging.getLogger(self.__class__.__name__)

    def explore_relations(self, entity: Entity, visited_entities: set = None) -> List[Relation]:
        """
        Explore relations associated with the given entity, avoiding visited entities.

        Args:
            entity: The entity to explore relations for.
            visited_entities: Set of entity IDs to avoid revisiting.

        Returns:
            A list of relations associated with the entity.
        """
        if visited_entities is None:
            visited_entities = set()
            
        self.logger.info(f"Exploring relations for entity: {entity.name}")
        
        # Get all candidate relations for the entity
        candidate_relations = self._get_candidates(entity, visited_entities)
        self.logger.info(f"Found {len(candidate_relations)} candidate relations: {candidate_relations}")
        print(f"Candidate relations: {candidate_relations}")
        # Prune based on relevance to query
        pruned_relations = self._prune_candidates(entity, candidate_relations)
        self.logger.info(f"Pruned to {len(pruned_relations)} relations")
        
        return pruned_relations
    
    @abstractmethod
    def _get_candidates(self, entity: Entity, visited_entities: set) -> List[Relation]:
        """
        Get candidate relations for the given entity, filtering out visited entities.

        Args:
            entity: The entity to get candidates for.
            visited_entities: Set of entity IDs to avoid.

        Returns:
            A list of candidate relations.
        """
        pass


    def _prune_candidates(self, entity: Entity, relations: List[Relation]) -> List[Relation]:
        """
        Prune the candidate relations using LLM to score their relevance to the query.

        Args:
            entity: The entity associated with the relations
            relations: The list of candidate relations to prune.

        Returns:
            A list of pruned relations ordered by relevance score.
        """
        if not relations:
            self.logger.debug("No relations to prune")
            return []
        
        try:
            # Format relations for the prompt
            relations_text = self._format_relations_text(relations)
            
            # Prepare prompt for ranking
            prompt = self._create_relations_prompt(relations_text, len(relations))
            
            # Call LLM for scoring
            scores_dict = self._get_llm_scores(prompt)
            
            # Assign scores to relations
            for idx_str, score in scores_dict.items():
                try:
                    idx = int(idx_str) - 1  # Convert to 0-based index
                    if 0 <= idx < len(relations):
                        relations[idx].metadata["relevance_score"] = float(score)
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error processing score for index {idx_str}: {e}")
            
            # Sort by score in descending order
            scored_relations = sorted(
                relations,
                key=lambda r: r.metadata.get("relevance_score", 0.0),
                reverse=True
            )
            
            # Return top N relations
            return scored_relations[:self.max_relations]
            
        except Exception as e:
            self.logger.error(f"Error pruning relations: {e}")
            return relations[:self.max_relations]

    def _format_relations_text(self, relations: List[Relation]) -> str:
        """Format relations for the prompt."""
        return prompt_utils.format_relations_for_prompt(relations)
    
    def _create_relations_prompt(self, relations_text: str, n: int) -> str:
        """Create prompt for relation scoring."""
        return prompt_utils.create_relations_prompt(
            self.query,
            relations_text,
            n,
            self.prompt_params.get('entity_name', 'Unknown Entity')
        )
    
    def _get_llm_scores(self, prompt: str) -> Dict:
        """Get scores from LLM."""
        messages = [
            {"role": "system", "content": "You are an AI assistant specialized in analyzing semantic relations between entities and questions."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate(messages, temperature=0.3)
        return prompt_utils.parse_llm_scores(response)


class Neo4jRelationExplorer(RelationExplorer):
    """
    A concrete implementation of RelationExplorer for Neo4j knowledge graph.
    """
    
    def _get_candidates(self, entity: Entity, visited_entities: set) -> List[Relation]:
        """
        Get candidate relations for the given entity using Neo4j knowledge graph.
        Filters out relations that lead to already visited entities.

        Args:
            entity: The entity to get candidates for.
            visited_entities: Set of entity IDs to avoid.

        Returns:
            A list of candidate relations.
        """
        try:
            self.logger.debug(f"Getting candidate relations for entity: {entity.name} (ID: {entity.id})")
            
            # Convert visited_entities set to list for Neo4j query
            visited_list = list(visited_entities) if visited_entities else []
            
            # Query to find all relationships where the given entity is the source (outgoing)
            # and target is not in visited entities
            query_outgoing = """
            MATCH (source)-[r]->(target)
            WHERE source.id = $entity_id 
            AND NOT target.id IN $visited_entities
            RETURN 
                source.id as source_id,
                source.name as source_name, 
                target.id as target_id,
                target.name as target_name,
                type(r) as relation_type,
                r.id as relation_id,
                properties(r) as metadata,
                false as is_incoming
            """
            
            # Query to find all relationships where the given entity is the target (incoming)
            # and source is not in visited entities
            query_incoming = """
            MATCH (source)-[r]->(target)
            WHERE target.id = $entity_id 
            AND NOT source.id IN $visited_entities
            RETURN 
                source.id as source_id,
                source.name as source_name,
                target.id as target_id,
                target.name as target_name,
                type(r) as relation_type,
                r.id as relation_id,
                properties(r) as metadata,
                true as is_incoming
            """
            
            # Execute both queries
            outgoing_results = self.kg.query(query_outgoing, entity_id=entity.id, visited_entities=visited_list)
            incoming_results = self.kg.query(query_incoming, entity_id=entity.id, visited_entities=visited_list)
            print("*" * 20)
            print(outgoing_results)
            print("*" * 20)
            print(incoming_results)
             
            # Combine results
            all_results = outgoing_results + incoming_results
            self.logger.debug(f"Found {len(all_results)} total relations ({len(outgoing_results)} outgoing, {len(incoming_results)} incoming)")
            
            # Convert results to Relation objects
            relations = []
            
            for result in all_results:
                # Extract metadata and ensure it's a dictionary
                metadata = result.get("metadata", {})
                if metadata is None:
                    metadata = {}
                
                # Add source and target names to metadata for better context
                metadata["source_name"] = result["source_name"]
                metadata["target_name"] = result["target_name"]
                metadata["is_incoming"] = result["is_incoming"]
                
                # Create the relation object
                relation = Relation(
                    id=result["relation_id"],
                    source_id=result["source_id"],
                    target_id=result["target_id"],
                    type=result["relation_type"],
                    metadata=metadata
                )
                print('---:'*60, relation)
                relations.append(relation)
            
            return relations
            
        except Exception as e:
            self.logger.error(f"Error getting candidate relations: {e}")
            return []

class RelationalPathFinder(RelationExplorer):
    """
    Extended relation explorer that finds not just immediate relations,
    but also multi-hop paths between entities.
    """
    
    def __init__(self, 
                llm: BaseLLM, 
                kg: KnowledgeGraph, 
                query: str,
                max_relations: int = 3,
                max_path_length: int = 2,
                system_prompt: str = None):
        """
        Initialize the RelationalPathFinder.
        
        Args:
            llm: The language model to use for exploration.
            kg: The knowledge graph to explore.
            query: Query string for exploration guidance.
            max_relations: Maximum number of relations to return.
            max_path_length: Maximum length of paths to consider (number of hops).
            system_prompt: System prompt for the LLM.
        """
        super().__init__(llm, kg, query, max_relations, system_prompt)
        self.max_path_length = max_path_length
    
    def _get_candidates(self, entity: Entity) -> List[Relation]:
        """
        Get candidate relations for the given entity, considering multi-hop paths.
        
        Args:
            entity: The entity to get candidates for.
            
        Returns:
            A list of candidate relations.
        """
        try:
            self.logger.debug(f"Getting multi-hop relations for entity: {entity.name} (ID: {entity.id})")
            
            # Query to find paths up to max_path_length hops from the entity
            # This uses the Neo4j variable length path syntax
            query = f"""
            MATCH path = (source)-[r1:*1..{self.max_path_length}]->(target)
            WHERE source.id = $entity_id
            WITH source, target, relationships(path) AS rels
            LIMIT 100  // Limit to prevent excessive results
            RETURN 
                source.id as source_id,
                source.name as source_name,
                target.id as target_id,
                target.name as target_name,
                [rel IN rels | type(rel)] AS relation_types,
                [rel IN rels | rel.id] AS relation_ids,
                length(rels) as path_length
            """
            
            # Execute the query
            results = self.kg.query(query, entity_id=entity.id)
            
            self.logger.debug(f"Found {len(results)} multi-hop relation paths")
            
            # Convert results to Relation objects
            # For multi-hop paths, we'll create a composite relation
            relations = []
            
            for result in results:
                # Skip if no relations in path
                if not result.get("relation_ids") or len(result["relation_ids"]) == 0:
                    continue
                
                # Create a composite relation ID
                composite_id = "_".join(result["relation_ids"])
                
                # Create a composite relation type
                composite_type = " -> ".join(result["relation_types"])
                
                # Create metadata
                metadata = {
                    "source_name": result["source_name"],
                    "target_name": result["target_name"],
                    "path_length": result["path_length"],
                    "relation_ids": result["relation_ids"],
                    "relation_types": result["relation_types"],
                    "is_composite": True
                }
                
                # Create the relation object
                relation = Relation(
                    id=composite_id,
                    source_id=result["source_id"],
                    target_id=result["target_id"],
                    type=composite_type,
                    metadata=metadata
                )
                
                relations.append(relation)
            
            return relations
            
        except Exception as e:
            self.logger.error(f"Error getting multi-hop relations: {e}")
            return []