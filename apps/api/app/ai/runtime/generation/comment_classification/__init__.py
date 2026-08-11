"""Objective/preference classification for feedback comments (E11,
EVALUATION_PLAN.md §12/1g).

A user's free-text feedback comment can be a factual quality complaint
("this cited the wrong paper" -- objective, should feed the shared
regression gates via E10's promotion loop) or a stylistic preference
("this answer was too formal" -- stays owner-scoped, should never
contaminate the shared golden set). Nothing before this classified that
split; `POST /feedback` (E3) only ever stored the comment as free text.
"""

from __future__ import annotations
