from langchain_core.prompts import PromptTemplate
from typing import Dict


BASE_TEMPLATE = """
Question: {user_query}

You are a helpful assistant. Please answer the user's question in a simple and clear way.

IMPORTANT RULES:
- Keep answers short and simple
- Use easy-to-understand language
- Focus on the main point
- If you don't know, say "I don't have that information"
- Be friendly and helpful

Your response should be clear and easy to understand.
"""

prompt = BASE_TEMPLATE

def create_prompts() -> Dict[str, PromptTemplate]:
    return {
        "prompt": PromptTemplate(
            input_variables=["user_query"],
            template=BASE_TEMPLATE
        )
    }
