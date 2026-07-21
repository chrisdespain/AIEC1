"""RAGAS evaluation utilities for Activity 1.

Compares a Fireworks AI RAG pipeline against an OpenAI ``gpt-4.1-mini``
equivalent using RAGAS and captures per-query cost/latency with LangSmith
tracing enabled.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, Sequence, TypedDict

import tiktoken
from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from langsmith import Client as LangSmithClient
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

load_dotenv(override=True)
# Ensure LangSmith tracing is on for this session if the user has an API key.
os.environ.setdefault("LANGSMITH_TRACING", "true")

Provider = Literal["fireworks", "openai"]

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# Defaults aligned with ENDPOINT_SETUP.md / README.md.
DEFAULT_FIREWORKS_EMBEDDING = "accounts/fireworks/models/qwen3-embedding-4b"
DEFAULT_FIREWORKS_CHAT = "accounts/fireworks/models/gpt-oss-20b"

# Rough per-1M-token pricing used for cost estimates. Override via env vars.
PRICE_RATES: dict[str, dict[str, float]] = {
    "fireworks": {
        "input": float(os.environ.get("FIREWORKS_INPUT_PRICE", "0.07")),
        "output": float(os.environ.get("FIREWORKS_OUTPUT_PRICE", "0.30")),
        "embedding": float(os.environ.get("FIREWORKS_EMBEDDING_PRICE", "0.10")),
    },
    "openai": {
        "input": float(os.environ.get("OPENAI_INPUT_PRICE", "0.40")),
        "output": float(os.environ.get("OPENAI_OUTPUT_PRICE", "1.60")),
        "embedding": float(os.environ.get("OPENAI_EMBEDDING_PRICE", "0.02")),
    },
}


class _RAGState(TypedDict):
    """State schema for the simple two-step RAG graph."""

    question: str
    context: list[Document]
    response: str


def _tiktoken_len(text: str) -> int:
    """Return token length using tiktoken; used for chunk length measurement."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))


@lru_cache(maxsize=2)
def _load_chunks(pdf_path: str = "data/cat-health-guide.pdf") -> list[Document]:
    """Load and split the PDF into token-aware chunks."""
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=0,
        length_function=_tiktoken_len,
    )
    return splitter.split_documents(docs)


def _get_embedding_model(provider: Provider) -> OpenAIEmbeddings:
    """Return an embeddings model for the requested provider."""
    if provider == "fireworks":
        dims = os.environ.get("FIREWORKS_EMBEDDING_DIMENSIONS")
        kwargs = {}
        if dims:
            kwargs["dimensions"] = int(dims)
        return OpenAIEmbeddings(
            model=os.environ.get("FIREWORKS_EMBEDDING_MODEL", DEFAULT_FIREWORKS_EMBEDDING),
            openai_api_key=os.environ["FIREWORKS_API_KEY"],
            openai_api_base=FIREWORKS_BASE_URL,
            check_embedding_ctx_length=False,
            **kwargs,
        )
    return OpenAIEmbeddings(
        model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=os.environ.get("OPENAI_API_KEY"),
    )


def _get_chat_model(
    provider: Provider,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    """Return a chat model for the requested provider."""
    kwargs: dict[str, Any] = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if provider == "fireworks":
        return ChatOpenAI(
            model=os.environ.get("FIREWORKS_CHAT_MODEL", DEFAULT_FIREWORKS_CHAT),
            temperature=temperature,
            openai_api_key=os.environ["FIREWORKS_API_KEY"],
            openai_api_base=FIREWORKS_BASE_URL,
            **kwargs,
        )
    return ChatOpenAI(
        model=os.environ.get("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
        temperature=temperature,
        api_key=os.environ.get("OPENAI_API_KEY"),
        **kwargs,
    )


@lru_cache(maxsize=2)
def build_rag_graph(provider: Provider, pdf_path: str = "data/cat-health-guide.pdf"):
    """Build a compiled two-step RAG graph for the given provider."""
    chunks = _load_chunks(pdf_path)
    embedding = _get_embedding_model(provider)
    vectorstore = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding,
        location=":memory:",
        collection_name=f"rag_collection_{provider}",
    )
    retriever = vectorstore.as_retriever()

    human_template = (
        "\n#CONTEXT:\n{context}\n\nQUERY:\n{query}\n\n"
        "Use the provided context to answer the provided user query. "
        "Only use the provided context to answer the query. "
        "If you do not know the answer, or it's not contained in the provided context respond with \"I don't know\""
    )
    prompt = ChatPromptTemplate.from_messages([("human", human_template)])
    # Cap the generator to avoid runaway outputs from the open-source model.
    max_tokens = int(os.environ.get("MAX_TOKENS", "1024"))
    llm = _get_chat_model(provider, max_tokens=max_tokens)

    def retrieve(state: _RAGState):
        retrieved_docs = retriever.invoke(state["question"]) if retriever else []
        return {"context": retrieved_docs}

    def generate(state: _RAGState):
        context_text = "\n\n".join(
            f"Context {i + 1}:\n{doc.page_content}"
            for i, doc in enumerate(state.get("context", []))
        )
        chain = prompt | llm | StrOutputParser()
        response_text = chain.invoke(
            {"query": state["question"], "context": context_text}
        )
        return {"response": response_text}

    graph_builder = StateGraph(_RAGState)
    graph_builder = graph_builder.add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")
    return graph_builder.compile()


@dataclass
class RAGResponse:
    """A single RAG result plus timing and usage/cost estimates."""

    provider: str
    question: str
    answer: str
    contexts: list[str]
    latency_seconds: float
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    estimated_cost_usd: float


def _estimate_cost(
    provider: str,
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
) -> float:
    """Estimate USD cost from token counts using per-provider rates."""
    rates = PRICE_RATES[provider]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * rates["embedding"]
    ) / 1_000_000


