import chainlit as cl
from rag.chain import answer


@cl.on_chat_start
async def on_start():
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

    # Show thinking indicator
    async with cl.Step(name="Searching KT documents...") as step:
        result = answer(question)
        step.output = f"Found {result['chunks_used']} relevant sections"

    # Format sources as footer
    sources_text = "\n".join(f"  - {s}" for s in result["sources"])
    full_response = (
        f"{result['answer']}\n\n"
        f"---\n**Sources used:**\n{sources_text}"
    )

    await cl.Message(content=full_response).send()
