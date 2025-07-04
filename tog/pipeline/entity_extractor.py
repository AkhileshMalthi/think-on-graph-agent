from abc import ABC, abstractmethod
from pprint import pprint
from typing import List

from tog.llms.base_llm import BaseLLM
from tog.llms.groq_llm import GroqLLM
from tog.llms.azure_openai_llm import AzureOpenAILLM
from tog.models.entity import Entity
import json

from tog.utils import PromptLoader
from tog.models.response import ExtractionResponse
from tog.utils.logger import console_logger as logger

class EntityExtractor(ABC):
    @abstractmethod
    def extract_entities(self, messages: str) -> List[str]:
        """Extract entities from the given text."""
        pass

class LLMExtractor(EntityExtractor):
    def __init__(self, model_name: str):
        logger.info(f"Initializing LLMExtractor with model: {model_name}")
        self.llm: BaseLLM = self.initialize_llm(model_name)
        self.prompt_loader = PromptLoader()

    @abstractmethod
    def initialize_llm(self) -> BaseLLM:
        pass

    def extract_entities(self, text: str) -> List[str]:
        logger.debug(f"Extracting entities from text: {text[:50]}...")
        
        # Get the extraction prompt
        prompt = self.prompt_loader.get_prompt("extraction_prompt")
        logger.debug("Loaded extraction prompt")

        # Extract the system and user prompts
        system_prompt = prompt["system"]
        user_prompt = prompt["user"].replace("{query}", text) # Replace placeholder with input text

        # Call the LLM with the formatted prompt
        logger.info("Calling LLM for entity extraction")
        response = self.llm.generate([{"role": "system", "content": system_prompt},
                                      {"role": "user", "content": user_prompt}])

        # Parse the response using the ExtractionResponse model
        try:
            # Use the helper method to parse the extraction output
            extraction_response = ExtractionResponse.from_extraction_output(response)
            
            # Just return the list of entity strings directly
            entities = extraction_response.entities
            logger.info(f"Successfully extracted {len(entities)} entities")
            logger.debug(f"Extracted entities: {entities}")
        except Exception as e:
            # Handle parsing errors
            logger.error(f"Failed to parse extraction response: {str(e)}")
            raise ValueError(f"Failed to parse extraction response: {e}")
            
        return entities
    
class GroqEntityExtractor(LLMExtractor):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        logger.info(f"Initializing GroqEntityExtractor with model: {model_name}")
        self.api_key = api_key
        self.kwargs = kwargs
        super().__init__(model_name)

    def initialize_llm(self, model_name) -> BaseLLM:
        logger.debug(f"Creating GroqLLM instance with model: {model_name}")
        return GroqLLM(
            model_name=model_name,
            api_key=self.api_key,
            **self.kwargs
        )
    
class AzureOpenAIEntityExtractor(LLMExtractor):
    def __init__(self, model_name: str, api_key: str = None, endpoint: str = None, api_version: str = None, **kwargs):
        logger.info(f"Initializing AzureOpenAIEntityExtractor with model: {model_name}")
        self.api_key = api_key
        self.endpoint = endpoint
        self.api_version = api_version
        self.kwargs = kwargs
        super().__init__(model_name)

    def initialize_llm(self, model_name) -> BaseLLM:
        logger.debug(f"Creating AzureOpenAILLM instance with model: {model_name}")
        return AzureOpenAILLM(
            model_name=model_name,
            api_key=self.api_key,
            endpoint=self.endpoint,
            api_version=self.api_version,
            **self.kwargs
        )

if __name__ == '__main__':
    # Example usage
    llm_extractor = GroqEntityExtractor("llama-3.3-70b-versatile")
    sample_text = """OpenAI's GPT-4 was released in March 2023 by Sam Altman's team. The model has 1.76 trillion parameters according to some estimates."""
    
    logger.info("Extracting entities from sample text")
    entities = llm_extractor.extract_entities(sample_text)
    pprint(entities)
    print(len(entities))
    
    llm_extractor = AzureOpenAIEntityExtractor("gpt-4o")
    entities = llm_extractor.extract_entities(sample_text)
    pprint(entities)
    print(len(entities))