def ask_rag(
    provider: Provider,
    question: str,
    pdf_path: str = "data/cat-health-guide.pdf",
) -> RAGResponse:
    """Run a RAG pipeline and return the response with usage/cost estimates."""
    graph = build_rag_graph(provider, pdf_path)

    # Count the question tokens that will be sent to the embedding endpoint.
    embedding_tokens = _tiktoken_len(question)

    start = time.perf_counter()
    config = {
        "metadata": {"provider": provider, "question": question, "pdf_path": pdf_path},
        "tags": ["activity_1", provider],
    }
    result = graph.invoke({"question": question}, config)
    latency = time.perf_counter() - start

    answer = result.get("response", "")
    contexts = [doc.page_content for doc in result.get("context", [])]

    context_text = "\n\n".join(contexts)
    generation_input = f"{context_text}\n\n{question}".strip()
    input_tokens = _tiktoken_len(generation_input)
    output_tokens = _tiktoken_len(answer)

    cost = _estimate_cost(provider, input_tokens, output_tokens, embedding_tokens)

    return RAGResponse(
        provider=provider,
        question=question,
        answer=answer,
        contexts=contexts,
        latency_seconds=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        embedding_tokens=embedding_tokens,
        estimated_cost_usd=cost,
    )


def run_ragas_evaluation(
    responses: Sequence[RAGResponse],
    references: Sequence[str] | None = None,
    experiment_name: str = "activity_1_rag_eval",
) -> dict[str, Any]:
    """Run RAGAS on a set of RAG responses.

    ``responses`` and ``references`` must be aligned. If ``references`` is None,
    ground-truth correctness metrics are skipped.
    """
    contexts = [r.contexts for r in responses]
    dataset_dict: dict[str, list[Any]] = {
        "user_input": [r.question for r in responses],
        "response": [r.answer for r in responses],
        "retrieved_contexts": contexts,
    }
    metrics: list[Any] = [Faithfulness(), AnswerRelevancy()]
    if references is not None:
        dataset_dict["reference"] = list(references)
        metrics.extend([ContextPrecision(), ContextRecall(), AnswerCorrectness()])

    dataset = Dataset.from_dict(dataset_dict)

    # Use a consistent judge for both pipelines so the scores are comparable.
    # No max_tokens cap for the judge, because correctness/precision metrics can
    # request longer structured outputs.
    judge_llm = LangchainLLMWrapper(_get_chat_model("openai", temperature=0.0))
    judge_embeddings = LangchainEmbeddingsWrapper(_get_embedding_model("openai"))

    result = evaluate(
        dataset,
        metrics=metrics,
        llm=judge_llm,
        embeddings=judge_embeddings,
        experiment_name=experiment_name,
        raise_exceptions=True,
    )
    return result


def compare_providers(
    questions: Sequence[str],
    references: Sequence[str] | None = None,
    pdf_path: str = "data/cat-health-guide.pdf",
) -> dict[str, Any]:
    """Run both the Fireworks and OpenAI RAG pipelines and compare them.

    Returns a dictionary with:
        - fireworks_responses: list[RAGResponse]
        - openai_responses: list[RAGResponse]
        - fireworks_scores: RAGAS EvaluationResult
        - openai_scores: RAGAS EvaluationResult
        - fireworks_cost_usd: float
        - openai_cost_usd: float
    """
    fireworks_responses = [ask_rag("fireworks", q, pdf_path) for q in questions]
    openai_responses = [ask_rag("openai", q, pdf_path) for q in questions]

    fireworks_eval = run_ragas_evaluation(
        fireworks_responses,
        references=references,
        experiment_name="activity_1_fireworks",
    )
    openai_eval = run_ragas_evaluation(
        openai_responses,
        references=references,
        experiment_name="activity_1_openai",
    )

    return {
        "fireworks_responses": fireworks_responses,
        "openai_responses": openai_responses,
        "fireworks_eval": fireworks_eval,
        "openai_eval": openai_eval,
        "fireworks_cost_usd": sum(r.estimated_cost_usd for r in fireworks_responses),
        "openai_cost_usd": sum(r.estimated_cost_usd for r in openai_responses),
    }
