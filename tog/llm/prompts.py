from enum import Enum
import yaml
from pathlib import Path
from ..logging_config import logger
class Prompts(Enum):
    EXTRACT_ENTITIES = "EXTRACT_ENTITIES"
    GENERATE_NATURAL_LANGUAGE = "GENERATE_NATURAL_LANGUAGE"
    BEAM_SEARCH = "BEAM_SEARCH"
    PRUNE_RELATIONS = "PRUNE_RELATIONS"
    EVALUATE_PATHS = "EVALUATE_PATHS"
    GENERATE_ANSWER = "GENERATE_ANSWER"

    def __str__(self):
        return self._load_prompt(self.value)

    @staticmethod
    def _load_prompt(key):
        yaml_path = Path(__file__).parent / "prompts.yaml"
        with open(yaml_path, 'r') as f:
            prompts = yaml.safe_load(f)
            logger.info(f"Loaded prompts: {prompts}")
        return "\n" + prompts[key]
    
if __name__ == "__main__":
    print(Prompts.GENERATE_NATURAL_LANGUAGE)
    print(Prompts.BEAM_SEARCH)
    print(Prompts.PRUNE_RELATIONS)
    print(Prompts.GENERATE_ANSWER)
    print(Prompts.EVALUATE_PATHS)
    print(Prompts.EXTRACT_ENTITIES)