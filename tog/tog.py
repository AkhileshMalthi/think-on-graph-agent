import os
from .kg.visualization import visualize_graph
from typing import Dict, List, Any, Tuple
import numpy as np
from .logging_config import logger
from .llm import AzureOpenAILLM
from .kg import NetworkxKG

class ThinkOnGraph:
    def __init__(self, llm=AzureOpenAILLM, kg=NetworkxKG, beam_width=3, max_depth=3, top_n_entities=5):
        """
        Initializes the ToG framework.
        :param llm: Instance of LLM manager.
        :param kg: Instance of KG manager.
        :param beam_width: Number of paths to retain at each iteration.
        :param max_depth: Maximum search depth.
        :param top_n_entities: Number of top-N topic entities to consider (N).
        """
        self.llm = llm
        self.kg = kg
        self.beam_width = beam_width
        self.max_depth = max_depth
        self.top_n_entities = top_n_entities
        self.paths = []
        self.visited_entities = set()
        logger.info("ToG framework initialized.")

    def _find_similar_entities(self, query: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Finds similar entities in the graph using vector similarity.
        """
        query_embedding = self.kg.model.encode(query, convert_to_tensor=False)
        similar_entities = []

        for node_id, data in self.kg.graph.nodes(data=True):
            if "embeddings" in data:
                max_similarity = 0
                for field_embedding in data["embeddings"].values():
                    similarity = np.dot(query_embedding, field_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(field_embedding)
                    )
                    max_similarity = max(max_similarity, similarity)
                
                if max_similarity >= threshold:
                    similar_entities.append((node_id, float(max_similarity)))

        return sorted(similar_entities, key=lambda x: x[1], reverse=True)

    def retrieve_initial_triples(self, entities: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves initial triples for the given entities using similarity search.
        """
        triples = []
        logger.info(f"Retrieving initial triples for entities: {entities}")
        
        for entity_query in entities:
            similar_entities = self._find_similar_entities(entity_query)
            
            for entity_id, similarity_score in similar_entities:
                source_name = self.kg.graph.nodes[entity_id]['name']
                
                for _, target, key in self.kg.graph.out_edges(entity_id, keys=True):
                    edge_data = self.kg.graph.get_edge_data(entity_id, target, key)
                    target_name = self.kg.graph.nodes[target]['name']
                    
                    triple = {
                        "subject": source_name,
                        "predicate": edge_data["type"],
                        "object": target_name,
                        "metadata": edge_data.get("metadata", {}),
                        "similarity_score": similarity_score,
                        "_subject_id": entity_id,
                        "_object_id": target
                    }
                    triples.append(triple)
        
        return triples

    def retrieve_relations(self, entity: str) -> List[Dict[str, Any]]:
        """
        Retrieves relationships for the given entity.
        """
        relations = []
        for _, target, key, data in self.kg.graph.out_edges(entity, keys=True, data=True):
            relation = {
                "id": data["id"],
                "type": data["type"],
                "target_id": target,
                "target_name": self.kg.graph.nodes[target]["name"],
                "metadata": data.get("metadata", {})
            }
            relations.append(relation)
        return relations

    def initialize_search(self, query):
        """
        Extracts initial top-N entities and retrieves corresponding triples from the KG.
        """
        logger.info(f"Initializing search for query: {query}")
        # Get initial topic entities (E0)
        initial_entities = self.llm.extract_initial_entities(query, self.top_n_entities)
        if not initial_entities:
            logger.warning("No initial entities extracted.")
            raise ValueError("No initial entities extracted.")
        
        logger.info(f"Extracted top-{len(initial_entities)} initial entities: {initial_entities}")
        
        # Initialize reasoning paths P with triples from initial entities
        self.paths = self.retrieve_initial_triples(initial_entities)
        if not self.paths:
            logger.warning("No initial triples found.")
            return []
        
        # Add initial entities to visited set
        for path in self.paths:
            if '_subject_id' in path:
                self.visited_entities.add(path['_subject_id'])
            if '_object_id' in path:
                self.visited_entities.add(path['_object_id'])
                
        # Keep only top beam_width paths based on similarity scores
        self.paths = sorted(self.paths, key=lambda x: x['similarity_score'], reverse=True)[:self.beam_width]
        
        logger.debug(f"Initial paths: {self.paths}")
        return self.paths

    def explore_and_prune(self, paths):
        """Expands and prunes paths by exploring neighboring entities and relations."""
        logger.info(f"Exploring and pruning paths: {paths}")
        all_expanded_paths = []
        
        # Convert single triple to list if necessary
        current_paths = paths if isinstance(paths, list) else [paths]
        
        for path in current_paths:
            # Get the last triple's object ID
            entity_id = path['_object_id']
            relations = self.retrieve_relations(entity_id)
            
            if not relations:
                logger.debug(f"No relations found for entity {path['object']}")
                continue
                
            logger.debug(f"Relations for entity {path['object']}: {relations}")
            
            # Create path context for pruning
            path_context = current_paths if isinstance(paths, list) else path
            pruned_relations = self.llm.prune_relations(relations, path_context)
            
            if not pruned_relations:
                logger.debug(f"No pruned relations for entity {path['object']}")
                continue
                
            logger.debug(f"Pruned relations for entity {path['object']}: {pruned_relations}")
            
            for relation in pruned_relations:
                target_id = relation["target_id"]
                if target_id not in self.visited_entities:
                    # Create new path by extending the current path
                    new_path = current_paths.copy() if isinstance(paths, list) else []
                    new_triple = {
                        "subject": path["object"],
                        "predicate": relation["type"],
                        "object": relation["target_name"],
                        "metadata": relation.get("metadata", {}),
                        "_subject_id": entity_id,
                        "_object_id": target_id
                    }
                    
                    if isinstance(paths, list):
                        new_path.append(new_triple)
                    else:
                        new_path = [path, new_triple]
                        
                    all_expanded_paths.append(new_path)
                    logger.debug(f"Expanded path: {all_expanded_paths[-1]}")
                    self.visited_entities.add(target_id)
        
        # Sort expanded paths by relevance if any exist
        if all_expanded_paths:
            return all_expanded_paths[:self.beam_width]
        return []

    def evaluate_paths(self, query, paths):
        """Determines if the current paths are sufficient to generate an answer."""
        if not paths:
            logger.warning("No paths to evaluate.")
            return False
        return self.llm.evaluate_paths(query, paths)

    def generate_answer(self, query, paths):
        """Generates an answer using the current reasoning paths."""
        return self.llm.generate_answer(query, paths)

    def run(self, query):
        """Runs the complete Think-on-Graph reasoning process."""
        logger.info(f"Running ToG process for query: {query}")
        
        try:
            self.paths = self.initialize_search(query)
        except ValueError as e:
            logger.error(f"Error initializing search: {e}")
            return str(e)
            
        if not self.paths:
            logger.warning("No initial paths found.")
            return "Unable to find relevant information to answer the query."
            
        current_paths = self.paths
        depth = 0
        
        while depth < self.max_depth:
            logger.debug(f"Current depth: {depth}, paths: {current_paths}")
            
            # Check if current paths are sufficient
            if self.evaluate_paths(query, current_paths):
                answer = self.generate_answer(query, current_paths)
                logger.info(f"Generated answer: {answer}")
                return answer
            
            # Explore and prune paths
            expanded_paths = self.explore_and_prune(current_paths)
            
            if not expanded_paths:
                # If we have current paths but no expansions, try generating an answer
                if current_paths:
                    logger.info("No more paths to explore, generating answer from current paths")
                    return self.generate_answer(query, current_paths)
                logger.warning("No paths found after pruning.")
                break
                
            current_paths = expanded_paths
            depth += 1
            
        # If we reached max depth, try to generate answer from final paths
        if current_paths:
            logger.info("Reached maximum depth, generating answer from final paths")
            return self.generate_answer(query, current_paths)
            
        logger.warning("Unable to derive an answer.")
        return "Unable to find sufficient information to answer the query."
    
    
if __name__ == '__main__':

    from tog.llm import AzureOpenAILLM
    from tog.kg import NetworkxKG

    llm = AzureOpenAILLM(model_name='gpt-4o')

    kg = NetworkxKG(
        graph_endpoint='knowledge_graph.json',
    )
    visualize_graph(kg.graph)

    tog = ThinkOnGraph(llm=llm, kg=kg, beam_width=3, max_depth=5)
    response = tog.run("Name a researcher involved in the study of Cannabidiol's therapeutic effects") 
    print(response)