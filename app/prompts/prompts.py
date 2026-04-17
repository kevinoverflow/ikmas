from app.domain.types import RoleName
from app.prompts.context_reconstructor_agent import PROMPT as CONTEXT_RECONSTRUCTOR_AGENT_PROMPT
from app.prompts.mentor_agent import PROMPT as MENTOR_AGENT_PROMPT
from app.prompts.scribe_agent import PROMPT as SCRIBE_AGENT_PROMPT
from app.prompts.semantic_linking_agent import PROMPT as SEMANTIC_LINKING_AGENT_PROMPT

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


ROLE_PROMPTS: dict[RoleName, str] = {
    "ContextReconstructorAgent": CONTEXT_RECONSTRUCTOR_AGENT_PROMPT,
    "MentorAgent": MENTOR_AGENT_PROMPT,
    "ScribeAgent": SCRIBE_AGENT_PROMPT,
    "SemanticLinkingAgent": SEMANTIC_LINKING_AGENT_PROMPT,
}


def get_role_prompt(role: RoleName) -> str:
    return ROLE_PROMPTS[role]
