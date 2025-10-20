import os
from autogen import LLMConfig
from dotenv import load_dotenv

load_dotenv()


def get_llm_config():
    return LLMConfig(
        config_list={
            "api_type": "openai",
            "model": "o3-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    )
