"""Analysis modules — one per risk-scoring category.

Each analyzer exposes an ``async def analyze(...)`` coroutine that returns
a :class:`~app.models.schemas.CategoryResult`.
"""
