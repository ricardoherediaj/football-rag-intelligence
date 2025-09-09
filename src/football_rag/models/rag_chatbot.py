# mypy: ignore-errors
import os
from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List

import mlflow
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Get the current working directory
script_dir = Path(os.getcwd())

# Navigate up to the parent folder (you can use .parent to go up one level)
parent_dir = script_dir.parent
grandparent_dir = parent_dir.parent  # Go up one more level

# Combine the path to reach the config directory
config_path = "rag_chain_config.yaml"

## Enable MLflow Tracing
mlflow.langchain.autolog()

print("CONFIG PATH", config_path)
model_config = mlflow.models.ModelConfig(development_config=config_path)

guardrail_config = model_config.get("guardrail_config")
llm_config = model_config.get("llm_config")
retriever_config = model_config.get("retriever_config")


# The question is the last entry of the history
def extract_question(input: List[Dict[str, Any]]) -> str:
    """
    Extract the question from the input.

    Args:
        input (list[dict]): The input containing chat messages.

    Returns:
        str: The extracted question.
    """
    return input[-1]["content"]


# The history is everything before the last question
def extract_history(input: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Extract the chat history from the input.

    Args:
        input (list[dict]): The input containing chat messages.

    Returns:
        list[dict]: The extracted chat history.
    """
    return input[:-1]


# TODO: Convert to Few Shot Prompt
guardrail_prompt = PromptTemplate(
    input_variables=["chat_history", "question"],
    template=guardrail_config["prompt"],
)

guardrail_model = ChatBedrock(
    model_id=guardrail_config["model"],
    model_kwargs=dict(temperature=0.01),
)

chat_model = ChatBedrock(
    model_id=llm_config["llm_model"],
    model_kwargs=dict(temperature=0.01),
)


guardrail_chain = (
    {
        "question": itemgetter("messages") | RunnableLambda(extract_question),
        "chat_history": itemgetter("messages") | RunnableLambda(extract_history),
    }
    | guardrail_prompt
    | guardrail_model
    | StrOutputParser()
)


def get_retriever(path: str):
    """
    Get the FAISS retriever.

    Args:
        path (str, optional): The path to the vector store. Defaults to None.

    Returns:
        FAISS: The FAISS retriever.
    """
    # Ensure the config path is relative to this script's location
    # Load Vector Store
    # Get the FAISS retriever
    embeddings = BedrockEmbeddings()
    vector_store = FAISS.load_local(
        embeddings=embeddings,
        folder_path=path,
        allow_dangerous_deserialization=True,
    )

    # configure document retrieval
    retriever = vector_store.as_retriever(
        search_kwargs={"k": retriever_config.get("parameters")["k"]}
    )
    return retriever


# Setup Prompt to re-write query from chat history context
generate_query_to_retrieve_context_prompt = PromptTemplate(
    input_variables=["chat_history", "question"],
    template=llm_config["query_rewriter_prompt_template"],
)


# Setup query rewriter chain
generate_query_to_retrieve_context_chain = {
    "question": itemgetter("messages") | RunnableLambda(extract_question),
    "chat_history": itemgetter("messages") | RunnableLambda(extract_history),
} | RunnableBranch(  # Augment query only when there is a chat history
    (
        lambda x: x["chat_history"],
        generate_query_to_retrieve_context_prompt | chat_model | StrOutputParser(),
    ),
    (lambda x: not x["chat_history"], RunnableLambda(lambda x: x["question"])),
    RunnableLambda(lambda x: x["question"]),
)  # type: ignore


question_with_history_and_context_prompt = PromptTemplate(
    input_variables=["chat_history", "context", "question"],
    template=llm_config.get("llm_prompt_template"),  # Add Question with History and Context Prompt
)


def format_context(docs: List[Document]) -> str:
    """
    Format the context from a list of documents.

    Args:
        docs (list[Document]): A list of documents.

    Returns:
        str: A formatted string containing the content of the documents.
    """
    return "\n\n".join([d.page_content for d in docs])


def extract_source_urls(docs: List[Document]) -> List[str]:
    """
    Extract source URLs from a list of documents.

    Args:
        docs (list[Document]): A list of documents.

    Returns:
        list[str]: A list of source URLs extracted from the documents' metadata.
    """
    return [d.metadata[retriever_config.get("schema")["document_uri"]] for d in docs]


relevant_question_chain = (
    RunnablePassthrough()  # type: ignore
    | {
        "relevant_docs": generate_query_to_retrieve_context_prompt | chat_model | StrOutputParser(),
        "chat_history": itemgetter("chat_history"),
        "question": itemgetter("question"),
        "vector_store_path": itemgetter("vector_store_path"),
    }
    | {
        "relevant_docs": itemgetter("relevant_docs"),
        "chat_history": itemgetter("chat_history"),
        "question": itemgetter("question"),
        "vector_store_path": itemgetter("vector_store_path"),
    }
    | RunnableLambda(
        lambda x: {
            "relevant_docs": get_retriever(x["vector_store_path"]).get_relevant_documents(
                x["relevant_docs"]
            ),
            "chat_history": x["chat_history"],
            "question": x["question"],
            "vector_store_path": x["vector_store_path"],
        }
    )
    | {
        "context": itemgetter("relevant_docs") | RunnableLambda(format_context),
        "sources": itemgetter("relevant_docs") | RunnableLambda(extract_source_urls),
        "chat_history": itemgetter("chat_history"),
        "question": itemgetter("question"),
    }
    | {"prompt": question_with_history_and_context_prompt, "sources": itemgetter("sources")}
    | {
        "result": itemgetter("prompt") | chat_model | StrOutputParser(),
        "sources": itemgetter("sources"),
    }
)


irrelevant_question_chain = RunnableLambda(
    lambda x: {"result": llm_config.get("llm_refusal_fallback_answer"), "sources": []}
)

branch_node = RunnableBranch(
    (lambda x: "yes" in x["question_is_relevant"].lower(), relevant_question_chain),
    (lambda x: "no" in x["question_is_relevant"].lower(), irrelevant_question_chain),
    irrelevant_question_chain,
)  # type: ignore

full_chain = {
    "question_is_relevant": guardrail_chain,
    "question": itemgetter("messages") | RunnableLambda(extract_question),
    "chat_history": itemgetter("messages") | RunnableLambda(extract_history),
    "vector_store_path": itemgetter("vector_store_path"),
} | branch_node  # type: ignore


## Tell MLflow logging where to find your chain.
mlflow.models.set_model(model=full_chain)  # type: ignore
