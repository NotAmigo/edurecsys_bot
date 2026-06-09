from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from logic import analyze_test

from repository import InMemoryRecommendationRepository

from repository_pandas import DataFrameRecommendationRepository

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from repository import (
    Recommendation,
    RecommendationRepository,
)


INSTRUCTION_TEXT = (
    "Предположим, что после соответствующего обучения Вы сможете выполнять любую работу. "
    "Из предложенных попарно вариантов профессий выберите ту, которой Вы отдаете предпочтение. "
    "В бланке ответов найдите выбранный вариант ответа и отметьте его. "
    "Если Вы плохо представляете себе, чем занимаются специалисты названных профессий, "
    "обратитесь за помощью к профконсультанту или Интернету. "
    "Ответы необходимо дать на все высказывания. Время диагностики не ограничено."
)

START_TEXT = (
    "Здравствуйте!\n\n"
    "Далее Вам необходимо пройти тест из 42 вопросов. "
    "В каждом вопросе будет два варианта ответа. "
    "Выберите тот вариант профессии, которому отдаете предпочтение.\n\n"
    "Ваш прогресс будет сохраняться автоматически, поэтому при перезапуске бота "
    "или временном отключении сервера тест можно будет продолжить."
)


@dataclass(frozen=True)
class Question:
    number: int
    a: str
    b: str


QUESTIONS: List[Question] = [
    Question(1, "Инженер", "Социолог"),
    Question(2, "Кондитер", "Священнослужитель"),
    Question(3, "Повар", "Статистик"),
    Question(4, "Фотограф", "Торговый администратор"),
    Question(5, "Механик", "Дизайнер"),
    Question(6, "Философ", "Врач"),
    Question(7, "Эколог", "Бухгалтер"),
    Question(8, "Программист", "Адвокат"),
    Question(9, "Кинолог", "Литературный переводчик"),
    Question(10, "Страховой агент", "Архивист"),
    Question(11, "Тренер", "Телерепортер"),
    Question(12, "Следователь", "Искусствовед"),
    Question(13, "Нотариус", "Брокер"),
    Question(14, "Оператор ЭВМ", "Манекенщица"),
    Question(15, "Фотокорреспондент", "Реставратор"),
    Question(16, "Озеленитель", "Биолог-исследователь"),
    Question(17, "Водитель", "Бортпроводник"),
    Question(18, "Метролог", "Картограф"),
    Question(19, "Радиомонтажник", "Художник по дереву"),
    Question(20, "Геолог", "Дипломат"),
    Question(21, "Журналист", "Режиссер"),
    Question(22, "Библиограф", "Аудитор"),
    Question(23, "Фармацевт", "Юрисконсульт"),
    Question(24, "Генетик", "Архитектор"),
    Question(25, "Продавец", "Оператор почтовой связи"),
    Question(26, "Социальный работник", "Предприниматель"),
    Question(27, "Преподаватель вуза", "Музыкант-исполнитель"),
    Question(28, "Экономист", "Менеджер"),
    Question(29, "Корректор", "Дирижер"),
    Question(30, "Инспектор таможни", "Художник-модельер"),
    Question(31, "Телефонист", "Орнитолог"),
    Question(32, "Агроном", "Топограф"),
    Question(33, "Лесник", "Директор"),
    Question(34, "Мастер по пошиву одежды", "Хореограф"),
    Question(35, "Историк", "Инспектор ГАИ"),
    Question(36, "Антрополог", "Экскурсовод"),
    Question(37, "Вирусолог", "Актер"),
    Question(38, "Официант", "Товаровед"),
    Question(39, "Главный бухгалтер", "Инспектор уголовного розыска"),
    Question(40, "Парикмахер-модельер", "Психолог"),
    Question(41, "Пчеловод", "Коммерсант"),
    Question(42, "Судья", "Стенографист"),
]

QUESTIONS_BY_NUMBER = {q.number: q for q in QUESTIONS}
TOTAL_QUESTIONS = len(QUESTIONS)
DB_PATH = "bot_storage.sqlite3"
PAGE_SIZE = 10

