import os
from pprint import pprint
from typing import Dict, Any, List
from groq import Groq
from tog.llms.base_llm import BaseLLM
from dotenv import load_dotenv

class GroqLLM(BaseLLM):
    """
    Groq LLM implementation that uses the Groq API service.
    """
    
    def __init__(self, model_name: str = None, api_key: str = None, **kwargs):
        """
        Initialize Groq client with the given model configuration.
        
        Args:
            model_name: The name of the model to use
            api_key: The Groq API key (defaults to environment variable if not provided)
            **kwargs: Additional model-specific configuration parameters
        """
        load_dotenv()  # Load environment variables from .env file
        
        super().__init__(model_name, **kwargs)
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        self.model_name = model_name or os.getenv("GROQ_MODEL_NAME")
    
    def generate(self, messages: List[Dict], **kwargs) -> str:
        """
        Generate a response for the given prompt using Groq.
        
        Args:
            messages: List of message dictionaries representing the conversation
            **kwargs: Additional generation parameters
            
        Returns:
            The generated text response
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        # pprint(response)
        return response.choices[0].message.content
    
    def generate_stream(self, messages: List[Dict], **kwargs):
        """
        Stream the response for the given prompt using Groq.
        
        Args:
            messages: List of message dictionaries representing the conversation
            **kwargs: Additional generation parameters
            
        Returns:
            A generator yielding chunks of the generated response
        """
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **kwargs
        )
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        """
        Generate responses for multiple prompts in batch mode using Groq.
        
        Args:
            prompts: A list of prompts to generate responses for
            **kwargs: Additional generation parameters
            
        Returns:
            A list of generated text responses
        """
        results = []
        for prompt in prompts:
            result = self.generate(prompt, **kwargs)
            results.append(result)
        return results
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """
        Return information about the loaded model.
        
        Returns:
            A dictionary containing model information
        """
        info = super().model_info
        info.update({
            "service": "Groq"
        })
        return info

# Example usage
if __name__ == "__main__":
    # Initialize the GroqLLM with a specific model
    llm = GroqLLM("mixtral-8x7b-32768")

    messages = [{"role": "user", "content": "Explain quantum computing in simple terms."}]
    
    # Simple generation example
    response = llm.generate(
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )
    print("Generated response:")
    print(response)
    print("\n" + "-"*50 + "\n")

