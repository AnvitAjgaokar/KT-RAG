from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from rag.retriever import retrieve
from config import config

# System prompt — tune this to your team's context
PROMPT_TEMPLATE = """You are a helpful assistant for a software development team.
You answer questions based ONLY on the Knowledge Transfer documents provided below.
If the answer is not in the documents, say "I don't have that information in the KT docs."
Always mention which document/file the information came from.

--- KNOWLEDGE BASE CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer (cite source document names):"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=PROMPT_TEMPLATE
)


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into readable context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        parts.append(f"[Source {i}: {source}, Page {page}]\n{chunk['text']}")
    return "\n\n".join(parts)


def answer(question: str) -> dict:
    """
    Full RAG pipeline: retrieve -> build context -> LLM answer.
    Returns {answer, sources} dict.
    """
    chunks = retrieve(question)
    context = build_context(chunks)

    llm = OllamaLLM(
        model=config.LLM_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0.1   # Low temp = factual, less creative
    )

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    # Deduplicate sources for display
    sources = list({
        f"{c['metadata'].get('source', 'Unknown')} (p.{c['metadata'].get('page', '?')})"
        for c in chunks
    })

    return {
        "answer": response,
        "sources": sources,
        "chunks_used": len(chunks)
    }