VIEW_STATE_AWAIT_MIN = "await_min"
VIEW_STATE_AWAIT_MAX = "await_max"

def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                current_question INTEGER NOT NULL DEFAULT 1,
                answers_json TEXT NOT NULL DEFAULT '{}',
                completed INTEGER NOT NULL DEFAULT 0,
                result_text TEXT,
                sort_order TEXT,
                price_min INTEGER,
                price_max INTEGER,
                view_state TEXT,
                page INTEGER NOT NULL DEFAULT 0,
                liked_ids_json TEXT NOT NULL DEFAULT '[]',
                archetypes_json TEXT NOT NULL DEFAULT '[]'
            )
            """
        )

        # Идемпотентные миграции для случая, если БД уже существовала со
        # старой схемой. Если таблица только что создана выше, цикл просто
        # ничего не делает.
        existing = _table_columns(conn, "user_progress")
        migrations: List[Tuple[str, str]] = [
            ("sort_order", "TEXT"),
            ("price_min", "INTEGER"),
            ("price_max", "INTEGER"),
            ("view_state", "TEXT"),
            ("page", "INTEGER NOT NULL DEFAULT 0"),
            ("liked_ids_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("archetypes_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("recommendations_json", "TEXT NOT NULL DEFAULT '[]'"),
        ]
        for column, ddl in migrations:
            if column not in existing:
                conn.execute(f"ALTER TABLE user_progress ADD COLUMN {column} {ddl}")
        conn.execute(
            "UPDATE user_progress SET sort_order = NULL WHERE sort_order = 'asc'")
        conn.commit()


def get_progress(user_id: int) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT user_id, current_question, answers_json, completed, result_text,
                   sort_order, price_min, price_max, view_state, page, liked_ids_json, 
                   archetypes_json, recommendations_json
            FROM user_progress
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return {
            "user_id": user_id,
            "current_question": 1,
            "answers": {},
            "completed": False,
            "result_text": None,
            "sort_order": None,
            "price_min": None,
            "price_max": None,
            "view_state": None,
            "page": 0,
            "liked_ids": [],
            "archetypes": [],
            "recommendations_json": []
        }

    return {
        "user_id": row["user_id"],
        "current_question": row["current_question"],
        "answers": json.loads(row["answers_json"]),
        "completed": bool(row["completed"]),
        "result_text": row["result_text"],
        "sort_order": row["sort_order"] or None,
        "price_min": row["price_min"],
        "price_max": row["price_max"],
        "view_state": row["view_state"],
        "page": row["page"] or 0,
        "liked_ids": deserialize_liked_ids(row["liked_ids_json"]),
        "archetypes": deserialize_archetypes(row["archetypes_json"]),
        "recommendations_json": row["recommendations_json"]
    }


def save_progress(
    user_id: int,
    current_question: int,
    answers: Dict[str, str],
    completed: bool = False,
    result_text: str | None = None,
    archetypes: List[str] | None = None,
    recommendations: List[Recommendation] | None = None
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_progress (
                user_id,
                current_question,
                answers_json,
                completed,
                result_text
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_question = excluded.current_question,
                answers_json = excluded.answers_json,
                completed = excluded.completed,
                result_text = excluded.result_text
            """,
            (
                user_id,
                current_question,
                json.dumps(answers, ensure_ascii=False),
                int(completed),
                result_text,
            ),
        )
        if archetypes is not None:
            conn.execute(
                "UPDATE user_progress SET archetypes_json = ? WHERE user_id = ?",
                (serialize_archetypes(archetypes), user_id),
            )
        if recommendations is not None:
            conn.execute(
                "UPDATE user_progress SET recommendations_json = ? WHERE user_id = ?",
                (recommendations_to_json(recommendations), user_id),
            )
        conn.commit()


def get_user_repo(user_id: int) -> RecommendationRepository | None:
    progress = get_progress(user_id)
    raw = progress.get("recommendations_json")
    recs = recommendations_from_json(raw)
    if not recs:
        return None
    return InMemoryRecommendationRepository(recs)


