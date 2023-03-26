import os

from fastapi import FastAPI, Query
from starlette.responses import StreamingResponse

from task5.task5 import (
    prevalidate_env_variables,
    init_morph,
    load_lemmes,
    load_index,
    extract_archive,
    get_all_texts,
    get_words_set_per_doc,
    generate_vectors,
    normalize,
    get_cosine_similarity,
    get_tf_idf,
)

app = FastAPI()

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


@app.get("/")
def index_page():
    return StreamingResponse(open("task5/index.html", "rb"), media_type="text/html")


@app.get("/search/")
def search(query: str = Query(..., description="Поисковый запрос")):
    query = normalize(query, morph)
    if query == "":
        return []
    query_tf_idf = {
        lemmes.index(token): float(tf) * float(idf) for token, tf, idf in get_tf_idf(query, normalized_texts_words) if token in lemmes_set
    }
    if not len(query_tf_idf):
        return []
    similarities = {doc: get_cosine_similarity(query_tf_idf, tf_idf) for doc, tf_idf in tf_idfs.items()}
    sorted_similarities = list(sorted(similarities.items(), key=lambda s: -s[1]))
    return [(index[similarity[0]], similarity[1]) for similarity in sorted_similarities]
