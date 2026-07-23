"""Owner-scoped persistence for Deep Research proposals."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_proposal import ResearchProposal


class ResearchProposalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, proposal: ResearchProposal) -> ResearchProposal:
        self._session.add(proposal)
        await self._session.flush()
        await self._session.refresh(proposal)
        return proposal

    async def get_by_id_for_owner(
        self, *, proposal_id: UUID, owner_id: UUID
    ) -> ResearchProposal | None:
        result = await self._session.execute(
            select(ResearchProposal).where(
                ResearchProposal.id == proposal_id, ResearchProposal.owner_id == owner_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_run_id(self, *, run_id: UUID) -> ResearchProposal | None:
        result = await self._session.execute(
            select(ResearchProposal).where(ResearchProposal.research_run_id == run_id)
        )
        return result.scalar_one_or_none()
