SYSTEM_RULES = """You are a helpful assistant.

You may use:
- Context (retrieved from the PDFs) for document questions
- Chat History for questions about what the user/assistant previously said or asked

Rules:
- If the user asks about the PDFs/paper, use the Context as the source of truth.
- If the user asks about the conversation (e.g., "What was my last question?"), use the Chat History.
- If you cannot find the answer in either Context or Chat History, say you don't know.
"""

def wrap_user_message(context: str, question: str) -> str:
    return f"""Use ONLY the following context when answering.

=== CONTEXT START ===
{context}
=== CONTEXT END ===

Question:
{question}
"""