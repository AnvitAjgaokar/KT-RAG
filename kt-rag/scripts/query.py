#!/usr/bin/env python3
"""
CLI test for the RAG pipeline without starting the UI.
Usage: python scripts/query.py "How do I deploy the auth service?"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag.chain import answer


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/query.py \"your question here\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\nQuestion: {question}\n")
    print("Thinking...\n")

    result = answer(question)
    print(f"Answer:\n{result['answer']}\n")
    print(f"Sources: {', '.join(result['sources'])}")


if __name__ == "__main__":
    main()
