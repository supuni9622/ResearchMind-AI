from pydantic import BaseModel


class PlannerStep(
    BaseModel,
):
    title: str

    description: str


class PlannerOutput(
    BaseModel,
):
    objective: str

    steps: list[PlannerStep]
