from pydantic import BaseModel


class ResearchReport(
    BaseModel,
):
    executive_summary: str

    findings: list[str]

    limitations: list[str]

    references: list[str]
