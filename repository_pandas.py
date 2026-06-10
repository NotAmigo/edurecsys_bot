from __future__ import annotations

from typing import List, Optional, Sequence

from repository import (
    QueryResult,
    Recommendation,
    RecommendationRepository,
    SortOrder,
)


REQUIRED_COLUMNS = ("id", "title", "description", "price")


class DataFrameRecommendationRepository(RecommendationRepository):
    """
    Реализация репозитория поверх pandas.DataFrame.

    Ожидаемые колонки: id, title, description, price.

    pandas импортируется лениво внутри методов, чтобы основной модуль
    бота можно было запустить без установленной зависимости pandas.
    """

    def __init__(self, df) -> None:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                "DataFrame missing required columns: " + ", ".join(missing)
            )
        self._df = df

    @staticmethod
    def _row_to_rec(row) -> Recommendation:
        return Recommendation(
            id=int(row["id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            price=int(row["price"]),
            url=str(row["url"])
        )

    def list_all(self) -> List[Recommendation]:
        return [self._row_to_rec(r) for _, r in self._df.iterrows()]

    def get_by_id(self, rec_id: int) -> Optional[Recommendation]:
        subset = self._df[self._df["id"] == rec_id]
        if subset.empty:
            return None
        return self._row_to_rec(subset.iloc[0])

    def query(
        self,
        *,
        ids: Optional[Sequence[int]] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        sort_order: SortOrder = "asc",
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> QueryResult:
        import pandas as pd  # noqa: F401  # lazy import, проверка доступности

        df = self._df

        if ids is not None:
            df = df[df["id"].isin(list(ids))]
        if price_min is not None:
            df = df[df["price"] >= price_min]
        if price_max is not None:
            df = df[df["price"] <= price_max]

        if sort_order == "asc":
            df = df.sort_values("price")
        elif sort_order == "desc":
            df = df.sort_values("price", ascending=False)

        total = int(len(df))

        if offset < 0:
            offset = 0

        if limit is None:
            page_df = df.iloc[offset:]
        else:
            page_df = df.iloc[offset : offset + limit]

        items = [self._row_to_rec(r) for _, r in page_df.iterrows()]
        return QueryResult(items=items, total=total)
