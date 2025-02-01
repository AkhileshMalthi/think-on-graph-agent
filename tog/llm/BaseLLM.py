from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def __init__(self):
        pass
    
    @abstractmethod
    def extract_initial_entities(self, query):
        """Extracts initial entities from the input query."""
        pass

    @abstractmethod
    def generate_prompt(self, entities, relations):
        """Generates a natural language prompt using entities and relations."""
        pass

    @abstractmethod
    def execute_beam_search(self, query, paths):
        """Executes beam search to expand reasoning paths."""
        pass

    @abstractmethod
    def prune_relations(self, query, relations, path):
        """Ranks and prunes relations based on query relevance."""
        pass

    @abstractmethod
    def evaluate_paths(self, query, paths):
        """Evaluates if the current paths are sufficient to answer the query."""
        pass

    @abstractmethod
    def generate_answer(self, query, paths):
        """Generates a final answer from the selected paths."""
        pass
