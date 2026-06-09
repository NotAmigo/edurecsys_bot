from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional, Sequence


@dataclass(frozen=True)
class Recommendation:
    id: int
    title: str
    description: str
    price: int
    url: str


@dataclass(frozen=True)
class QueryResult:
    items: List[Recommendation]
    total: int


SortOrder = Literal["asc", "desc"]


class RecommendationRepository(ABC):
    """
    Интерфейс хранилища рекомендаций.

    Реализации: InMemoryRecommendationRepository,
    DataFrameRecommendationRepository (в repository_pandas.py).
    """

    @abstractmethod
    def list_all(self) -> List[Recommendation]:
        ...

    @abstractmethod
    def get_by_id(self, rec_id: int) -> Optional[Recommendation]:
        ...

    @abstractmethod
    def query(
        self,
        *,
        ids: Optional[Sequence[int]] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        sort_order: Optional[str] = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> QueryResult:
        """
        Возвращает страницу рекомендаций после фильтрации и сортировки.

        items - элементы текущей страницы.
        total - общее число элементов, удовлетворяющих фильтру (до пагинации).
        """
        ...


class InMemoryRecommendationRepository(RecommendationRepository):
    def __init__(self, items: Iterable[Recommendation]) -> None:
        items_list = list(items)
        self._items: List[Recommendation] = items_list
        self._by_id: Dict[int, Recommendation] = {item.id: item for item in items_list}

    def list_all(self) -> List[Recommendation]:
        return list(self._items)

    def get_by_id(self, rec_id: int) -> Optional[Recommendation]:
        return self._by_id.get(rec_id)

    def query(
        self,
        *,
        ids: Optional[Sequence[int]] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        sort_order: SortOrder = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> QueryResult:
        ids_set = set(ids) if ids is not None else None

        filtered: List[Recommendation] = []
        for item in self._items:
            if ids_set is not None and item.id not in ids_set:
                continue
            if price_min is not None and item.price < price_min:
                continue
            if price_max is not None and item.price > price_max:
                continue
            filtered.append(item)
        if sort_order is not None:
            filtered.sort(key=lambda r: r.price, reverse=(sort_order == "desc"))

        total = len(filtered)

        if offset < 0:
            offset = 0

        if limit is None:
            page = filtered[offset:]
        else:
            page = filtered[offset : offset + limit]

        return QueryResult(items=page, total=total)

#
# MOCK_RECOMMENDATIONS: List[Recommendation] = [
#     Recommendation(
#         id=1,
#         title="Курс «Введение в программирование на Python»",
#         description=(
#             "Базовый онлайн-курс для тех, кто только начинает путь в IT. "
#             "Изучаются переменные, циклы, функции, работа с файлами и стандартная "
#             "библиотека Python. По итогам - небольшой собственный проект."
#         ),
#         price=4900,
#     ),
#     Recommendation(
#         id=2,
#         title="Курс «Data Science с нуля»",
#         description=(
#             "Полугодовая программа: numpy, pandas, визуализация, классические "
#             "алгоритмы машинного обучения. Подходит выпускникам инженерных "
#             "и экономических специальностей."
#         ),
#         price=54000,
#     ),
#     Recommendation(
#         id=3,
#         title="Профессия «Графический дизайнер»",
#         description=(
#             "Большая программа по графическому дизайну: композиция, типографика, "
#             "Figma, Adobe Illustrator, упаковка проектов в портфолио."
#         ),
#         price=89000,
#     ),
#     Recommendation(
#         id=4,
#         title="Курс «Юридические основы предпринимательства»",
#         description=(
#             "Регистрация бизнеса, договоры, налоги, защита интеллектуальной "
#             "собственности. Подходит начинающим предпринимателям."
#         ),
#         price=15000,
#     ),
#     Recommendation(
#         id=5,
#         title="Курс «Основы фотографии»",
#         description=(
#             "Технические основы съёмки, работа со светом, базовая обработка в "
#             "Lightroom. Практические задания каждую неделю."
#         ),
#         price=7500,
#     ),
#     Recommendation(
#         id=6,
#         title="Профессия «Аналитик данных»",
#         description=(
#             "SQL, Python, статистика, A/B-тесты, BI-инструменты. Включает "
#             "стажировку на реальных данных компании-партнёра."
#         ),
#         price=72000,
#     ),
#     Recommendation(
#         id=7,
#         title="Курс «Технический писатель»",
#         description=(
#             "Документация API, пользовательские руководства, работа в Markdown "
#             "и системах статической генерации сайтов."
#         ),
#         price=22000,
# url=""
#     ),
#     Recommendation(
#         id=8,
#         title="Курс «Бухгалтерский учёт для начинающих»",
#         description=(
#             "1С, первичные документы, налоговая отчётность, основы аудита. "
#             "Подходит тем, кто планирует работать ассистентом бухгалтера."
#         ),
#         price=18500,
#         url=""
#     ),
#     Recommendation(
#         id=9,
#         title="Профессия «UX/UI-дизайнер»",
#         description=(
#             "Исследования пользователей, прототипирование, дизайн-системы, "
#             "Figma, защита решений перед стейкхолдерами."
#         ),
#         price=95000,
#         url=""
#     ),
#     Recommendation(
#         id=10,
#         title="Курс «Введение в экологический мониторинг»",
#         description=(
#             "Методы оценки качества воды, воздуха и почвы. Полевая практика "
#             "и работа с лабораторным оборудованием."
#         ),
#         price=11000,
#         url=""
#     ),
#     Recommendation(
#         id=11,
#         title="Курс «Профессиональный гид-экскурсовод»",
#         description=(
#             "Методика проведения экскурсий, краеведение, работа с группами, "
#             "получение аккредитации."
#         ),
#         price=9800,
#         url=""
#     ),
#     Recommendation(
#         id=12,
#         title="Профессия «Frontend-разработчик»",
#         description=(
#             "HTML, CSS, JavaScript, React, основы TypeScript. Большой "
#             "выпускной проект и помощь с трудоустройством."
#         ),
#         price=78000,
#         url=""
#     ),
#     Recommendation(
#         id=13,
#         title="Курс «Социология: введение в профессию»",
#         description=(
#             "Классические и современные подходы, методы количественных и "
#             "качественных исследований, обработка опросов."
#         ),
#         price=12500,
#         url=""
#     ),
#     Recommendation(
#         id=14,
#         title="Курс «Основы кинологии»",
#         description=(
#             "Психология собак, базовая дрессировка, подготовка к работе "
#             "с породными клубами и кинологическими службами."
#         ),
#         price=6500,
#         url=""
#     ),
#     Recommendation(
#         id=15,
#         title="Профессия «Менеджер по продукту»",
#         description=(
#             "Customer development, метрики, приоритизация бэклога, работа "
#             "с командой разработки. Подходит специалистам с опытом 1-2 года."
#         ),
#         price=110000,
#         url=""
#     ),
# ]
