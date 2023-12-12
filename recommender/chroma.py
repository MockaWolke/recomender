from recommender.sql_models import Movie
from recommender import REPO_PATH
import chromadb
import tqdm
import math
import os

os.chdir(REPO_PATH)

CHROMA_DIR = str(REPO_PATH / "chroma")
os.makedirs(CHROMA_DIR, exist_ok=True)


class CHROMA_Manager:
    _instance = None

    @classmethod
    def get_instance(cls, *args, **kwarfs):
        if cls._instance is None:
            cls._instance = CHROMA_Manager(*args, **kwarfs)

        return cls._instance

    def __init__(self, batchsize=100) -> None:
        self.client = chromadb.PersistentClient(CHROMA_DIR)
        self.collection = self.client.get_or_create_collection("imdb")
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

    def query(self):
        raise NotImplementedError()
