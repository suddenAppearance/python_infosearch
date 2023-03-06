import json
import os
from functools import lru_cache

from pymorphy2 import MorphAnalyzer
from pymorphy2.analyzer import Parse


def prevalidate_env_variables():
    assert os.getenv("INDEX_PATH"), "Укажите путь для файла индекса в переменную окружения INDEX_PATH"


def init_morph() -> MorphAnalyzer:
    """
    Инициализировать морфологический анализатор
    :return: объект `pymorphy2.MorphAnalyzer`
    """
    return MorphAnalyzer()


morph = init_morph()


def print_help_message():
    print(
        """
        Поиск по индексу.\n\n 
        
        Слова написанные через пробел автоматически объединяются с помощью AND.\n
        Минус перед словом означает NOT.\n
        Например:\n
        здесь -есть | другой\n
        означает: документы, где есть слово "здесь", но нет слова "есть", или документы где есть слово "другой"
        """.strip()
    )
    print()


def load_index(index_path: str):
    assert os.path.isfile(index_path), "Указанный путь до индекса не существует."
    index = {}
    with open(index_path, "r", encoding="utf8") as f:
        rows = f.readlines()
        for row in rows:
            data = json.loads(row)
            index[data["word"]] = {"documents": set(data["documents"]), "count": data["count"]}

    return index


def get_all_docs(index: dict[str, dict[str, set | int]]) -> set[str]:
    docs = set()
    for value in index.values():
        docs |= value["documents"]

    return docs


def search(query: str, index: dict[str, dict[str, set | int]]) -> set[str]:
    if not len(query):
        return set()

    tokens = query.split("|")
    # if multiple - recursive search and union results
    if len(tokens) > 1:
        result = set()
        for token in tokens:
            result = result.union(search(token, index))
        return result

    # if single - recursive search and intersect or subtract (if negative)
    tokens = tokens[0].split()
    if len(tokens) > 1 or tokens[0].startswith("-"):
        result = get_all_docs(index)

        for token in tokens:
            clear_token = token.strip()
            if clear_token.startswith("-"):
                result = result - search(token.lstrip("-"), index)
            else:
                result = result.intersection(search(token, index))

        return result

    words: list[Parse] = morph.parse(tokens[0])
    word = words[0].normal_form
    return index[word]["documents"] if index.get(word) else set()


if __name__ == '__main__':
    prevalidate_env_variables()
    index = load_index(os.getenv("INDEX_PATH"))
    print(search(input("Введите поисковый запрос: "), index))
