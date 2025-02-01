import os
from openai import AzureOpenAI as Client
from .BaseLLM import BaseLLM
from typing import List, Dict, Any, Union
from ..logging_config import logger
from .prompts import Prompts
from .utils import format_relations, format_paths, format_relations_for_pruning, format_path_string

class AzureOpenAILLM(BaseLLM):
    def __init__(self, model_name: str):
        self.model_name = model_name  # Store the model name
        try:
            self.client = Client(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-15-preview",
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            logger.info(f"Initialized Azure OpenAI client with model: {model_name}")
        except Exception as e:
            logger.error(f"Error initializing Azure OpenAI client: {str(e)}")
            raise

    def _get_completion(self, prompt: str, temperature: float = 0.0) -> str:
        logger.info(f"Getting completion for prompt: {prompt}")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            logger.info(f"Got completion response: {response.choices[0].message.content}")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in getting completion: {str(e)}")
            return ""

    def extract_initial_entities(self, query: str, top_n: int = 5) -> List[str]:
        """
        Extract top-N initial topic entities from the input query.
        
        Args:
            query (str): Input query
            top_n (int): Maximum number of topic entities to extract
            
        Returns:
            List[str]: List of entity names, limited to top_n entries
        """
        logger.info(f"Extracting top-{top_n} initial entities for query: {query}")
        prompt = str(Prompts.EXTRACT_ENTITIES).format(query=query, top_n=top_n)
        response = self._get_completion(prompt)
        entities = [entity.strip() for entity in response.split(',')][:top_n]
        logger.info(f"Extracted entities: {entities}")
        return entities

    def generate_prompt(self, entities: List[str], relations: List[Dict[str, Any]]) -> str:
        """
        Generate a natural language prompt using entities and relations.
        
        Args:
            entities (List[str]): List of entity IDs
            relations (List[Dict[str, Any]]): List of relations
            
        Returns:
            str: Generated prompt
        """
        logger.info(f"Generating prompt for entities: {entities} and relations: {relations}")
        entities_str = ", ".join(entities)
        relations_str = format_relations(relations)
        
        prompt = str(Prompts.GENERATE_NATURAL_LANGUAGE).format(
            entities_str=entities_str,
            relations_str=relations_str
        )
        return self._get_completion(prompt)

    def execute_beam_search(self, query: str, paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute beam search to expand reasoning paths.
        
        Args:
            query (str): Input query
            paths (List[Dict[str, Any]]): Current reasoning paths
            
        Returns:
            List[Dict[str, Any]]: Expanded paths
        """
        logger.info(f"Executing beam search for query: {query} with paths: {paths}")
        paths_str = format_paths(paths)
        
        prompt = str(Prompts.BEAM_SEARCH).format(
            query=query,
            paths_str=paths_str
        )
        response = self._get_completion(prompt)
        return [step.strip() for step in response.split(',')]

    def prune_relations(self, relations: List[Dict[str, Any]], path: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Prunes and ranks relations based on relevance to the current path.
        
        Args:
            relations: List of available relations
            path: Current path (single triple or list of triples)
            
        Returns:
            List[Dict[str, Any]]: Pruned and ranked relations
        """
        if not relations:
            return []
            
        path_str = format_path_string(path)
        relations_str = format_relations_for_pruning(relations)
        
        prompt = str(Prompts.PRUNE_RELATIONS).format(
            path_str=path_str,
            relations_str=relations_str
        )
        
        response = self._get_completion(prompt)
        if not response:
            return []
            
        # Parse relation IDs from response
        relation_ids = [rid.strip() for rid in response.split(',')]
        
        # Filter and sort relations based on response
        pruned_relations = []
        for rid in relation_ids:
            for rel in relations:
                if rel['id'] == rid:
                    pruned_relations.append(rel)
                    break
                    
        return pruned_relations

    def evaluate_paths(self, query:str, paths: List[Dict[str, Any]]) -> bool:
        """
        Evaluate if the current paths are sufficient to answer the query.
        
        Args:
            paths (List[Dict[str, Any]]): Current reasoning paths
            
        Returns:
            bool: True if paths are sufficient, False otherwise
        """
        logger.info(f"Evaluating paths: {paths}")
        paths_str = format_paths(paths)
        
        prompt = str(Prompts.EVALUATE_PATHS).format(paths_str=paths_str, query=query)
        response = self._get_completion(prompt).lower()
        logger.info(f"Got evaluation response: {response}")
        return response.startswith('yes')

    def generate_answer(self, query, paths: List[Dict[str, Any]]) -> str:
        """
        Generate a final answer from the selected paths.
        
        Args:
            paths (List[Dict[str, Any]]): Final reasoning paths
            
        Returns:
            str: Generated answer
        """
        logger.info(f"Generating answer for paths: {paths}")
        paths_str = format_paths(paths)
        
        prompt = str(Prompts.GENERATE_ANSWER).format(paths_str=paths_str, query=query)
        return self._get_completion(prompt, temperature=0.7)