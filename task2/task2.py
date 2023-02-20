import os
import re
import shutil
import zipfile
from collections import defaultdict

from pymorphy2 import MorphAnalyzer
from pymorphy2.analyzer import Parse


def prevalidate_env_variables():
    assert os.getenv("POSTS_DIR_PATH"), "Укажите путь для папки и архива в переменную окружения POSTS_DIR_PATH"
    assert os.getenv("TOKENS_PATH"), "Укажите путь для файла токенов в переменную окружения TOKENS_PATH"
    assert os.getenv("LEMMES_PATH"), "Укажите путь для файла лемм в переменную окружения LEMMES_PATH"


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


def concat_all_files(dir_path: str) -> str:
    """
    Объединить текст всех .txt файлов в директории
    :param dir_path: директория с файлами
    :return: строка сконкатенированных файлов
    """
    texts = []
    for file in os.listdir(dir_path):
        if file.endswith(".txt"):
            texts.append(open(os.path.join(dir_path, file), "r", encoding="utf8").read())

    return "\n".join(texts)


def clear(dir_path):
    shutil.rmtree(dir_path)


def preprocess_text(text: str) -> str:
    pattern = re.compile(r"[^А-Яа-я ]")
    return re.sub(pattern, '', text)


def tokenize(text: str, morph: MorphAnalyzer) -> dict[str, set[str]]:
    tokens_dict = defaultdict(set)

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

        tokens_dict[token.normal_form].add(token.word)

    return tokens_dict


def write_tokens(tokens_path: str, lemmes_path: str, tokens_dict: dict[str, set[str]]):
    with open(tokens_path, "w", encoding="utf8") as tokens_file, open(lemmes_path, "w", encoding="utf8") as lemmes_file:
        for lemme, tokens in tokens_dict.items():
            tokens_file.write("\n".join(tokens) + "\n")
            lemmes_file.write(" ".join((lemme, *tokens)) + "\n")


def main():
    prevalidate_env_variables()
    dir_path = os.getenv('POSTS_DIR_PATH')

    morph = init_morph()
    extract_archive(dir_path)
    text = concat_all_files(dir_path)
    text = preprocess_text(text)
    tokens_dict = tokenize(text=text, morph=morph)
    write_tokens(os.getenv("TOKENS_PATH"), os.getenv("LEMMES_PATH"), tokens_dict)
    clear(dir_path)


if __name__ == '__main__':
    main()
