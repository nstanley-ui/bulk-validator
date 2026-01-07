import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.configs: Dict[str, Any] = {}

    def load_platform_config(self, platform_name: str) -> Dict[str, Any]:
        """Loads configuration for a specific platform."""
        # Check for exact name, snake_case, or platform key match
        possible_names = [
            platform_name.lower().replace(" ", "_"),
            platform_name.lower().split(" ")[0], # e.g. "linkedin" from "LinkedIn Ads"
        ]
        
        file_path = None
        for name in possible_names:
            p = os.path.join(self.config_dir, f"{name}.yaml")
            if os.path.exists(p):
                file_path = p
                break
        
        if not file_path:
            raise FileNotFoundError(f"Configuration for platform '{platform_name}' not found in {self.config_dir}")
            
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
            self.configs[platform_name] = config
            return config

    def get_config(self, platform_name: str) -> Dict[str, Any]:
        if platform_name not in self.configs:
            return self.load_platform_config(platform_name)
        return self.configs[platform_name]
