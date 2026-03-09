from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from rag.retriever import retrieve
from config import config

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

Question: {question}

Step-by-step reasoning and answer (always cite source document names):"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=PROMPT_TEMPLATE
)


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a structured context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        score = chunk.get("score", "?")
        sheet = f", Sheet: {meta['sheet']}" if meta.get("sheet") else ""
        parts.append(
            f"[Source {i}: {source}, Page {page}{sheet}, relevance={score:.3f}]\n{chunk['text']}"
        )
    return "\n\n".join(parts)


def answer(question: str) -> dict:
    """
    Full RAG pipeline: retrieve -> filter -> build context -> LLM answer.
    Returns {answer, sources, chunks_used} dict.
    """
    chunks = retrieve(question)
    context = build_context(chunks)

    llm = OllamaLLM(
        model=config.LLM_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0.1
    )

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    sources = list({
        f"{c['metadata'].get('source', 'Unknown')} (p.{c['metadata'].get('page', '?')})"
        for c in chunks
    })

    return {
        "answer": response,
        "sources": sources,
        "chunks_used": len(chunks)
    }
