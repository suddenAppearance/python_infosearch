import json
import os
import shutil
import zipfile
from collections import defaultdict

from pymorphy2 import MorphAnalyzer
from pymorphy2.analyzer import Parse


def prevalidate_env_variables():
    assert os.getenv("POSTS_DIR_PATH"), "Укажите путь для папки и архива в переменную окружения POSTS_DIR_PATH"
    assert os.getenv("LEMMES_PATH"), "Укажите путь для файла лемм в переменную окружения LEMMES_PATH"
    assert os.getenv("INDEX_PATH"), "Укажите путь для файла индекса в переменную окружения INDEX_PATH"


def init_morph() -> MorphAnalyzer:
    """
    Инициализировать морфологический анализатор
    :return: объект `pymorphy2.MorphAnalyzer`
    """
    return MorphAnalyzer()


def extract_archive(dir_path: str):
    """
    Разархивировать архмв
    :param dir_path: путь до архива без расширения
    """
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
    with zipfile.ZipFile(f"{dir_path}.zip", "r") as zip_ref:
        zip_ref.extractall(dir_path)


def clear(dir_path: str):
    """
    Удалить папку с файлами
    :param dir_path: путь до папки с файлами
    """
    shutil.rmtree(dir_path)


def normalize(text: str, morph: MorphAnalyzer) -> set[str]:
    """
    Вернуть список лемм по тексту
    :param text: текст документа
    :param morph: объект анализатора
    :return: множество лемм
    """
    lemmes = set()

    words = text.split()
    for word in words:
        token: Parse = morph.parse(word)[0]

        bad = False
        for bad_grammeme in [
            "PREP",  # предлог
            "CONJ",  # союз
            "NUMB",  # число
            "NUMR",  # числительное
            "LATN",  # не кириллица
            "PNCT",  # пунктуация
            "ROMN",  # римское число
            "UNKN",  # неизвестное слово
        ]:
            if bad_grammeme in token.tag:
                bad = True
                break

        if bad:
            continue

        lemmes.add(token.normal_form)

    return lemmes


def get_inverted_index(dir_path: str, morph: MorphAnalyzer) -> dict[str, dict[str, set | int]]:
    inverted_index = defaultdict(lambda: {"documents": set(), "count": 0})
    for file in os.listdir(dir_path):
        if file.endswith(".txt"):
            text = open(os.path.join(dir_path, file), "r", encoding="utf8").read()
            lemmes = normalize(text, morph)
            for lemme in lemmes:
                inverted_index[lemme]["documents"].add(file)
                inverted_index[lemme]["count"] += 1

    return dict(sorted(inverted_index.items(), key=lambda s: s[1]["count"]))


def write_index(index_path: str, index: dict[str, dict[str, set | int]]):
    with open(index_path, "w", encoding="utf8") as f:
        for key, value in index.items():
            f.write(
                json.dumps(
                    {"word": key, "documents": list(value["documents"]), "count": value["count"]},
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )


if __name__ == "__main__":
    prevalidate_env_variables()
    dir_path = os.getenv("POSTS_DIR_PATH")
    extract_archive(dir_path)
    morph = init_morph()
    index = get_inverted_index(dir_path, morph)
    write_index(os.getenv("INDEX_PATH"), index)
    clear(dir_path)
