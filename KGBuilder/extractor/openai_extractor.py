import json
from openai import OpenAI 
import os
from dotenv import load_dotenv
load_dotenv()

## Model name
MODEL="gpt-4o-mini"


class OpenAIExtractor:
    def __init__(self, model=MODEL):
        """
        Initialize the OpenAI Extractor with an API key and model.
        
        :param model: The OpenAI model to use, default is "gpt-4o-mini".
        """
        self.model = model
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "<your OpenAI API key if not set as an env var>"))

    def extract(self, text):
        """
        Extract entities and relationships from text using the LLM.
        
        :param text: The input text for extraction.
        :return: A dictionary containing entities and relationships.
        """
        system_prompt = "You are a helpful assistant for extracting entities and relationships."
        prompt = f"""
        Extract entities and relationships from the following text in JSON format:
        Text: "{text}"
        Format the output as:
        {{
            "entities": ["Entity1", "Entity2", ...],
            "relationships": [
                {{"source": "Entity1", "relation": "Relationship", "target": "Entity2"}}
            ]
        }}
        """
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            result_text = completion.choices[0].message
            # result_json = json.loads(result_text.content)
            return result_text
        except Exception as e:
            print(f"Error during extraction: {e}")
            return {"entities": [], "relationships": []}

if __name__ == "__main__":
    text = "Barack Obama was the 44th President of the United States and Michelle Obama is an author."
    extractor = OpenAIExtractor()
    graph_data = extractor.extract(text)
    print(json.dumps(graph_data.content, indent=4))
