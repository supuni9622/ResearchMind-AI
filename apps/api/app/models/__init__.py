"""
ResearchMind ORM models.

Import all ORM models here so SQLAlchemy metadata
is populated for Alembic autogeneration.
"""

from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.eval_score import EvalScore
from app.models.feedback import Feedback
from app.models.generation_usage import GenerationUsage
from app.models.memory import Memory, MemoryScopeSetting
from app.models.memory_feedback import MemoryFeedback
from app.models.project import Project, ProjectMembership
from app.models.promotion_review import PromotionReview
from app.models.research import ResearchSession
from app.models.research_proposal import ResearchProposal
from app.models.research_run import ResearchRun
from app.models.research_run_dispatch import ResearchRunDispatch
from app.models.research_run_event import ResearchRunEvent
from app.models.user import User

__all__ = [
    "User",
    "Document",
    "Conversation",
    "Message",
    "ResearchSession",
    "ResearchRun",
    "ResearchProposal",
    "ResearchRunDispatch",
    "ResearchRunEvent",
    "Memory",
    "MemoryScopeSetting",
    "MemoryFeedback",
    "GenerationUsage",
    "Feedback",
    "EvalScore",
    "PromotionReview",
    "Project",
    "ProjectMembership",
]
