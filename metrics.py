import math

from bot import get_progress, deserialize_archetypes,deserialize_liked_ids
import sqlite3
import json

from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DB_PATH = "bot_storage.sqlite3"

GLOSSARY = {
    "Предпринимательский":
        [
            {"cluster": 0, "size": 41},
            {"cluster": 3, "size": 21},
            {"cluster": 7, "size": 49}
        ],
    "Исследовательский":
        [
            {"cluster": 1, "size": 52},
            {"cluster": 8, "size": 128}
        ],
    "Социальный":
        [
            {"cluster": 2, "size": 86},
            {"cluster": 5, "size": 20},
            {"cluster": 9, "size": 31}
        ],
    "Конвенциональный":
        [
            {"cluster": 4, "size": 59}
        ],
    "Артистический":
        [
            {"cluster": 6, "size": 124}
        ]
}

def get_data():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT user_id, current_question, answers_json, completed, result_text,
                   sort_order, price_min, price_max, view_state, page, liked_ids_json, 
                   archetypes_json, recommendations_json
            FROM user_progress
            """
        )

    if rows is None:
        return {
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
    list =  []
    for row in rows:
        list.append(
            {
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
                "recommendations_json": json.loads(row["recommendations_json"])
            }
        )

    return list

DATAFRAME = get_data()

def gain_helper(marked, origin):
    mask = []
    for i in origin:
        if i in marked:
            mask.append(1)
        else:
            mask.append(0)
    return mask


def ideal_gain(lenght):
    return sum([1 / math.log2(i + 1) for i in range(1, lenght + 1)])


def gain(marked, origin):
    mask = gain_helper(marked, origin)
    acc = 0
    for i in range(1, len(mask) + 1):
        acc += mask[i - 1] / math.log2(i + 1)
    return acc

def compute_diversity_tfidf(descriptions: List[str]) -> float:
    n = len(descriptions)
    if n < 2:
        return 0.0

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(descriptions)

    # Попарное косинусное сходство (разреженная матрица -> плотный массив)
    sim_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Берём верхний треугольник без диагонали
    i_upper = np.triu_indices(n, k=1)
    pairwise_similarities = sim_matrix[i_upper]

    avg_sim = float(np.mean(pairwise_similarities))
    return 1.0 - avg_sim


def get_metrics():
    for user in DATAFRAME:
        if not user['completed']:
            continue
        descriptions = [str(course.get('title', '')) + ' ' + str(course.get('description', '')) for course in user['recommendations_json']]
        courses = user['result_text']
        likes = user['liked_ids']
        archetypes = user['archetypes']
        k = len(courses)
        likes_count = len(likes)

        precision = likes_count / k
        recallK = likes_count / (sum([cluster['size'] for arch in archetypes for cluster in GLOSSARY[arch]]))
        dcg = gain(likes, courses) / ideal_gain(k)
        diversity = compute_diversity_tfidf(descriptions)

        return f"Метрики на основе выборки\n" \
               f"Precision: {precision},\n" \
               f"Recall: {recallK},\n" \
               f"NDCG: {dcg},\n" \
               f"Diversity: {diversity}"


print(get_metrics())