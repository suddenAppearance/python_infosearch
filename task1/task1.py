import json
import os
import shutil

from httpx import Client
from urllib3.util import Url


def prevalidate_env_variables():
    assert os.getenv("APP_ID"), "Укажите VK API App ID в переменную окружения APP_ID"
    assert os.getenv("GROUP_ID"), "Укажите ID группы в переменную окружения GROUP_ID"
    assert os.getenv("POSTS_DIR_PATH"), "Укажите путь для папки и архива в переменную окружения POSTS_DIR_PATH"


def initialize_api() -> Client:
    """
    Иницализация клиента httpx для VK API
    :return: кортеж состоящий из клиента и токена доступа
    """

    if not (token := os.getenv("ACCESS_TOKEN")):
        print("Перейдите` по ссылке:")
        print(
            "https://oauth.vk.com/authorize?"
            f"client_id={os.getenv('APP_ID')}&"
            "display=page&"
            "redirect_uri=https://oauth.vk.com/blank.html&"
            "scope=offline&"
            "response_type=token&"
            "v=5.131"
        )
        token = input("Введите токен: ")
        if not token:
            raise ValueError(
                "Подставьте значение access_token из командной строки. "
                "Чтобы не выполнять эту операцию, сохраните его в переменную окружения ACCESS_TOKEN"
            )

    client = Client(base_url="https://api.vk.com/method/", params={"access_token": token, "v": "5.131"})
    assert client.get("account.getAppPermissions").json().get("response"), "Invalid token"
    return client


def fetch_posts(client: Client, group_id: str, count: int = 100, min_length: int = 1000) -> list[dict]:
    """
    Запрос постов группы вк
    :param client: клиент вк с настроенными доступами
    :param group_id: идентификатор группы
    :param count: итоговое количество постов
    :param min_length: минимальная длинна текста в записи
    :return: список элементов структуры `Запись на стене <https://dev.vk.com/reference/objects/post>`_
    """
    posts = []
    offset = 0
    while len(posts) < count:
        response = client.get(
            url='wall.get',
            params={
                "owner_id": group_id,
                "offset": offset,
                "count": 100
            }
        ).json()
        for post in response['response']['items']:
            if len(post['text']) >= min_length:
                posts.append(post)
        offset += 100

    return posts[:100]


def __build_url(post: dict) -> Url:
    """
    Построить URL из данных поста
    :param post: данные поста
    :return: объект `urllib3.util.Url` с URL поста
    """
    return Url(scheme="https", host="vk.com", path=f"wall{post['owner_id']}_{post['id']}")


def generate_directory(dir_path: str, posts: list[dict], index_path: str = "./index.txt"):
    """
    Сгенерировать директорию с текстовыми файлами постов
    :param dir_path: путь до директории
    :param posts: список постов
    :param index_path: путь до index файла
    """
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
    indexes = []
    for post in posts:
        post_path = f"{post['id']}.txt"
        post_url = str(__build_url(post))

        with open(os.path.join(dir_path, post_path), "w", encoding="utf8") as post_file:
            post_file.write(post["text"])
        indexes.append("\t".join((post_path, post_url)) + "\n")

    with open(index_path, "w", encoding="utf8") as index:
        index.writelines(indexes)


def archive_directory(dir_path: str) -> None:
    """
    Заархивировать директорию
    :param dir_path: путь до директории
    """
    shutil.make_archive(dir_path, 'zip', dir_path)
    shutil.rmtree(dir_path)


def main():
    prevalidate_env_variables()
    client = initialize_api()
    posts = fetch_posts(client, group_id=os.getenv("GROUP_ID"))
    dir_path = os.getenv("POSTS_DIR_PATH")
    generate_directory(dir_path, posts)
    archive_directory(dir_path)


if __name__ == '__main__':
    main()
