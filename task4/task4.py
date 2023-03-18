import math
import os
import zipfile
from collections import Counter
import re

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


def get_tf_idf(text: str, docs: list[set[str]]) -> list[tuple[str, int, int]]:
    """
    Получить TF-IDF текста. Предполагается, что `text` это документ

    :param text: текст документа, для которого нужно посчитать TF-IDF.
    :param docs: список множества слов в документах
    :return: список кортежей, каждый из которых представляет собой: токен, tf, idf.
    """

    tokens = text.split()
    tokens_set = set(tokens)

    # подсчет TF
    tfs = Counter(tokens)

    # подсчет IDF
    token_entries = {token: len([doc for doc in docs if token in doc]) for token in tokens_set}
    idfs = {token: math.log10(len(docs) / token_entries[token]) for token in tokens_set}

    return [(token, tfs[token], idfs[token]) for token in tokens_set]


def write_tf_idf(path: str, tf_idfs: list[tuple[str, int, int]]):
    """
    Записать результаты

    :param path:
    :return:
    """
    with open(path, "w", encoding="utf8") as f:
        f.writelines([" ".join(str(i) for i in line) + "\n" for line in tf_idfs])


if __name__ == "__main__":
    prevalidate_env_variables()
    dir_path = os.getenv("POSTS_DIR_PATH")

    morph = init_morph()

    tf_idfs_path = os.getenv("TF_IDFS_PATH")

    extract_archive(dir_path)
    texts = get_all_texts(dir_path)
    texts_words = get_words_set_per_doc(list(texts.values()))

    if not os.path.isdir(tf_idfs_path):
        os.mkdir(tf_idfs_path)

    # считаем tf-idf для терминов
    for filename, text in texts.items():
        tf_idf = get_tf_idf(text, texts_words)
        write_tf_idf(os.path.join(tf_idfs_path, "tokens" + filename), tf_idf)

    normalized_texts = {filename: normalize(text, morph) for filename, text in texts.items()}
    normalized_texts_words = get_words_set_per_doc(list(normalized_texts.values()))

    # считаем tf-idf для лемм
    for filename, text in normalized_texts.items():
        tf_idf = get_tf_idf(text, normalized_texts_words)
        write_tf_idf(os.path.join(tf_idfs_path, "lemmes" + filename), tf_idf)
