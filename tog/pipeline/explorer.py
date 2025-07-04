from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import logging
import json
import re

from tog.llms import BaseLLM
from tog.kgs import KnowledgeGraph
from tog.models.entity import Entity
from tog.models.relation import Relation


class Explorer:
    """Abstract base class for exploring entities and relations in a knowledge graph."""
    def __init__(self, llm: BaseLLM, kg: KnowledgeGraph, query: str, prune_prompt: str, 
                 prompt_params: Dict[str, str] = None, system_prompt: str = None):
        self.llm = llm
        self.kg = kg
        self.query = query
        self.prune_prompt = prune_prompt
        self.prompt_params = prompt_params or {}
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.logger = logging.getLogger(self.__class__.__name__)


class RelationExplorer(Explorer, ABC):
    """Abstract base class for relation explorers."""

    def explore_relations(self, entity: Entity) -> List[Relation]:
        """Explore relations associated with the given entity."""
        candidate_relations = self.get_candidates(entity)
        return self.prune_candidates(candidate_relations)
    
    @abstractmethod
    def get_candidates(self, entity: Entity) -> List[Relation]:
        """Get candidate relations for the given entity."""
        pass

    def prune_candidates(self, relations: List[Relation]) -> List[Relation]:
        """Prune candidate relations using LLM to score their relevance."""
        if not relations:
            self.logger.debug("No relations to prune")
            return []
        
        try:
            # Format relations for the prompt
            relations_text = self._format_relations_text(relations)
            n = min(3, len(relations))
            
            # Get LLM response
            prompt = self._create_relations_prompt(relations_text, n)
            scores_dict = self._get_llm_scores(prompt)
            
            # Score and sort relations
            scored_relations = self._score_relations(relations, scores_dict)
            return scored_relations[:n]
            
        except Exception as e:
            self.logger.error(f"Error pruning relations: {e}")
            return relations[:min(3, len(relations))]
    
    def _format_relations_text(self, relations: List[Relation]) -> str:
        """Format relations for the prompt."""
        relations_text = ""
        for i, relation in enumerate(relations, 1):
            is_incoming = relation.metadata.get("is_incoming", False)
            source = relation.metadata.get('source_name', 'Unknown')
            target = relation.metadata.get('target_name', 'Unknown')
            direction = f"{source} → {target}"
            relations_text += f"{i}. Relation: {relation.type}, Direction: {direction}\n"
        return relations_text
    
    def _create_relations_prompt(self, relations_text: str, n: int) -> str:
        """Create prompt for relation scoring."""
        return f"""
        Please retrieve {n} relations that contribute to the question and rate their contribution on a scale from 0 to 1 (the sum of the scores of {n} relations is 1). Return the result in valid JSON format.
        
        Q: {self.query}
        Topic Entity: {self.prompt_params.get('entity_name', 'Unknown Entity')}
        Relations: 
        {relations_text}
        """
    
    def _get_llm_scores(self, prompt: str) -> Dict:
        """Get scores from LLM."""
        messages = [
            {"role": "system", "content": "You are an AI assistant specialized in analyzing semantic relations between entities and questions."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate(messages, temperature=0.3)
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON")
                return {}
        else:
            self.logger.error(f"No JSON found in LLM response")
            return {}
    
    def _score_relations(self, relations: List[Relation], scores_dict: Dict) -> List[Relation]:
        """Score relations based on LLM response."""
        scored_relations = []
        for relation in relations:
            score = 0.0
            for rel_type, rel_score in scores_dict.items():
                if relation.type.lower() in rel_type.lower():
                    score = float(rel_score)
                    break
            
            relation.metadata["relevance_score"] = score
            scored_relations.append(relation)
        
        scored_relations.sort(key=lambda r: r.metadata.get("relevance_score", 0.0), reverse=True)
        return scored_relations
        

class Neo4jRelationExplorer(RelationExplorer):
    """A concrete implementation of RelationExplorer for Neo4j knowledge graph."""
    
    def get_candidates(self, entity: Entity) -> List[Relation]:
        """Get candidate relations for the given entity using Neo4j knowledge graph."""
        try:
            self.logger.debug(f"Getting candidate relations for entity: {entity.name} (ID: {entity.id})")
            
            outgoing_results = self._query_outgoing_relations(entity.id)
            incoming_results = self._query_incoming_relations(entity.id)
            all_results = outgoing_results + incoming_results
            
            relations = self._convert_results_to_relations(all_results)
            
            self.logger.debug(f"Found {len(relations)} candidate relations for entity: {entity.name}")
            return relations
            
        except Exception as e:
            self.logger.error(f"Error getting candidate relations for entity {entity.name}: {e}")
            return []
    
    def _query_outgoing_relations(self, entity_id: str):
        """Query outgoing relations."""
        query = """
        MATCH (source)-[r]->(target)
        WHERE source.id = $entity_id
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
        return self.kg.query(query, entity_id=entity_id)
    
    def _query_incoming_relations(self, entity_id: str):
        """Query incoming relations."""
        query = """
        MATCH (source)-[r]->(target)
        WHERE target.id = $entity_id
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
        return self.kg.query(query, entity_id=entity_id)
    
    def _convert_results_to_relations(self, results):
        """Convert query results to Relation objects."""
        relations = []
        for result in results:
            relation_id = str(result.get("relation_id", ""))
            
            # Generate ID if not found
            if not relation_id:
                relation_id = f"rel_{result['source_id']}_{result['relation_type']}_{result['target_id']}"
            
            metadata = result.get("metadata", {})
            metadata.update({
                "source_name": result.get("source_name", ""),
                "target_name": result.get("target_name", ""),
                "is_incoming": result.get("is_incoming", False)
            })
            
            relation = Relation(
                id=relation_id,
                source_id=result["source_id"],
                target_id=result["target_id"],
                type=result["relation_type"],
                metadata=metadata
            )
            relations.append(relation)
        
        return relations


class EntityExplorer(Explorer, ABC):
    """Abstract base class for entity exploration in a knowledge graph."""
    
    def __init__(self, llm: BaseLLM, kg: KnowledgeGraph, query: str, 
                 prune_prompt: str, max_entities_per_round: int = 3,
                 decay_factor: float = 0.9, prompt_params: Dict[str, str] = None,
                 system_prompt: str = None):
        """
        Initialize the EntityExplorer with a language model, knowledge graph, and query.
        
        Args:
            llm (BaseLLM): The language model to use for exploration.
            kg (KnowledgeGraph): The knowledge graph to explore.
            query (str): The query string for exploration.
            prune_prompt (str): Prompt template for pruning entities.
            max_entities_per_round (int): Maximum number of entities to keep per exploration round.
            decay_factor (float): Decay factor for context ranking.
            prompt_params (Dict[str, str]): Parameters for the prompt.
            system_prompt (str, optional): System prompt for the LLM.
        """
        super().__init__(llm, kg, query, prune_prompt, prompt_params, system_prompt)
        self.max_entities_per_round = max_entities_per_round
        self.decay_factor = decay_factor
    
    def explore_entities(self, entity: Entity) -> List[Entity]:
        """Get entities related to the given entity in the knowledge graph."""
        candidate_entities = self._get_related_entities(entity)
        self.logger.debug(f"Candidate entities for {entity.name}: {len(candidate_entities)}")
        
        pruned_entities = self._prune_entities(candidate_entities)
        self.logger.debug(f"Pruned entities for {entity.name}: {len(pruned_entities)}")
        
        return pruned_entities
    
    def explore_with_relations(self, topic_entity: Entity, selected_relations: List[Relation]) -> List[Tuple[Entity, Relation, Entity]]:
        """
        Explore entities connected to the topic entity through the selected relations.
        
        Args:
            topic_entity: The entity to explore from.
            selected_relations: The relations to follow for exploration.
            
        Returns:
            A list of tuples (source_entity, relation, target_entity).
        """
        self.logger.info(f"Starting entity exploration for '{topic_entity.name}'")
        
        # Step 1: Entity Discovery - Find all connected entities
        entity_relation_tuples = self._discover_connected_entities(topic_entity, selected_relations)
        self.logger.info(f"Found {len(entity_relation_tuples)} entity-relation tuples")
        
        # Step 2: Context-Based Entity Pruning - Select the most relevant entities
        pruned_tuples = self._batch_prune_entities(entity_relation_tuples)
        self.logger.info(f"Pruned to {len(pruned_tuples)} entity-relation tuples")
        
        return pruned_tuples
    
    @abstractmethod
    def _get_related_entities(self, entity: Entity) -> List[Entity]:
        """
        Get related entities for the given entity from the knowledge graph.
        
        Args:
            entity: The entity to explore.
            
        Returns:
            A list of candidate entities.
        """
        pass
    
    @abstractmethod
    def _discover_connected_entities(self, entity: Entity, relations: List[Relation]) -> List[Tuple[Entity, Relation, Entity]]:
        """
        Discover entities connected to the source entity through the given relations.
        
        Args:
            entity: The source entity.
            relations: The relations to follow.
            
        Returns:
            A list of tuples (source_entity, relation, target_entity).
        """
        pass

    def _prune_entities(self, entities: List[Entity]) -> List[Entity]:
        """Prune the list of entities based on certain criteria."""
        if not entities:
            self.logger.debug("No entities to prune")
            return []
        
        try:
            entities_text = self._format_entities_text(entities)
            n = min(self.max_entities_per_round, len(entities))
            
            # Get LLM response
            formatted_prompt = self._create_entities_prompt(entities_text, n)
            scores_dict = self._get_llm_scores(formatted_prompt)
            
            # Score and sort entities
            scored_entities = self._score_entities(entities, scores_dict)
            return scored_entities[:n]
            
        except Exception as e:
            self.logger.error(f"Error pruning entities: {e}")
            return entities[:min(self.max_entities_per_round, len(entities))]
    
    def _batch_prune_entities(self, entity_relation_tuples: List[Tuple[Entity, Relation, Entity]]) -> List[Tuple[Entity, Relation, Entity]]:
        """
        Prune entities based on their relevance to the query using batch processing.
        All tuples are sent to the LLM at once for evaluation.
        
        Args:
            entity_relation_tuples: List of (source, relation, target) tuples.
            
        Returns:
            A pruned list of tuples.
        """
        if not entity_relation_tuples:
            self.logger.debug("No entity-relation tuples to prune")
            return []
        
        try:
            # Format entity-relation tuples for the prompt
            tuples_text = ""
            for i, (source, relation, target) in enumerate(entity_relation_tuples, 1):
                source_desc = f"{source.name} ({source.type})"
                relation_desc = relation.type
                target_desc = f"{target.name} ({target.type})"
                
                # Add descriptions if available
                if source.metadata and "description" in source.metadata:
                    source_desc += f": {source.metadata['description']}"
                if relation.metadata and "description" in relation.metadata:
                    relation_desc += f": {relation.metadata['description']}"
                if target.metadata and "description" in target.metadata:
                    target_desc += f": {target.metadata['description']}"
                
                tuples_text += f"{i}. {source_desc} -[{relation_desc}]-> {target_desc}\n"
            
            # Create prompt for batch pruning
            prompt = f"""
            Please analyze the following knowledge graph triples and rank them based on their relevance to the query.
            
            QUERY: {self.query}
            
            KNOWLEDGE GRAPH TRIPLES:
            {tuples_text}
            
            For each triple, assign a relevance score between 0.0 and 1.0, where 1.0 is highly relevant and 0.0 is not relevant at all.
            Consider how useful each triple would be in answering the query.
            
            Return your response as a JSON object where the keys are the indexes of the triples and the values are their relevance scores.
            Example format:
            {{
                "1": 0.9,
                "2": 0.7,
                "3": 0.3
            }}
            
            Return only the JSON object, no additional explanations.
            """
            
            # Call LLM for batch scoring
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm.generate(messages, temperature=0.2)
            
            # Parse LLM response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    scores_dict = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse LLM response as JSON: {response}")
                    return entity_relation_tuples[:self.max_entities_per_round]
            else:
                self.logger.error(f"No JSON found in LLM response: {response}")
                return entity_relation_tuples[:self.max_entities_per_round]
            
            # Assign scores to entities
            for idx_str, score in scores_dict.items():
                try:
                    idx = int(idx_str) - 1  # Convert to 0-based index
                    if 0 <= idx < len(entity_relation_tuples):
                        _, _, target = entity_relation_tuples[idx]
                        target.metadata["relevance_score"] = float(score)
                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Error processing score for index {idx_str}: {e}")
            
            # Sort by score in descending order
            scored_tuples = sorted(
                entity_relation_tuples,
                key=lambda t: t[2].metadata.get("relevance_score", 0.0),
                reverse=True
            )
            
            # Return top N tuples
            return scored_tuples[:self.max_entities_per_round]
            
        except Exception as e:
            self.logger.error(f"Error in batch pruning entities: {e}")
            # Return at most max_entities_per_round if pruning fails
            return entity_relation_tuples[:self.max_entities_per_round]
    
    def _format_entities_text(self, entities: List[Entity]) -> str:
        """Format entities for the prompt."""
        entities_text = ""
        for i, entity in enumerate(entities, 1):
            entity_desc = f"{entity.name} ({entity.type})"
            if entity.metadata and "description" in entity.metadata:
                entity_desc += f": {entity.metadata['description']}"
            entities_text += f"{i}. {entity_desc}\n"
        return entities_text
    
    def _create_entities_prompt(self, entities_text: str, n: int) -> str:
        """Create prompt for entity scoring."""
        return self.prune_prompt.format(
            query=self.query,
            n=n,
            entities=entities_text,
            **self.prompt_params
        )
    
    def _get_llm_scores(self, prompt: str) -> Dict:
        """Get scores from LLM."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate(messages, temperature=0.3)
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                self.logger.error("Failed to parse LLM response as JSON")
                return {}
        else:
            self.logger.error("No JSON found in LLM response")
            return {}
    
    def _score_entities(self, entities: List[Entity], scores_dict: Dict) -> List[Entity]:
        """Score entities based on LLM response."""
        scored_entities = []
        for entity in entities:
            score = 0.0
            for entity_name, entity_score in scores_dict.items():
                if entity.name.lower() in entity_name.lower():
                    score = float(entity_score)
                    break
            
            entity.metadata["relevance_score"] = score
            scored_entities.append(entity)
        
        scored_entities.sort(key=lambda e: e.metadata.get("relevance_score", 0.0), reverse=True)
        return scored_entities


class Neo4jEntityExplorer(EntityExplorer):
    """Entity explorer for Neo4j knowledge graph."""
    
    def _get_related_entities(self, entity: Entity) -> List[Entity]:
        """Get related entities for the given entity from the Neo4j knowledge graph."""
        try:
            self.logger.debug(f"Getting related entities for entity: {entity.name} (ID: {entity.id})")
            
            results = self._query_related_entities(entity.id)
            entities = self._convert_results_to_entities(results)
            
            self.logger.debug(f"Found {len(entities)} related entities for entity: {entity.name}")
            return entities
            
        except Exception as e:
            self.logger.error(f"Error getting related entities for entity {entity.name}: {e}")
            return []
    
    def _discover_connected_entities(self, entity: Entity, relations: List[Relation]) -> List[Tuple[Entity, Relation, Entity]]:
        """
        Discover entities connected to the source entity through the given relations using Neo4j.
        
        Args:
            entity: The source entity.
            relations: The relations to follow.
            
        Returns:
            A list of tuples (source_entity, relation, target_entity).
        """
        entity_relation_tuples = []
        
        # Collect relation IDs for batch query
        relation_ids = [relation.id for relation in relations]
        
        try:
            # Query to find all connected entities through the specified relations
            # This query handles both directions: entity as source or as target
            query = """
            MATCH (e)-[r]->(target)
            WHERE e.id = $entity_id AND r.id IN $relation_ids
            RETURN 
                e.id as source_id,
                e.name as source_name,
                labels(e)[0] as source_type,
                properties(e) as source_properties,
                r.id as relation_id,
                type(r) as relation_type,
                properties(r) as relation_properties,
                target.id as target_id,
                target.name as target_name,
                labels(target)[0] as target_type,
                properties(target) as target_properties
            UNION
            MATCH (source)-[r]->(e)
            WHERE e.id = $entity_id AND r.id IN $relation_ids
            RETURN 
                source.id as source_id,
                source.name as source_name,
                labels(source)[0] as source_type,
                properties(source) as source_properties,
                r.id as relation_id,
                type(r) as relation_type,
                properties(r) as relation_properties,
                e.id as target_id,
                e.name as target_name,
                labels(e)[0] as target_type,
                properties(e) as target_properties
            """
            
            # Execute the query using the knowledge graph
            self.logger.debug(f"Executing Neo4j query for entity ID: {entity.id} with {len(relation_ids)} relations")
            results = self.kg.query(query, entity_id=entity.id, relation_ids=relation_ids)
            
            self.logger.debug(f"Found {len(results)} connected entities")
            
            # Process results
            for result in results:
                # Create source entity
                source_entity = Entity(
                    id=result["source_id"],
                    name=result["source_name"],
                    type=result["source_type"],
                    metadata={k: v for k, v in result.get("source_properties", {}).items() 
                              if k not in ["id", "name"]}
                )
                
                # Find matching relation from the provided list
                relation = None
                relation_id = result["relation_id"]
                for r in relations:
                    if r.id == relation_id:
                        relation = r
                        break
                
                # If relation not found, create it from result
                if not relation:
                    relation = Relation(
                        id=relation_id,
                        source_id=result["source_id"],
                        target_id=result["target_id"],
                        type=result["relation_type"],
                        metadata={k: v for k, v in result.get("relation_properties", {}).items() 
                                  if k not in ["id"]}
                    )
                
                # Create target entity
                target_entity = Entity(
                    id=result["target_id"],
                    name=result["target_name"],
                    type=result["target_type"],
                    metadata={k: v for k, v in result.get("target_properties", {}).items() 
                              if k not in ["id", "name"]}
                )
                
                # Add the tuple to the list
                entity_relation_tuples.append((source_entity, relation, target_entity))
            
            return entity_relation_tuples
            
        except Exception as e:
            self.logger.error(f"Error discovering connected entities: {e}")
            return []
    
    def _query_related_entities(self, entity_id: str):
        """Query related entities."""
        query = """
        MATCH (source)-[r]-(target)
        WHERE source.id = $entity_id AND target.id <> $entity_id
        RETURN DISTINCT
            target.id as id,
            target.name as name,
            labels(target)[0] as type,
            properties(target) as properties
        """
        return self.kg.query(query, entity_id=entity_id)
    
    def _convert_results_to_entities(self, results):
        """Convert query results to Entity objects."""
        entities = []
        for result in results:
            metadata = {k: v for k, v in result.get("properties", {}).items() 
                      if k not in ["id", "name"]}
            
            entity = Entity(
                id=result["id"],
                name=result["name"],
                type=result["type"],
                metadata=metadata
            )
            entities.append(entity)
        
        return entities
    
    def batch_get_entity_metadata(self, entity_relation_tuples: List[Tuple[Entity, Relation, Entity]]) -> List[Tuple[Entity, Relation, Entity]]:
        """
        Efficiently retrieve additional metadata for all entities in one batch query.
        
        Args:
            entity_relation_tuples: List of (source, relation, target) tuples.
            
        Returns:
            The same list with enriched metadata.
        """
        if not entity_relation_tuples:
            return []
        
        try:
            # Extract all entity IDs
            entity_ids = set()
            for source, _, target in entity_relation_tuples:
                entity_ids.add(source.id)
                entity_ids.add(target.id)
            
            # Query to get additional metadata for all entities at once
            query = """
            MATCH (e)
            WHERE e.id IN $entity_ids
            RETURN 
                e.id as id,
                properties(e) as properties
            """
            
            # Execute the query
            results = self.kg.query(query, entity_ids=list(entity_ids))
            
            # Create metadata lookup dictionary
            metadata_lookup = {}
            for result in results:
                entity_id = result["id"]
                properties = result.get("properties", {})
                metadata = {k: v for k, v in properties.items() if k not in ["id", "name"]}
                metadata_lookup[entity_id] = metadata
            
            # Update entities with additional metadata
            for i, (source, relation, target) in enumerate(entity_relation_tuples):
                if source.id in metadata_lookup:
                    source.metadata.update(metadata_lookup[source.id])
                if target.id in metadata_lookup:
                    target.metadata.update(metadata_lookup[target.id])
            
            return entity_relation_tuples
            
        except Exception as e:
            self.logger.error(f"Error batch retrieving entity metadata: {e}")
            return entity_relation_tuples


if __name__ == "__main__":
    # Example usage
    import logging
    from tog.llms import AzureOpenAILLM
    from tog.kgs import Neo4jKnowledgeGraph
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    llm = AzureOpenAILLM(model_name="gpt-35-turbo")
    kg = Neo4jKnowledgeGraph()

    query = "What are the medical benefits of Medical Cannabis?"
    prune_prompt = """
    Please retrieve {n} entities that contribute to answering the question and rate their contribution on a scale from 0 to 1 (the sum of the scores of {n} entities is 1). Return the result in valid JSON format.
    
    Q: {query}
    Topic Entity: {entity_name}
    Entities: 
    {entities}
    """
    prompt_params = {"entity_name": "Chronic Pain"}
    
    # Create a topic entity for exploration
    topic_entity = Entity(
        id="192db73673d90090cf1cb7d1be13aebc", 
        name="Chronic Pain", 
        type="Medical Condition", 
        metadata={"description": "A long-lasting pain that persists beyond the usual recovery period or accompanies a chronic health condition."}
    )
    
    # Example of relation exploration
    print("\n=== RELATION EXPLORATION ===")
    relation_explorer = Neo4jRelationExplorer(llm, kg, query, prune_prompt, prompt_params)
    relations = relation_explorer.explore_relations(topic_entity)
    
    print(f"Top relations for {topic_entity.name}:")
    for i, relation in enumerate(relations, 1):
        score = relation.metadata.get("relevance_score", 0.0)
        source = relation.metadata.get("source_name", "Unknown")
        target = relation.metadata.get("target_name", "Unknown")
        print(f"{i}. {source} -[{relation.type}]-> {target}, Score: {score:.2f}")
    
    # Example of entity exploration with relations
    print("\n=== ENTITY EXPLORATION WITH RELATIONS ===")
    entity_explorer = Neo4jEntityExplorer(
        llm=llm,
        kg=kg,
        query=query,
        prune_prompt=prune_prompt,
        max_entities_per_round=3,
        prompt_params=prompt_params
    )

    # Use the relations identified above for entity exploration
    if relations:
        # Explore and prune connected entities
        entity_relation_tuples = entity_explorer.explore_with_relations(topic_entity, relations)
        
        # Enrich entity metadata
        enriched_tuples = entity_explorer.batch_get_entity_metadata(entity_relation_tuples)
        
        # Print results with detailed information
        print(f"\nTop entity-relation tuples relevant to '{query}':")
        for i, (source, relation, target) in enumerate(enriched_tuples, 1):
            score = target.metadata.get("relevance_score", 0.0)
            source_desc = f"{source.name} ({source.type})"
            if source.metadata.get("description"):
                source_desc += f": {source.metadata.get('description', '')[:50]}..."
                
            target_desc = f"{target.name} ({target.type})"
            if target.metadata.get("description"):
                target_desc += f": {target.metadata.get('description', '')[:50]}..."
                
            print(f"{i}. {source_desc} -[{relation.type}]-> {target_desc}")
            print(f"   Relevance Score: {score:.2f}")
            
            # Print additional metadata if available
            if "evidence" in target.metadata:
                print(f"   Evidence: {target.metadata['evidence']}")
            print()
    else:
        print("No relations found for further entity exploration.")
    
    # # Example of direct entity exploration without relation context
    # print("\n=== DIRECT ENTITY EXPLORATION ===")
    # related_entities = entity_explorer._get_related_entities(topic_entity)
    # pruned_entities = entity_explorer._prune_entities(related_entities)
    
    # print(f"Top entities directly related to {topic_entity.name}:")
    # for i, entity in enumerate(pruned_entities, 1):
    #     score = entity.metadata.get("relevance_score", 0.0)
    #     description = entity.metadata.get("description", "No description available")
    #     print(f"{i}. {entity.name} ({entity.type}), Score: {score:.2f}")
    #     print(f"   Description: {description[:100]}..." if len(description) > 100 else f"   Description: {description}")
    #     print()
    
    # Print summary
    # print("\n=== SUMMARY ===")
    # print(f"Query: {query}")
    # print(f"Topic Entity: {topic_entity.name}")
    # print(f"Identified {len(relations)} relevant relations")
    # if 'entity_relation_tuples' in locals():
    #     print(f"Explored {len(entity_relation_tuples)} entity-relation tuples")
    # print(f"Found {len(pruned_entities)} directly related entities")
    # print("\nExploration complete!")