from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from rag.retriever import retrieve
from config import config

# Module-level LLM instance — initialized once, reused across all requests
_llm: OllamaLLM | None = None


def _get_llm() -> OllamaLLM:
    global _llm
    if _llm is None:
        _llm = OllamaLLM(
            model=config.LLM_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=0.1
        )
    return _llm


PROMPT_TEMPLATE = """You are a precise technical assistant for a software development team.
Your job is to answer questions using ONLY the Knowledge Transfer documents provided below.

Instructions:
1. Read all the provided context carefully before answering.
2. Think step by step — identify which document sections are relevant to the question.
3. Synthesize information across multiple sources if needed.
4. Always cite the exact source document name(s) in your answer.
5. If the answer is not present in the context, say exactly: "I don't have that information in the KT docs."
6. Never guess or add information not found in the context.

--- KNOWLEDGE BASE CONTEXT ---
{context}
--- END CONTEXT ---
{chat_history}
Question: {question}

Step-by-step reasoning and answer (always cite source document names):"""

prompt = PromptTemplate(
    input_variables=["context", "question", "chat_history"],
    template=PROMPT_TEMPLATE
)


def _format_history(history: list[dict]) -> str:
    """Format the last 3 conversation turns as a context block for the prompt."""
    if not history:
        return ""
    lines = ["\n--- RECENT CONVERSATION ---"]
    for turn in history[-3:]:
        lines.append(f"User: {turn['question']}")
        answer_preview = turn['answer'][:500] + ("..." if len(turn['answer']) > 500 else "")
        lines.append(f"Assistant: {answer_preview}")
    lines.append("--- END CONVERSATION ---")
    return "\n".join(lines)


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a structured context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        score = chunk.get("score", 0.0)
        sheet = f", Sheet: {meta['sheet']}" if meta.get("sheet") else ""
        section = f", Section: {meta['section']}" if meta.get("section") else ""
        parts.append(
            f"[Source {i}: {source}, Page {page}{sheet}{section}, relevance={score:.3f}]\n{chunk['text']}"
        )
    return "\n\n".join(parts)


def get_context(question: str) -> dict:
    """
    Retrieve chunks and build context string. Returns {chunks, context_str, sources}.
    Called by the UI before streaming so retrieval and generation can be shown separately.
    """
    chunks = retrieve(question)
    return {
        "chunks": chunks,
        "context_str": build_context(chunks),
        "sources": list({
            f"{c['metadata'].get('source', 'Unknown')} (p.{c['metadata'].get('page', '?')})"
            for c in chunks
        })
    }


async def stream_answer(question: str, context_str: str, history: list[dict] = None):
    """
    Async generator that streams LLM tokens one by one.
    Used by the Chainlit UI for real-time response rendering.
    """
    llm = _get_llm()
    chain = prompt | llm
    chat_history_str = _format_history(history or [])
    async for token in chain.astream({
        "context": context_str,
        "question": question,
        "chat_history": chat_history_str
    }):
        yield token


def answer(question: str, history: list[dict] = None) -> dict:
    """
    Full RAG pipeline (non-streaming): retrieve -> build context -> LLM answer.
    Used by scripts/query.py CLI. Returns {answer, sources, chunks_used} dict.
    """
    ctx = get_context(question)
    llm = _get_llm()
    chain = prompt | llm
    response = chain.invoke({
        "context": ctx["context_str"],
        "question": question,
        "chat_history": _format_history(history or [])
    })
    return {
        "answer": response,
        "sources": ctx["sources"],
        "chunks_used": len(ctx["chunks"])
    }
