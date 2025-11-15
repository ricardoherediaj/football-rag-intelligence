"""Load and manage prompts from YAML files."""

from pathlib import Path
from typing import Dict, Any
import yaml

from football_rag.logging import get_logger

logger = get_logger(__name__)


def load_prompt(profile_name: str = "profile_football_v1") -> Dict[str, str]:
    """Load prompt from YAML file.

    Args:
        profile_name: Name of prompt profile (without .yml extension)

    Returns:
        Dict with 'system' and 'user_template' keys
    """
    prompt_path = (
        Path(__file__).parent.parent.parent.parent / "prompts" / f"{profile_name}.yml"
    )

    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {prompt_path}, using defaults")
        return {
            "system": "You are a football analytics assistant.",
            "user_template": "Context: {context}\n\nQuestion: {question}\n\nAnswer:",
        }

    try:
        with open(prompt_path) as f:
            data = yaml.safe_load(f)
            return {
                "system": data.get("system", ""),
                "user_template": data.get("user_template", ""),
            }
    except Exception as e:
        logger.error(f"Failed to load prompt: {e}")
        return {
            "system": "You are a football analytics assistant.",
            "user_template": "Context: {context}\n\nQuestion: {question}\n\nAnswer:",
        }
