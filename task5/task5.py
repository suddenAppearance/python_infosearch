import math
import os
import re
import zipfile
from collections import Counter, defaultdict
from typing import Literal

from pymorphy2 import MorphAnalyzer
from pymorphy2.analyzer import Parse


def prevalidate_env_variables():
    assert os.getenv("POSTS_DIR_PATH"), "Укажите путь для папки и архива в переменную окружения POSTS_DIR_PATH"
    assert os.getenv("LEMMES_PATH"), "Укажите путь для файла лемм в переменную окружения LEMMES_PATH"
    assert os.getenv("TF_IDFS_PATH"), "Укажите путь для папки, в которую поместятся результаты в переменную TF-IDF"


def init_morph() -> MorphAnalyzer:
    """
    Инициализировать морфологический анализатор
    :return: объект `pymorphy2.MorphAnalyzer`
    """
    return MorphAnalyzer()


def extract_archive(dir_path: str):
    """
    Разархивировать архив.

    :param dir_path: путь до архива без расширения
    """
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
    with zipfile.ZipFile(f"{dir_path}.zip", "r") as zip_ref:
        zip_ref.extractall(dir_path)


def preprocess_text(text: str) -> str:
    """
    Очистить текст от некириллических символов

    :param text: текст для очистки.
    :return: очищенный текст.
    """
    pattern = re.compile(r"[^А-Яа-я ]")
    return re.sub(pattern, ' ', text)


def get_all_texts(dir_path: str) -> dict[str, str]:
    """
    Получить тексты всех документов

    :param dir_path: директория с файлами.
    :return: список текстов всех документов в этой дериктории
    """

    texts = {}
    for file in os.listdir(dir_path):
        if file.endswith(".txt"):
            texts[file] = preprocess_text(open(os.path.join(dir_path, file), "r", encoding="utf8").read())

    return texts


def normalize(text: str, morph: MorphAnalyzer) -> str:
    """
    Вернуть нормализованный текст.

    :param text: текст документа
    :param morph: объект анализатора
    :return: строку нормализованного текста
    """
    lemmes = list()

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

        lemmes.append(token.normal_form)

    return " ".join(lemmes)


def get_words_set_per_doc(docs: list[str]) -> list[set[str]]:
    """
    Получить множество слов для каждого документа

    :param docs: список документов
    :return: список множества слов для каждого документа
    """

    return [set(doc.split()) for doc in docs]


def load_lemmes(lemmes_path: str) -> set[str]:
    """
    Загрузить леммы из файла

    :param lemmes_path: путь до файла с леммами.
    :return: множество лемм
    """
    with open(lemmes_path, "r", encoding="utf8") as f:
        return {line.split()[0] for line in f.readlines()}


def load_index(index_path: str) -> dict[str, str]:
    with open(index_path, "r", encoding="utf8") as f:
        return {filename: link for filename, link in (link.split() for link in f.readlines())}


def get_tf_idf(text: str, docs: list[set[str]]) -> list[tuple[str, float, int]]:
    """
    Получить TF-IDF текста. Предполагается, что `text` это документ

    :param text: текст документа, для которого нужно посчитать TF-IDF.
    :param docs: список множества слов в документах.
    :return: список кортежей, каждый из которых представляет собой: токен, tf, idf.
    """

    tokens = text.split()
    tokens_set = set(tokens)

    # подсчет TF
    tfs = Counter(tokens)

    # подсчет IDF
    token_entries = {token: len([doc for doc in docs if token in doc]) for token in tokens_set}
    idfs = {token: math.log10(len(docs) / token_entries[token]) if token_entries[token] else 0 for token in tokens_set}

    return [(token, tfs[token] / len(tokens), idfs[token]) for token in tokens_set]


def generate_vectors(
        tf_idfs_path: str, lemmes: list[str],
        prefix: Literal["lemmes", "tokens"] = "lemmes"
):
    tf_idfs = {}
    for file in os.listdir(tf_idfs_path):
        if file.startswith(prefix):
            with open(os.path.join(tf_idfs_path, file), "r", encoding="utf8") as f:
                key = file.lstrip(prefix)
                tf_idfs[key] = defaultdict(float)
                for line in f.readlines():
                    token, tf, idf = line.split()
                    tf_idfs[key][lemmes.index(token)] = float(tf) * float(idf)

    return tf_idfs


def get_cosine_similarity(vec1: dict[int, float], vec2: dict[int, float]):
    return (
            sum(value * vec2[key] for key, value in vec1.items()) /
            (
                    sum(value ** 2 for value in vec1.values()) ** 0.5
                    * sum(value ** 2 for value in vec2.values()) ** 0.5
            )
    )


if __name__ == '__main__':
    print("Загрузка индексов")
    prevalidate_env_variables()
    dir_path = os.getenv("POSTS_DIR_PATH")
    morph = init_morph()

    tf_idfs_path = os.getenv("TF_IDFS_PATH")

    lemmes_set = load_lemmes(os.getenv("LEMMES_PATH"))
    index = load_index("index.txt")
    extract_archive(dir_path)
    texts = get_all_texts(dir_path)

    texts_words = get_words_set_per_doc(list(texts.values()))
    lemmes = list(lemmes_set)
    tf_idfs = generate_vectors(os.getenv("TF_IDFS_PATH"), lemmes)

    normalized_texts = {filename: normalize(text, morph) for filename, text in texts.items()}
    normalized_texts_words = get_words_set_per_doc(list(normalized_texts.values()))

    while (query := normalize(input("Введите запрос: "), morph)) != "":
        query_tf_idf = {
            lemmes.index(token): float(tf) * float(idf) for token, tf, idf in get_tf_idf(query, normalized_texts_words)
        }
        similarities = {doc: get_cosine_similarity(query_tf_idf, tf_idf) for doc, tf_idf in tf_idfs.items()}

        sorted_similarities = list(sorted(similarities.items(), key=lambda s: -s[1]))
        for i, similarity in enumerate(sorted_similarities[:5]):
            print(f"{i + 1}. {index[similarity[0]]} (сходство: {similarity[1]})")

        print()