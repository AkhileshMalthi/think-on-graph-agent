import json
import re
from openai import OpenAI
import os
import traceback
from dotenv import load_dotenv
from prompts import PROMPTS
# Load environment variables
load_dotenv()

# Detailed system and extraction prompts
system_prompt = PROMPTS['system_prompt']

extraction_prompt = PROMPTS['entity_extraction']

class OpenAIExtractor:
    def __init__(self, model="gpt-4o-mini"):
        """
        Initialize the advanced OpenAI extractor with robust configuration.
        
        :param model: OpenAI model for extraction
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def extract(self, text):
        """
        Comprehensively extract entities and relationships from text.
        
        :param text: Input text to analyze
        :return: Structured graph data
        """
        try:
            # Prepare detailed extraction prompt
            formatted_prompt = extraction_prompt.format(input_text=text)
            
            # print("DEBUG: Sending request to OpenAI")
            # print("DEBUG: Input Text:", text)
            # print("DEBUG: Formatted Prompt:", formatted_prompt)
            
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
            result_text = response.choices[0].message.content
            
            # print("DEBUG: Raw OpenAI Response:")
            # print(result_text)
            
            # Comprehensive parsing with multiple fallback strategies
            graph_data = self._robust_json_parse(result_text)
            
            return graph_data
        
        except Exception as e:
            print("CRITICAL ERROR during extraction:")
            print(traceback.format_exc())
            return {"entities": [], "relationships": []}

    def _robust_json_parse(self, response_text):
        """
        Implement multiple parsing strategies for JSON extraction.
        
        :param response_text: Raw text response from OpenAI
        :return: Parsed graph data
        """
        parsing_strategies = [
            self._standard_json_parse,
            self._regex_json_parse,
            self._fallback_json_parse
        ]
        
        for strategy in parsing_strategies:
            try:
                result = strategy(response_text)
                if result:
                    return result
            except Exception as e:
                print(f"Strategy {strategy.__name__} failed: {e}")
                continue
        
        print("ALL JSON PARSING STRATEGIES FAILED")
        return {"entities": [], "relationships": []}

    def _standard_json_parse(self, text):
        """Standard JSON parsing method."""
        clean_text = text.strip().replace('```json', '').replace('```', '')
        parsed_data = json.loads(clean_text)
        
        # Validate structure
        if not isinstance(parsed_data, dict):
            raise ValueError("Invalid JSON structure")
        
        parsed_data.setdefault('entities', [])
        parsed_data.setdefault('relationships', [])
        
        return parsed_data

    def _regex_json_parse(self, text):
        """Regex-based JSON extraction method."""
        # Extract JSON-like content between first '{' and last '}'
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            clean_text = match.group(0)
            return self._standard_json_parse(clean_text)
        raise ValueError("No JSON-like structure found")

    def _fallback_json_parse(self, text):
        """Extremely lenient parsing as last resort."""
        # Attempt to manually reconstruct JSON
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            return {"entities": [], "relationships": []}
        raise ValueError("Cannot parse JSON")

def main():
    # Demonstration with multiple test cases
    test_prompts = PROMPTS['extraction_test_prompts']
    
    extractor = OpenAIExtractor()
    
    for text in test_prompts:
        print("\n--- Processing Text: ---\n")
        print(text)
        graph_data = extractor.extract(text)
        print("Extracted Graph Data:")
        print(json.dumps(graph_data, indent=2))

if __name__ == "__main__":
    main()