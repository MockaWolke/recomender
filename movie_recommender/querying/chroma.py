from movie_recommender.querying.sql_models import Movie
from movie_recommender import REPO_PATH, CHROMA_PORT
import chromadb
import tqdm
import math
import os
from typing import Dict, List, Set, Tuple
from loguru import logger

os.chdir(REPO_PATH)


class CHROMA_Manager:
    _instance = None

    @classmethod
    def get_instance(cls, *args, **kwarfs):
        if cls._instance is None:
            cls._instance = CHROMA_Manager(*args, **kwarfs)

        return cls._instance

    def __init__(self, batchsize=100) -> None:
        self.client = chromadb.PersistentClient(str(REPO_PATH / "chroma/"))

        # try:
        #     self.client = chromadb.HttpClient(port=CHROMA_PORT)

        # except (
        #     ConnectionError,
        #     ValueError,
        #     ConnectionRefusedError,
        #     ConnectionAbortedError,
        # ):
        #     logger.error(
        #         f"Found now chroma running on {CHROMA_PORT}. Just run 'bash start-chroma.sh'"
        #     )

        self.collection = self.client.get_or_create_collection(
            "imdb", metadata={"hnsw:space": "cosine"}
        )
        self.batchsize = batchsize

    def get_set_movies(self):
        return set(self.collection.get()["ids"])

    @property
    def isfull(self):
        movies_with_imdb = Movie.query.filter(Movie.imdb_data_id.isnot(None)).all()
        allready = self.get_set_movies()

        ids = {str(movie.id) for movie in movies_with_imdb}

        missing = ids.difference(allready)

        return True if not missing else missing

    def fill(self):
        movies_with_imdb = Movie.query.filter(Movie.imdb_data_id.isnot(None)).all()

        allready = self.get_set_movies()

        new_movies = [
            movie for movie in movies_with_imdb if str(movie.id) not in allready
        ]

        for i in tqdm.tqdm(
            range(int(math.ceil(len(new_movies) / self.batchsize))),
            f"Adding new movies to chroma with self.batchsize {self.batchsize}",
        ):
            items = new_movies[i * self.batchsize : (i + 1) * self.batchsize]

            ids = [str(i.id) for i in items]
            documents = [i.imdb_data.summary for i in items]
            self.collection.add(ids=ids, documents=documents)

    def query(
        self, movie_id: int, top_k
    ) -> Tuple[List[int], List[int],]:
        movie_id = str(movie_id)

        em = self.collection.get(ids=movie_id, include=["embeddings"])["embeddings"]

        if len(em) == 0:
            logger.info(f"No embedding for {movie_id}")
            return [], []

        res = self.collection.query(query_embeddings=em, n_results=top_k + 1)
        ids = [int(c) for c in res["ids"][0][1:]]

        distances = res["distances"][0][1:]
        similarity = [1 - i for i in distances]

        return ids, similarity
