import sys
import os
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chainlit as cl
from rag.chain import get_context, stream_answer
from config import config


def _check_ollama() -> bool:
    """Return True if the Ollama API is reachable."""
    try:
        urllib.request.urlopen(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        return True
    except Exception:
        return False


@cl.on_chat_start
async def on_start():
    if not _check_ollama():
        await cl.Message(
            content=(
                "**Ollama is not running.**\n\n"
                "Please open the Ollama app from the Start Menu, wait a few seconds "
                "for it to start, then refresh this page."
            )
        ).send()
        return

    cl.user_session.set("history", [])
    await cl.Message(
        content=(
            "**Welcome to the KT Knowledge Base!**\n\n"
            "Ask me anything about the project — architecture, setup, processes, APIs, "
            "deployment, or any topic covered in the Knowledge Transfer documents.\n\n"
            "I'll answer based only on the KT docs and tell you exactly which document "
            "the information came from."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    question = message.content.strip()
    history = cl.user_session.get("history", [])

    try:
        # Step 1: Retrieve context (shown as a collapsible step)
        async with cl.Step(name="Searching KT documents...") as step:
            ctx = get_context(question)
            step.output = f"Found {len(ctx['chunks'])} relevant sections"

        # Step 2: Stream the LLM answer token by token
        msg = cl.Message(content="")
        full_answer_parts = []

        async with cl.Step(name="Generating answer..."):
            async for token in stream_answer(question, ctx["context_str"], history):
                await msg.stream_token(token)
                full_answer_parts.append(token)

        # Append sources footer after streaming completes
        sources_text = "\n".join(f"  - {s}" for s in ctx["sources"])
        await msg.stream_token(f"\n\n---\n**Sources used:**\n{sources_text}")
        await msg.send()

        # Persist this turn in session history (keep last 5 turns max)
        history.append({
            "question": question,
            "answer": "".join(full_answer_parts)
        })
        cl.user_session.set("history", history[-5:])

    except ConnectionRefusedError:
        await cl.Message(
            content=(
                "**Ollama stopped responding.**\n\n"
                "Please open the Ollama app from the Start Menu and try again."
            )
        ).send()

    except Exception as e:
        await cl.Message(
            content=(
                f"**Something went wrong.** Please try again or contact the admin.\n\n"
                f"`{type(e).__name__}: {e}`"
            )
        ).send()
