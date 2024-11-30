import json
import re
from typing import Dict, List, Any, Callable, Union
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
from prompts import PROMPTS

# Load environment variables
load_dotenv()

# Detailed system and extraction prompts
system_prompt: str = PROMPTS['system_prompt']
extraction_prompt: str = PROMPTS['entity_extraction']

class OpenAIExtractor:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """
        Initialize the advanced OpenAI extractor with robust configuration.
        
        :param model: OpenAI model for extraction
        """
        self.model: str = model
        self.client: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def extract(self, text: str) -> Dict[str, List[Any]]:
        """
        Comprehensively extract entities and relationships from text.
        
        :param text: Input text to analyze
        :return: Structured graph data
        """
        try:
            # Prepare detailed extraction prompt
            formatted_prompt: str = extraction_prompt.format(input_text=text)
            
            # Make API request with strict JSON formatting
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0.2  # Low temperature for more deterministic output
            )
            
            # Extract response content
            result_text: str = response.choices[0].message.content
            
            # Comprehensive parsing with multiple fallback strategies
            graph_data: Dict[str, List[Any]] = self._robust_json_parse(result_text)
            
            return graph_data
        
        except Exception as e:
            print("CRITICAL ERROR during extraction:")
            print(traceback.format_exc())
            return {"entities": [], "relationships": []}

    def _robust_json_parse(self, response_text: str) -> Dict[str, List[Any]]:
        """
        Implement multiple parsing strategies for JSON extraction.
        
        :param response_text: Raw text response from OpenAI
        :return: Parsed graph data
        """
        parsing_strategies: List[Callable[[str], Dict[str, List[Any]]]] = [
            self._standard_json_parse,
            self._regex_json_parse,
            self._fallback_json_parse
        ]
        
        for strategy in parsing_strategies:
            try:
                result: Dict[str, List[Any]] = strategy(response_text)
                if result:
                    return result
            except Exception as e:
                print(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        print("ALL JSON PARSING STRATEGIES FAILED")
        return {"entities": [], "relationships": []}

    def _standard_json_parse(self, text: str) -> Dict[str, List[Any]]:
        """Standard JSON parsing method."""
        clean_text: str = text.strip().replace('```json', '').replace('```', '')
        parsed_data: Dict[str, Any] = json.loads(clean_text)
        
        # Validate structure
        if not isinstance(parsed_data, dict):
            raise ValueError("Invalid JSON structure")
        
        parsed_data.setdefault('entities', [])
        parsed_data.setdefault('relationships', [])
        
        return parsed_data

    def _regex_json_parse(self, text: str) -> Dict[str, List[Any]]:
        """Regex-based JSON extraction method."""
        # Extract JSON-like content between first '{' and last '}'
        match: Union[re.Match, None] = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            clean_text: str = match.group(0)
            return self._standard_json_parse(clean_text)
        raise ValueError("No JSON-like structure found")

    def _fallback_json_parse(self, text: str) -> Dict[str, List[Any]]:
        """Extremely lenient parsing as last resort."""
        # Attempt to manually reconstruct JSON
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            return {"entities": [], "relationships": []}
        raise ValueError("Cannot parse JSON")

def main() -> None:
    # Demonstration with multiple test cases
    test_prompts: List[str] = PROMPTS['extraction_test_prompts']
    
    extractor: OpenAIExtractor = OpenAIExtractor()
    
    for text in test_prompts:
        print("\n--- Processing Text: ---\n")
        print(text)
        graph_data: Dict[str, List[Any]] = extractor.extract(text)
        print("Extracted Graph Data:")
        print(json.dumps(graph_data, indent=2))

if __name__ == "__main__":
    main()