def reset_progress(user_id: int) -> None:
    save_progress(
        user_id=user_id,
        current_question=1,
        answers={},
        completed=False,
        result_text=None,
        archetypes=[]
    )
    update_view_settings(
        user_id,
        sort_order=None,
        price_min=None,
        price_max=None,
        view_state=None,
        page=0,
    )


def get_result_ids(all_recs: list):
    return [r.id for r in all_recs]

def update_view_settings(user_id: int, **fields: Any) -> None:
    """Точечное обновление view-настроек пользователя.

    Допустимые поля: sort_order, price_min, price_max, view_state, page.
    """
    allowed = {"sort_order", "price_min", "price_max", "view_state", "page"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unknown view settings: {unknown}")

    if not fields:
        return

    with sqlite3.connect(DB_PATH) as conn:
        # Гарантируем существование строки.
        conn.execute(
            """
            INSERT INTO user_progress (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [user_id]
        conn.execute(
            f"UPDATE user_progress SET {assignments} WHERE user_id = ?",
            values,
        )
        conn.commit()


def serialize_archetypes(archetypes: List[str]) -> str:
    return json.dumps(archetypes, ensure_ascii=False)

def deserialize_archetypes(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]

def serialize_result_ids(ids: List[int]) -> str:
    return json.dumps(ids, ensure_ascii=False)


def deserialize_result_ids(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Старый формат "А,Б,А,..." - сохранение от прошлой версии бота.
        return []
    if not isinstance(data, list):
        return []
    result: List[int] = []
    for item in data:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def serialize_liked_ids(ids: List[int]) -> str:
    return json.dumps(ids, ensure_ascii=False)


def deserialize_liked_ids(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    result: List[int] = []
    for item in data:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result

def recommendations_to_json(recs: List[Recommendation]) -> str:
    return json.dumps([{
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "price": r.price,
        "url": r.url
    } for r in recs], ensure_ascii=False)

def recommendations_from_json(raw: Optional[str]) -> List[Recommendation]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    recs = []
    for item in data:
        if isinstance(item, dict):
            recs.append(Recommendation(
                id=int(item.get("id", 0)),
                title=str(item.get("title", "")),
                description=str(item.get("description", "")),
                price=int(item.get("price", 0)),
                url=str(item.get("url", ""))
            ))
    return recs


def toggle_like(user_id: int, rec_id: int) -> bool:
    """Переключает лайк для рекомендации. Возвращает новое состояние."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_progress (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )
        row = conn.execute(
            "SELECT liked_ids_json FROM user_progress WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        current = deserialize_liked_ids(row[0] if row else None)

        if rec_id in current:
            current.remove(rec_id)
            new_state = False
        else:
            current.append(rec_id)
            new_state = True

        conn.execute(
            "UPDATE user_progress SET liked_ids_json = ? WHERE user_id = ?",
            (serialize_liked_ids(current), user_id),
        )
        conn.commit()

    return new_state


def process_test_results(
    answers: Dict[str, str],
    repo: RecommendationRepository,
) -> List[int]:
    """
    Заглушка под нейронку.

    Сейчас просто возвращает все id из репозитория. Когда появится реальная
    модель, эта функция будет вызывать её и возвращать отобранные id.
    """
    #_ = answers  # пока не используем
    return [item.id for item in repo.list_all()]


def start_keyboard(has_progress: bool, completed: bool) -> InlineKeyboardMarkup:
    buttons = []

    if completed:
        buttons.append(
            [InlineKeyboardButton(text="Посмотреть результат", callback_data="show_result")]
        )
        buttons.append(
            [InlineKeyboardButton(text="Пройти заново", callback_data="restart_test")]
        )
    elif has_progress:
        buttons.append(
            [InlineKeyboardButton(text="Продолжить тест", callback_data="continue_test")]
        )
        buttons.append(
            [InlineKeyboardButton(text="Начать заново", callback_data="restart_test")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="Начать тест", callback_data="start_test")]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def instruction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти к вопросам", callback_data="continue_test")]
        ]
    )


def question_keyboard(question: Question) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"А — {question.a}",
                    callback_data=f"answer:{question.number}:А",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Б — {question.b}",
                    callback_data=f"answer:{question.number}:Б",
                )
            ],
        ]
    )


def finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пройти тест заново", callback_data="restart_test")]
        ]
    )


def build_question_text(question: Question) -> str:
    return (
        f"Вопрос {question.number} из {TOTAL_QUESTIONS}\n\n"
        f"А) {question.a}\n"
        f"Б) {question.b}\n\n"
        "Выберите один вариант:"
    )


def _format_price(value: Optional[int]) -> str:
    if value is None:
        return "—"
    return f"{value:,} ₽".replace(",", " ")


def _format_filter(price_min: Optional[int], price_max: Optional[int]) -> str:
    if price_min is None and price_max is None:
        return "не задан"
    return f"{_format_price(price_min)} – {_format_price(price_max)}"


def _sort_arrow(sort_order: str) -> str:
    return "↑" if sort_order == "asc" else "↓"


def build_results_view(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    progress = get_progress(user_id)
    archetypes = progress.get("archetypes", [])

    repo = get_user_repo(user_id)
    if repo is None:
        text = "Результаты не найдены. Пожалуйста, пройдите тест заново."
        return text, finish_keyboard()

    archetypes_text = ""
    if archetypes:
        archetypes_text = f"Ваши приоритетные архетипы: {', '.join(archetypes)}\n\n"

    result_ids = deserialize_result_ids(progress["result_text"])
    if not result_ids:
        text = (
            "Не удалось загрузить ваши результаты — возможно, сохранение в "
            "старом формате. Пожалуйста, пройдите тест заново."
        )
        return text, finish_keyboard()

    sort_order = progress["sort_order"]
    price_min = progress["price_min"]
    price_max = progress["price_max"]
    page = progress["page"]

    query = repo.query(
        ids=result_ids,
        price_min=price_min,
        price_max=price_max,
        sort_order=sort_order,
        offset=page * PAGE_SIZE,
        limit=PAGE_SIZE,
    )

    total = query.total
    total_pages = max(1, math.ceil(total / PAGE_SIZE)) if total > 0 else 1

    # Clamp page, если фильтр изменился и page стал невалиден.
    if page >= total_pages:
        page = total_pages - 1
        update_view_settings(user_id, page=page)
        query = repo.query(
            ids=result_ids,
            price_min=price_min,
            price_max=price_max,
            sort_order=sort_order,
            offset=page * PAGE_SIZE,
            limit=PAGE_SIZE,
        )

    if total == 0:
        text = archetypes_text + (
            "По заданному фильтру ничего не найдено.\n"
            f"Фильтр: {_format_filter(price_min, price_max)}\n\n"
            "Попробуйте изменить или сбросить фильтр."
        )
    else:
        sort_text = ""
        if sort_order is not None:
            sort_label = "по возрастанию цены" if sort_order == "asc" else "по убыванию цены"
            sort_text = f"Сортировка: {_sort_arrow(sort_order)} {sort_label}\n"
        text = archetypes_text + (
            f"Найдено результатов: {total}\n"
            f"{sort_text}"
            f"Фильтр: {_format_filter(price_min, price_max)}\n"
            f"Страница: {page + 1} / {total_pages}\n\n"
            "Нажмите на интересующий вариант, чтобы посмотреть подробности или добавить в Избранное."
        )

    rows: List[List[InlineKeyboardButton]] = []

    for item in query.items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item.title} — {_format_price(item.price)}",
                    callback_data=f"rec:{item.id}",
                )
            ]
        )

    # Пагинация.
    if total_pages > 1:
        prev_data = "page:prev" if page > 0 else "page:noop"
        next_data = "page:next" if page < total_pages - 1 else "page:noop"
        rows.append(
            [
                InlineKeyboardButton(text="◀", callback_data=prev_data),
                InlineKeyboardButton(
                    text=f"{page + 1}/{total_pages}",
                    callback_data="page:noop",
                ),
                InlineKeyboardButton(text="▶", callback_data=next_data),
            ]
        )

    # Управление.
    if sort_order is None:
        sort_button_text = "Сортировать"
    elif sort_order == "asc":
        sort_button_text = "Сортировка ↑"
    else:
        sort_button_text = "Сортировка ↓"
    rows.append([
            InlineKeyboardButton(text=sort_button_text, callback_data="sort:toggle"),
            InlineKeyboardButton(text="Фильтр цены", callback_data="filter:open"),
        ]
    )

    if price_min is not None or price_max is not None:
        rows.append(
            [InlineKeyboardButton(text="Сбросить фильтр", callback_data="filter:reset")]
        )

    rows.append(
        [InlineKeyboardButton(text="Пройти тест заново", callback_data="restart_test")]
    )

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def build_recommendation_view(
    rec: Recommendation,
    is_liked: bool,
) -> Tuple[str, InlineKeyboardMarkup]:
    text = (
        f"{rec.title}\n\n"
        f"{rec.description}\n\n"
        f"Стоимость: {_format_price(rec.price)}"
    )
    like_button = InlineKeyboardButton(
        text="♥ В избранном" if is_liked else "♡ Добавить в избранное",
        callback_data=f"like:{rec.id}",
    )
    buttons = [[like_button]]
    if rec.url:
        buttons.append(
            [InlineKeyboardButton(text="Перейти на сайт", url=rec.url)])
    buttons.append(
        [InlineKeyboardButton(text="← К списку", callback_data="results:back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


def build_filter_menu(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    progress = get_progress(user_id)
    price_min = progress["price_min"]
    price_max = progress["price_max"]

    text = (
        "Фильтр по цене.\n\n"
        f"Текущий минимум: {_format_price(price_min)}\n"
        f"Текущий максимум: {_format_price(price_max)}\n\n"
        "Выберите, что хотите изменить."
    )

    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Задать минимум", callback_data="filter:set_min")],
        [InlineKeyboardButton(text="Задать максимум", callback_data="filter:set_max")],
    ]
    if price_min is not None or price_max is not None:
        rows.append(
            [InlineKeyboardButton(text="Сбросить", callback_data="filter:reset")]
        )
    rows.append(
        [InlineKeyboardButton(text="← Назад к результатам", callback_data="results:back")]
    )

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


async def send_question(message_or_callback: Message | CallbackQuery, user_id: int) -> None:
    progress = get_progress(user_id)
    current_question = progress["current_question"]

    if current_question > TOTAL_QUESTIONS:
        await finish_test(message_or_callback, user_id)
        return

    question = QUESTIONS_BY_NUMBER[current_question]
    text = build_question_text(question)
    keyboard = question_keyboard(question)

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


async def _send_or_edit(
    message_or_callback: Message | CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)


async def finish_test(message_or_callback: Message | CallbackQuery, user_id: int) -> None:
    progress = get_progress(user_id)
    answers = progress["answers"]

    if len(answers) < TOTAL_QUESTIONS:
        missing = [
            str(i)
            for i in range(1, TOTAL_QUESTIONS + 1)
            if str(i) not in answers
        ]
        text = (
            "Пока заполнены не все ответы.\n"
            f"Не хватает вопросов: {', '.join(missing)}"
        )

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text)
        else:
            await message_or_callback.answer(text)

        return
    df, archetypes = analyze_test(answers)
    repo = DataFrameRecommendationRepository(df)
    all_recs = repo.list_all()
    result_ids = get_result_ids(all_recs)

    save_progress(
        user_id=user_id,
        current_question=TOTAL_QUESTIONS + 1,
        answers=answers,
        completed=True,
        result_text=serialize_result_ids(result_ids),
        archetypes=archetypes,
        recommendations=all_recs,
    )
    # Сбрасываем view-настройки на дефолтные для новой выдачи.
    update_view_settings(
        user_id,
        sort_order=None,
        price_min=None,
        price_max=None,
        view_state=None,
        page=0,
    )

    text, keyboard = build_results_view(user_id)
    intro = "Тест завершён. Вот подобранные для вас варианты:\n\n"
    await _send_or_edit(message_or_callback, intro + text, keyboard)


router_dp = Dispatcher()


@router_dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    progress = get_progress(user_id)

    has_progress = bool(progress["answers"]) and not progress["completed"]

    await message.answer(
        START_TEXT,
        reply_markup=start_keyboard(
            has_progress=has_progress,
            completed=progress["completed"],
        ),
    )


@router_dp.callback_query(F.data == "start_test")
async def on_start_test(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    reset_progress(user_id)

    await callback.message.edit_text(
        f"{INSTRUCTION_TEXT}\n\n"
        "Нажмите кнопку ниже, чтобы перейти к первому вопросу.",
        reply_markup=instruction_keyboard(),
    )
    await callback.answer()


@router_dp.callback_query(F.data == "continue_test")
async def on_continue_test(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await send_question(callback, user_id)
    await callback.answer()


@router_dp.callback_query(F.data == "restart_test")
async def on_restart_test(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    reset_progress(user_id)

    await callback.message.edit_text(
        f"{INSTRUCTION_TEXT}\n\n"
        "Нажмите кнопку ниже, чтобы перейти к первому вопросу.",
        reply_markup=instruction_keyboard(),
    )
    await callback.answer()


@router_dp.callback_query(F.data == "show_result")
async def on_show_result(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    progress = get_progress(user_id)

    if not progress["completed"]:
        await callback.message.edit_text(
            "Тест ещё не завершён.",
            reply_markup=start_keyboard(has_progress=True, completed=False),
        )
        await callback.answer()
        return

    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data == "results:back")
async def on_results_back(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    # На всякий случай очищаем состояние ожидания ввода.
    update_view_settings(user_id, view_state=None)
    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data.startswith("rec:"))
async def on_recommendation_details(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    try:
        _, rec_id_raw = callback.data.split(":", 1)
        rec_id = int(rec_id_raw)
    except ValueError:
        await callback.answer("Некорректный идентификатор.", show_alert=True)
        return

    rec = get_user_repo(user_id).get_by_id(rec_id)
    if rec is None:
        await callback.answer("Вариант не найден.", show_alert=True)
        return

    progress = get_progress(user_id)
    is_liked = rec_id in progress["liked_ids"]
    text, keyboard = build_recommendation_view(rec, is_liked=is_liked)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data.startswith("like:"))
async def on_like_toggle(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        _, rec_id_raw = callback.data.split(":", 1)
        rec_id = int(rec_id_raw)
    except ValueError:
        await callback.answer("Некорректный лайк.", show_alert=True)
        return

    rec = get_user_repo(user_id).get_by_id(rec_id)
    if rec is None:
        await callback.answer("Вариант не найден.", show_alert=True)
        return

    new_state = toggle_like(user_id, rec_id)

    text, keyboard = build_recommendation_view(rec, is_liked=new_state)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(
        "Добавлено в избранное" if new_state else "Убрано из избранного"
    )


@router_dp.callback_query(F.data == "sort:toggle")
async def on_sort_toggle(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    progress = get_progress(user_id)
    current = progress["sort_order"]
    if current is None:
        new_order = "asc"
    elif current == "asc":
        new_order = "desc"
    else:
        new_order = None
    update_view_settings(user_id, sort_order=new_order, page=0)

    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data == "page:prev")
async def on_page_prev(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    progress = get_progress(user_id)
    new_page = max(0, progress["page"] - 1)
    update_view_settings(user_id, page=new_page)

    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data == "page:next")
async def on_page_next(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    progress = get_progress(user_id)
    new_page = progress["page"] + 1
    update_view_settings(user_id, page=new_page)

    # build_results_view сам сделает clamp, если new_page вышел за границы.
    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data == "page:noop")
async def on_page_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router_dp.callback_query(F.data == "filter:open")
async def on_filter_open(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    # Если пользователь зашёл в меню — снимаем флаг ожидания ввода.
    update_view_settings(user_id, view_state=None)
    text, keyboard = build_filter_menu(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data == "filter:set_min")
async def on_filter_set_min(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    update_view_settings(user_id, view_state=VIEW_STATE_AWAIT_MIN)
    await callback.message.edit_text(
        "Введите минимальную цену целым числом (например, 5000).\n"
        "Отправьте 0, чтобы убрать ограничение снизу."
    )
    await callback.answer()


@router_dp.callback_query(F.data == "filter:set_max")
async def on_filter_set_max(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    update_view_settings(user_id, view_state=VIEW_STATE_AWAIT_MAX)
    await callback.message.edit_text(
        "Введите максимальную цену целым числом (например, 50000).\n"
        "Отправьте 0, чтобы убрать ограничение сверху."
    )
    await callback.answer()


@router_dp.callback_query(F.data == "filter:reset")
async def on_filter_reset(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    update_view_settings(
        user_id,
        price_min=None,
        price_max=None,
        view_state=None,
        page=0,
    )
    text, keyboard = build_results_view(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router_dp.callback_query(F.data.startswith("answer:"))
async def on_answer(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id

    try:
        _, question_number_raw, choice = callback.data.split(":")
        question_number = int(question_number_raw)
    except ValueError:
        await callback.answer("Некорректный ответ.", show_alert=True)
        return

    progress = get_progress(user_id)

    if progress["completed"]:
        await callback.answer("Тест уже завершен.", show_alert=True)
        return

    current_question = progress["current_question"]

    if question_number != current_question:
        await callback.answer(
            "Этот вопрос уже неактуален. Откройте текущий вопрос.",
            show_alert=True,
        )
        await send_question(callback, user_id)
        return

    if choice not in {"А", "Б"}:
        await callback.answer("Некорректный вариант ответа.", show_alert=True)
        return

    answers = progress["answers"]
    answers[str(question_number)] = choice

    next_question = question_number + 1

    save_progress(
        user_id=user_id,
        current_question=next_question,
        answers=answers,
        completed=False,
    )

    if next_question > TOTAL_QUESTIONS:
        await finish_test(callback, user_id)
    else:
        await send_question(callback, user_id)

    await callback.answer()


@router_dp.message(F.text)
async def on_text_message(message: Message) -> None:
    user_id = message.from_user.id
    progress = get_progress(user_id)
    view_state = progress["view_state"]

    if view_state not in {VIEW_STATE_AWAIT_MIN, VIEW_STATE_AWAIT_MAX}:
        return

    raw = (message.text or "").strip().replace(" ", "")
    try:
        value = int(raw)
    except ValueError:
        await message.answer(
            "Не удалось распознать число. Введите целое неотрицательное число, "
            "например 5000. Или отправьте 0, чтобы убрать ограничение."
        )
        return

    if value < 0:
        await message.answer("Значение не может быть отрицательным. Попробуйте ещё раз.")
        return

    new_value: Optional[int] = None if value == 0 else value

    if view_state == VIEW_STATE_AWAIT_MIN:
        # Проверим согласованность с максимумом.
        if (
            new_value is not None
            and progress["price_max"] is not None
            and new_value > progress["price_max"]
        ):
            await message.answer(
                f"Минимум ({new_value}) не может быть больше текущего "
                f"максимума ({progress['price_max']}). Введите другое значение."
            )
            return
        update_view_settings(
            user_id,
            price_min=new_value,
            view_state=None,
            page=0,
        )
    else:  # VIEW_STATE_AWAIT_MAX
        if (
            new_value is not None
            and progress["price_min"] is not None
            and new_value < progress["price_min"]
        ):
            await message.answer(
                f"Максимум ({new_value}) не может быть меньше текущего "
                f"минимума ({progress['price_min']}). Введите другое значение."
            )
            return
        update_view_settings(
            user_id,
            price_max=new_value,
            view_state=None,
            page=0,
        )

    text, keyboard = build_results_view(user_id)
    await message.answer("Фильтр обновлён.\n\n" + text, reply_markup=keyboard)


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Не найден BOT_TOKEN в .env")

    logging.basicConfig(level=logging.INFO)

    init_db()

    bot = Bot(token=token)
    await router_dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
