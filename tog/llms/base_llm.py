from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseLLM(ABC):
    """
    Abstract base class for all LLM implementations.
    All LLM models in the project should inherit from this class.
    """
    
    @abstractmethod
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize the LLM with a model name and any additional parameters.
        
        Args:
            model_name: The name of the model to use
            **kwargs: Additional model-specific configuration parameters
        """
        self.model_name = model_name
        self.model_params = kwargs
    
    @abstractmethod
    def generate(self, messages: List[Dict], **kwargs) -> str:
        """
        Generate a response for the given messages.
        
        Args:
            messages: List of message dictionaries representing the conversation
            **kwargs: Additional generation parameters
            
        Returns:
            The generated text response
        """
        pass
    
    @abstractmethod
    def generate_stream(self, messages: List[Dict], **kwargs):
        """
        Stream the response for the given messages.
        
        Args:
            messages: List of message dictionaries representing the conversation
            **kwargs: Additional generation parameters
            
        Returns:
            An async generator yielding chunks of the generated response
        """
        pass
    
    @abstractmethod
    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        """
        Generate responses for multiple prompts in batch mode.
        
        Args:
            prompts: A list of prompts to generate responses for
            **kwargs: Additional generation parameters
            
        Returns:
            A list of generated text responses
        """
        pass
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """
        Return information about the loaded model.
        
        Returns:
            A dictionary containing model information
        """
        return {
            "model_name": self.model_name,
            "model_params": self.model_params
        }