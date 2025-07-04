import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from tog.llms.base_llm import BaseLLM
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
from tog.utils.logger import console_logger as logger


class AzureOpenAILLM(BaseLLM):
    """
    Azure OpenAI LLM implementation that uses the Azure OpenAI service.
    """
    
    def __init__(self, model_name: str, api_key: str = None, 
                endpoint: str = None, api_version: str = None, **kwargs):
        """
        Initialize Azure OpenAI client with the given model configuration.
        
        Args:
            model_name: The name of the model to use
            api_key: The Azure OpenAI API key (defaults to environment variable if not provided)
            endpoint: The Azure OpenAI endpoint (defaults to environment variable if not provided)
            api_version: The Azure OpenAI API version (defaults to environment variable if not provided)
            **kwargs: Additional model-specific configuration parameters
        """
        load_dotenv()

        super().__init__(model_name, **kwargs)
        self.client = AzureOpenAI(
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
        )
        self.model_name = model_name
        logger.info(f"Initializing AzureOpenAILLM with model: {model_name}")
    
    def generate(self, messages: List[Dict], **kwargs) -> str:
        """
        Generate a response for the given prompt using Azure OpenAI.
        
        Args:
            messages: List of message dictionaries with role and content
            **kwargs: Additional generation parameters
            
        Returns:
            The generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            raise
    
    def generate_stream(self, messages: List[Dict], **kwargs):
        """
        Stream the response for the given prompt using Azure OpenAI.
        
        Args:
            messages: List of message dictionaries with role and content
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
        Generate responses for multiple prompts in batch mode using Azure OpenAI.
        
        Args:
            prompts: A list of prompts to generate responses for
            **kwargs: Additional generation parameters
            
        Returns:
            A list of generated text responses
        """
        results = []
        for prompt in prompts:
            messages = [{"role": "user", "content": prompt}]
            result = self.generate(messages, **kwargs)
            results.append(result)
        return results
    
class AsyncAzureOpenAILLM(BaseLLM):
    """
    Azure OpenAI implementation of the BaseLLM interface.
    Handles interactions with Azure OpenAI models.
    """
    
    def __init__(self, 
                 model_name: str,
                 api_key: str = None, 
                 endpoint: str = None,
                 api_version: str = "2023-05-15",
                 deployment_name: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 **kwargs):
        """
        Initialize the Azure OpenAI client.
        
        Args:
            model_name: The name of the model to use
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            api_version: API version to use
            deployment_name: Deployment name (if different from model_name)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            **kwargs: Additional model-specific configuration parameters
        """
        super().__init__(model_name, **kwargs)
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY"),
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
        self.deployment_name = deployment_name or model_name
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize both sync and async clients
        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            timeout=self.timeout
        )
        
        self.async_client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
            timeout=self.timeout
        )
        
    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=10))
    def generate(self, messages: List[Dict], **kwargs) -> str:
        """
        Generate a response for the given messages.
        
        Args:
            messages: List of message dictionaries representing the conversation
                     Each message should have 'role' and 'content' keys
            **kwargs: Additional generation parameters like temperature, max_tokens, etc.
            
        Returns:
            The generated text response
        """
        # Merge default parameters with any provided kwargs
        params = self._get_default_params()
        params.update(kwargs)
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                **params
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            raise
    
    async def generate_stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        """
        Stream the response for the given messages.
        
        Args:
            messages: List of message dictionaries representing the conversation
            **kwargs: Additional generation parameters
            
        Returns:
            An async generator yielding chunks of the generated response
        """
        # Merge default parameters with any provided kwargs
        params = self._get_default_params()
        params.update(kwargs)
        params["stream"] = True
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                **params
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in generate_stream: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(min=1, max=10))
    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        """
        Generate responses for multiple prompts in batch mode.
        
        Args:
            prompts: A list of prompts to generate responses for
            **kwargs: Additional generation parameters
            
        Returns:
            A list of generated text responses
        """
        results = []
        # Merge default parameters with any provided kwargs
        params = self._get_default_params()
        params.update(kwargs)
        
        try:
            # Process each prompt individually but in a batch way
            for prompt in prompts:
                messages = [{"role": "user", "content": prompt}]
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    **params
                )
                results.append(response.choices[0].message.content)
            return results
        except Exception as e:
            logger.error(f"Error in batch_generate: {str(e)}")
            raise
    
    def _get_default_params(self) -> Dict[str, Any]:
        """
        Get default parameters for completion requests.
        
        Returns:
            A dictionary of default parameters
        """
        return {
            "temperature": 0.7,
            "max_tokens": 800,
            "top_p": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """
        Return information about the loaded model.
        
        Returns:
            A dictionary containing model information
        """
        info = super().model_info
        info.update({
            "endpoint": self.endpoint,
            "api_version": self.api_version,
            "deployment_name": self.deployment_name,
        })
        return info
    
if __name__ == "__main__":
    # Example usage
    llm = AzureOpenAILLM(model_name="gpt-4o")
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    response = llm.generate(messages)
    print(response)
    print(llm.model_info)
    print(llm.generate_stream(messages))
    print(llm.batch_generate(["Hello, how are you?", "What is the weather today?"]))

    # TODO: Async AzureOpenAILLM rasing error

    # llm_async = AsyncAzureOpenAILLM(model_name="gpt-4o")
    # messages = [{"role": "user", "content": "Hello, how are you?"}]
    # response = llm_async.generate(messages)
    # print(response)
    # print(llm_async.model_info)
    # print(llm_async.generate_stream(messages))
    # print(llm_async.batch_generate(["Hello, how are you?", "What is the weather today?"]))