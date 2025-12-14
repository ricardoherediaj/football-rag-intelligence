"""Load and manage prompts from YAML files."""

import logging
from pathlib import Path
from typing import Dict, Any
import yaml

from football_rag.config.settings import settings 

logger = logging.getLogger(__name__)

def load_prompt(version_key: str = "v3.5_balanced") -> Dict[str, str]:
    """Load a specific prompt version from prompt_versions.yaml."""
    
    # 1. Define where to look (Project Root/prompts)
    project_root = Path.cwd()
    prompts_dir = project_root / "prompts"
    
    # 2. Define what filenames to look for (handle .yaml vs .yml)
    candidates = ["prompt_versions.yaml", "prompt_versions.yml"]
    
    prompt_path = None
    
    # 3. Find the first match
    if prompts_dir.exists():
        for filename in candidates:
            candidate_path = prompts_dir / filename
            if candidate_path.exists():
                prompt_path = candidate_path
                break
    
    # 4. If still not found, crash with a helpful error
    if not prompt_path:
        # Debug: List what files actually ARE there
        existing_files = [f.name for f in prompts_dir.glob("*")] if prompts_dir.exists() else "Directory not found"
        error_msg = (
            f"❌ Could not find prompt file.\n"
            f"   Looking in: {prompts_dir}\n"
            f"   Found these files instead: {existing_files}"
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        with open(prompt_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # 5. Extract the specific version
        version_data = data.get("versions", {}).get(version_key)
        
        if not version_data:
            # Fallback: Check if the file IS the prompt (old v1 structure)
            if "system" in data:
                return {"system": data.get("system"), "user_template": data.get("user_template")}
            
            valid_keys = list(data.get("versions", {}).keys())
            raise KeyError(f"Version '{version_key}' not found in {prompt_path.name}. Available: {valid_keys}")

        logger.info(f"✅ Loaded prompt version: {version_key} (Score: {version_data.get('score')})")
        
        return {
            "system": version_data["system"],
            "user_template": version_data["user_prompt"]
        }

    except Exception as e:
        logger.error(f"❌ Failed to parse prompt file: {e}")
        raise e