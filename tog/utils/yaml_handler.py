import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

class YamlHandler:
    """
    Utility class for working with YAML files, particularly designed for managing prompts.
    """
    
    @staticmethod
    def read_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read a YAML file and return its contents.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dictionary containing the YAML file contents
            
        Raises:
            FileNotFoundError: If the specified file doesn't exist
            yaml.YAMLError: If the YAML file is malformed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    @staticmethod
    def write_yaml(data: Dict[str, Any], file_path: Union[str, Path], 
                  default_flow_style: bool = False) -> None:
        """
        Write data to a YAML file.
        
        Args:
            data: Dictionary containing data to write to YAML
            file_path: Path where the YAML file will be written
            default_flow_style: YAML formatting style (False for block style)
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=default_flow_style, sort_keys=False)
    
    @staticmethod
    def update_yaml(file_path: Union[str, Path], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing YAML file with new data.
        
        Args:
            file_path: Path to the YAML file
            updates: Dictionary containing updates to apply
            
        Returns:
            Updated dictionary
            
        Note:
            Creates the file if it doesn't exist
        """
        file_path = Path(file_path)
        
        if file_path.exists():
            data = YamlHandler.read_yaml(file_path)
            # Deep update the dictionary
            YamlHandler._deep_update(data, updates)
        else:
            data = updates
        
        YamlHandler.write_yaml(data, file_path)
        return data
    
    @staticmethod
    def _deep_update(original: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """
        Recursively update a dictionary.
        
        Args:
            original: Dictionary to update
            updates: Dictionary with updates to apply
        """
        for key, value in updates.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                YamlHandler._deep_update(original[key], value)
            else:
                original[key] = value
    
    @staticmethod
    def get_prompt(file_path: Union[str, Path], prompt_key: str) -> Optional[str]:
        """
        Get a specific prompt from a YAML file.
        
        Args:
            file_path: Path to the YAML file
            prompt_key: Key to retrieve the prompt
            default: Default value if key not found
            
        Returns:
            Prompt string or default if not found
        """
        try:
            data = YamlHandler.read_yaml(file_path)
            keys = prompt_key.split('.')
            
            for key in keys:
                data = data.get(key, {})
                
            return data
            
        except (FileNotFoundError, yaml.YAMLError):
            raise ValueError(f"Error reading prompt: {prompt_key}")