from typing import List
import logging

from tog.llms import BaseLLM
from tog.kgs import KnowledgeGraph
from tog.models.entity import Entity
from tog.models.triple import Triple
from tog.models.path import Path, TopNPaths

from tog.pipeline.entity_explorer import EntityExplorer
from tog.pipeline.relation_explorer import RelationExplorer

class ExplorationLoop:
    """
    Main class for implementing the end-to-end exploration loop process.
    Iteratively discovers entities and relationships, ranks them, and 
    determines if enough information is available to answer a query.
    """
    
    def __init__(self, 
                 llm: BaseLLM, 
                 kg: KnowledgeGraph,
                 entity_explorer: EntityExplorer,
                 relation_explorer: RelationExplorer,
                 query: str,
                 max_iterations: int = 3,
                 max_paths: int = 5,
                 system_prompt: str = None):
        """
        Initialize the exploration loop.
        
        Args:
            llm: Language model for exploration and verification
            kg: Knowledge graph to explore
            entity_explorer: Explorer for entity discovery
            relation_explorer: Explorer for relation discovery
            query: User query to answer
            max_iterations: Maximum number of exploration iterations
            max_paths: Maximum number of paths to maintain
            system_prompt: System prompt for LLM
        """
        self.llm = llm
        self.kg = kg
        self.entity_explorer = entity_explorer
        self.relation_explorer = relation_explorer
        self.query = query
        self.max_iterations = max_iterations
        self.max_paths = max_paths
        self.system_prompt = system_prompt or "You are a helpful assistant specialized in knowledge graph exploration."
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize top paths collection
        self.top_paths = TopNPaths(n=max_paths)
    
    def explore(self, initial_entities: List[Entity]) -> List[Path]:
        """
        Execute the exploration loop starting from initial entities.
        
        Args:
            initial_entities: List of entities to start exploration from
            
        Returns:
            List of best paths found during exploration
        """
        self.logger.info(f"Starting exploration loop for query: {self.query}")
        
        # Step 1: Initialize paths with topic entities
        current_paths = self._initialize_paths(initial_entities)
        print(f"Initialized {len(current_paths)} paths from initial entities")
        print("Current paths:", current_paths)
        self.logger.debug(f"Initialized paths: {current_paths}")
        
        # Main exploration loop
        for iteration in range(self.max_iterations):
            self.logger.info(f"Starting iteration {iteration+1}/{self.max_iterations}")
            
            # Step 2: Explore relations for each entity in current paths
            paths_with_relations = self._explore_relations(current_paths)
            
            # Step 3: Explore entities for each relation
            new_paths = self._explore_entities(paths_with_relations)
            
            # Step 4: Rank paths and select top-N
            current_paths = self._rank_and_select_paths(new_paths)
            
            # Step 5: Check if knowledge is sufficient
            if self._is_knowledge_sufficient(current_paths):
                self.logger.info("Found sufficient knowledge to answer query")
                break
                
        return self.top_paths.get_paths()
    
    def _initialize_paths(self, initial_entities: List[Entity]) -> List[Path]:
        """
        Initialize paths with the topic entities from the user query.
        
        Args:
            initial_entities: List of entities to start with
            
        Returns:
            List of initial paths
        """
        paths = []
        
        for entity in initial_entities:
            # Create a "dummy" triple with the entity as both subject and object
            # This is because at iteration 0, we don't have real triples yet
            triple = Triple(
                subject=entity,
                predicate=None,
                object=entity
            )
            
            # Create a path with this triple
            path = Path()
            path.add_triple(triple)  # This will automatically add entity to visited_entities
            path.set_confidence_score(1.0)  # Initial confidence is high
            
            paths.append(path)
            
        self.logger.debug(f"Initialized {len(paths)} paths from query entities")
        return paths

    
    def _explore_relations(self, current_paths: List[Path]) -> List[Path]:
        """
        Explore relations for the last entity in each path.
        
        Args:
            current_paths: List of current paths to extend
            
        Returns:
            List of paths extended with relations
        """
        paths_with_relations = []
        
        for path in current_paths:
            # Get the last entity in the path
            last_entity = path.get_last_entity()
            if not last_entity:
                continue
            
            # Get visited entities from this path
            visited_entities = path.copy_visited_entities()
                
            # Explore relations for this entity, avoiding visited entities
            relations = self.relation_explorer.explore_relations(last_entity, visited_entities)
            
            # For each relation, create a new path
            for relation in relations:
                new_path = Path()
                
                # Copy visited entities from original path
                new_path.visited_entities = visited_entities.copy()
                
                # Copy all triples from the original path
                for triple in path.path:
                    new_path.add_triple(triple)
                
                # Add metadata
                new_path.metadata = path.metadata.copy()
                
                # For now, set the path with a placeholder relation
                # This will be replaced in the entity exploration step
                placeholder_triple = Triple(
                    subject=last_entity,
                    predicate=relation,
                    object=None  # Will be filled in _explore_entities
                )
                
                new_path.add_triple(placeholder_triple)
                
                # Use relation's relevance score as path score for now
                score = relation.metadata.get("relevance_score", 0.5)
                new_path.set_confidence_score(score)
                
                paths_with_relations.append(new_path)
        
        self.logger.debug(f"Created {len(paths_with_relations)} paths with relations")
        return paths_with_relations
    
    def _explore_entities(self, paths_with_relations: List[Path]) -> List[Path]:
        """
        Explore target entities for each relation in the paths.
        
        Args:
            paths_with_relations: List of paths with relations to explore
            
        Returns:
            List of paths with both relations and target entities
        """
        complete_paths = []
        
        for path in paths_with_relations:
            # Get the last triple (which has a placeholder target entity)
            last_triple = path.path[-1] if path.path else None
            if not last_triple or not last_triple.predicate:
                continue
                
            # Get the source entity and relation
            source_entity = last_triple.subject
            relation = last_triple.predicate
            
            # Get visited entities from this path
            visited_entities = path.copy_visited_entities()
            
            # Find target entities for this relation, avoiding visited entities
            tuples = self.entity_explorer.explore_entities(source_entity, [relation], visited_entities)
            
            # Filter to only keep tuples where the relation matches
            relevant_tuples = [
                (s, r, t) for s, r, t in tuples 
                if r.id == relation.id
            ]
            
            # If no target entities found, skip this path
            if not relevant_tuples:
                continue
                
            # For each target entity, create a new path
            for source_ent, rel, target_entity in relevant_tuples:
                new_path = Path()
                
                # Copy visited entities from original path
                new_path.visited_entities = visited_entities.copy()
                
                # Copy all triples except the last one (which had a placeholder)
                for i, triple in enumerate(path.path):
                    if i < len(path.path) - 1:
                        new_path.add_triple(triple)
                
                # Add metadata
                new_path.metadata = path.metadata.copy()
                
                # Create a complete triple with the target entity
                complete_triple = Triple(
                    subject=source_entity,
                    predicate=relation,
                    object=target_entity
                )
                
                new_path.add_triple(complete_triple)  # This will add target_entity to visited_entities
                
                # Calculate combined score
                relation_score = relation.metadata.get("relevance_score", 0.5)
                entity_score = target_entity.metadata.get("relevance_score", 0.5)
                combined_score = (relation_score + entity_score) / 2
                
                new_path.set_confidence_score(combined_score)
                
                # Add to the top paths collection
                self.top_paths.add_path(new_path, combined_score)
                complete_paths.append(new_path)
        
        self.logger.debug(f"Created {len(complete_paths)} complete paths with target entities")
        return complete_paths
        
    def _rank_and_select_paths(self, paths: List[Path]) -> List[Path]:
        """
        Rank paths by score and select top-N.
        
        Args:
            paths: List of paths to rank
            
        Returns:
            Top-N paths
        """
        # All paths should be in self.top_paths already
        # Just return the current top paths
        return self.top_paths.get_paths()
    
    def _is_knowledge_sufficient(self, paths: List[Path]) -> bool:
        """
        Check if the knowledge gathered is sufficient to answer the query.
        
        Args:
            paths: List of top paths to check
            
        Returns:
            True if knowledge is sufficient, False otherwise
        """
        # If no paths, knowledge is not sufficient
        if not paths:
            return False
            
        # Format paths for LLM
        paths_text = ""
        for i, path in enumerate(paths, 1):
            path_str = " → ".join([
                f"{triple.subject.name}" + 
                (f" -{triple.predicate.type}→ {triple.object.name}" if triple.predicate and triple.object else "")
                for triple in path.path
            ])
            paths_text += f"{i}. {path_str} (Confidence: {path.confidence_score:.2f})\n"
        
        # Prepare LLM prompt
        prompt = f"""
        Please determine if the following knowledge graph paths provide sufficient information to answer the query.
        
        QUERY: {self.query}
        
        KNOWLEDGE PATHS:
        {paths_text}
        
        Is this information sufficient to provide a comprehensive answer to the query?
        Please respond with only "SUFFICIENT" or "INSUFFICIENT" followed by a brief explanation.
        """
        
        # Call LLM for verification
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.generate(messages, temperature=0.3)
        
        # Check if response indicates sufficient knowledge
        is_sufficient = "SUFFICIENT" in response.upper()
        
        self.logger.info(f"Knowledge sufficiency check: {is_sufficient}")
        return is_sufficient