import openai
import json

from .BaseLLM import BaseLLM

class OpenAILLM(BaseLLM):
    def __init__(self, model_name, api_key):
        """
        Initialize OpenAI Language Model
        
        :param model_name: Name of the OpenAI model to use
        :param api_key: OpenAI API key
        """
        super().__init__(model_name, api_key)
        openai.api_key = api_key

    def extract_initial_entities(self, query):
        """
        Extract initial entities from the input query using OpenAI
        
        :param query: Input query string
        :return: List of extracted entities
        """
        prompt = f"""Extract key entities from the following query. 
        Return a JSON list of entities.

        Query: {query}
        
        Entities:"""

        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an entity extraction assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        try:
            entities = json.loads(response.choices[0].message.content)
            return entities.get('entities', [])
        except (json.JSONDecodeError, KeyError):
            return []

    def generate_prompt(self, entities, relations):
        """
        Generate a natural language prompt using entities and relations
        
        :param entities: List of entities
        :param relations: List of relations
        :return: Generated prompt string
        """
        prompt = "Based on the following entities and relations:\n"
        
        for entity in entities:
            prompt += f"Entity: {entity}\n"
        
        for relation in relations:
            prompt += f"Relation: {relation['relation']} between {relation['from_entity']} and {relation['to_entity']}\n"
        
        prompt += "\nGenerate a comprehensive explanation connecting these entities."
        
        return prompt

    def execute_beam_search(self, query, paths):
        """
        Execute beam search to expand reasoning paths
        
        :param query: Original query
        :param paths: Current reasoning paths
        :return: Expanded paths
        """
        expanded_paths = []
        
        for path in paths:
            prompt = f"""You are a reasoning assistant. 
            Given the current reasoning path: {path}
            And the original query: {query}
            
            Suggest the most promising next steps to expand this path."""

            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a strategic reasoning assistant."},
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse and expand paths based on the response
            path_expansion = response.choices[0].message.content
            # This is a simplified version - you'd need more complex logic to truly expand paths
            expanded_paths.append(path + [path_expansion])
        
        return expanded_paths

    def prune_relations(self, relations, path):
        """
        Rank and prune relations based on query relevance
        
        :param relations: List of relations to prune
        :param path: Current reasoning path
        :return: Pruned relations
        """
        # Create a prompt to evaluate and rank relations
        prompt = f"""Given the current reasoning path: {path}
        And the following possible relations: {relations}
        
        Rank these relations from most to least relevant, 
        considering their potential to lead to an answer."""

        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a relation relevance ranker."},
                {"role": "user", "content": prompt}
            ]
        )

        # Parse the response and return top relations
        pruned_relations = []
        for relation in relations:
            if relation not in pruned_relations:
                pruned_relations.append(relation)
                if len(pruned_relations) == 3:  # Limit to top 3 relations
                    break
        
        return pruned_relations

    def evaluate_paths(self, query, paths):
        """
        Evaluate if the current paths are sufficient to answer the query
        
        :param paths: Current reasoning paths
        :return: Boolean indicating if paths are sufficient
        """
        prompt = f"""Evaluate these reasoning paths:
        {query}
        {paths}
        
        Determine if they are sufficiently comprehensive 
        to construct a definitive answer. 
        Respond with YES or NO."""

        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a path evaluation expert."},
                {"role": "user", "content": prompt}
            ]
        )

        return "YES" in response.choices[0].message.content.upper()

    def generate_answer(self, paths):
        """
        Generate a final answer from the selected paths
        
        :param paths: Selected reasoning paths
        :return: Generated answer
        """
        prompt = f"""Using the following reasoning paths:
        {paths}
        
        Construct a comprehensive, coherent answer 
        that explains the reasoning process."""

        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an answer generation expert."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content