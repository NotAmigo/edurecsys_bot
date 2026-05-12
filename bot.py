from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv


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


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                current_question INTEGER NOT NULL DEFAULT 1,
                answers_json TEXT NOT NULL DEFAULT '{}',
                completed INTEGER NOT NULL DEFAULT 0,
                result_text TEXT
            )
            """
        )
        conn.commit()


def get_progress(user_id: int) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT user_id, current_question, answers_json, completed, result_text
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
        }

    return {
        "user_id": row["user_id"],
        "current_question": row["current_question"],
        "answers": json.loads(row["answers_json"]),
        "completed": bool(row["completed"]),
        "result_text": row["result_text"],
    }


def save_progress(
    user_id: int,
    current_question: int,
    answers: Dict[str, str],
    completed: bool = False,
    result_text: str | None = None,
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
        conn.commit()


def reset_progress(user_id: int) -> None:
    save_progress(
        user_id=user_id,
        current_question=1,
        answers={},
        completed=False,
        result_text=None,
    )

def process_test_results(answers: Dict[str, str]) -> str:
    """
    Заглушка.

    answers хранится как словарь:
    {
        "1": "А",
        "2": "Б",
        ...
    }

    Возвращает строку вида:
    А,Б,А,А,...
    """
    ordered_answers = [
        answers[str(question_number)]
        for question_number in range(1, TOTAL_QUESTIONS + 1)
    ]

    return ",".join(ordered_answers)

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

    result_text = process_test_results(answers)

    save_progress(
        user_id=user_id,
        current_question=TOTAL_QUESTIONS + 1,
        answers=answers,
        completed=True,
        result_text=result_text,
    )

    text = (
        "Тест завершен.\n\n"
        "Результат обработки:\n"
        f"{result_text}"
    )

    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=finish_keyboard())
    else:
        await message_or_callback.answer(text, reply_markup=finish_keyboard())

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
            "Тест еще не завершен.",
            reply_markup=start_keyboard(has_progress=True, completed=False),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "Ваш сохраненный результат:\n\n"
        f"{progress['result_text']}",
        reply_markup=finish_keyboard(),
    )
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