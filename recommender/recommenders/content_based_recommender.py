from typing import List, Tuple, Dict, Set
from recommender.querying.sql_models import (
    Movie,
    Actor,
    Director,
    movie_actors,
    movie_directors,
)  # Assuming models are in a file named models.py
from collections import defaultdict
from loguru import logger
from recommender.querying.chroma import CHROMA_Manager


class ContentBasedRecommender:
    weights = {
        "directors": 1,
        "actors": 0.2,
        "plots": 1.2,
    }

    def find_most_simmilar(
        self, movies: List[Movie], ratings: List[float]
    ) -> Tuple[List[Movie], List[float]]:
        """returns list of movies and similartiy scores"""

        assert len(movies) == len(ratings)

        import time

        start_time = time.time()

        actor_scores, director_scores, plot_scores = self.get_scores(movies, ratings)

        logger.info(f"the scores {time.time()- start_time}")

        total_scores: Dict[Movie, float] = defaultdict(lambda: 0)

        for movie, val in actor_scores.items():
            total_scores[movie] += val * self.weights["actors"]

        for movie, val in director_scores.items():
            total_scores[movie] += val * self.weights["directors"]

        for movie, val in plot_scores.items():
            total_scores[movie] += val * self.weights["plots"]

        # delete the inputs
        for movie in movies:
            if movie in total_scores:
                del total_scores[movie]

        sorted_movies = list(
            filter(
                lambda key: total_scores[key] > 0,
                sorted(total_scores.keys(), key=total_scores.get, reverse=True),
            )
        )

        scores = [total_scores[movie] for movie in sorted_movies]

        return sorted_movies, scores

    def get_scores(
        self, movies: List[Movie], ratings: List[float]
    ) -> Tuple[Dict, Dict, Dict]:
        """Given a list of movie we find the movies which are most similar to them"""

        # first the directors
        director_scores: Dict[Movie, int] = defaultdict(lambda: 0)

        import time

        start = time.time()

        for movie, rating in zip(movies, ratings):
            director = self.get_director(movie)

            if director is None:
                logger.info(f"Cant find director for {movie.title}")
                continue

            for other_movie in self.get_movies_of_director(director):
                if other_movie.id == movie.id:
                    continue

                director_scores[other_movie] += rating

        logger.info(f"direcor {time.time()- start}")
        start = time.time()

        actor_scores: Dict[Movie, int] = defaultdict(lambda: 0)

        for movie, rating in zip(movies, ratings):
            actors = self.get_actors(movie)

            for actor in actors:
                for other_movie in self.get_movies_of_actor(actor):
                    if other_movie.id == movie.id:
                        continue

                    actor_scores[other_movie] += rating

        plot_scores: Dict[Movie, float] = defaultdict(lambda: 0)

        logger.info(f"actors {time.time()- start}")
        start = time.time()

        for movie, rating in zip(movies, ratings):
            for other_movie, distance in zip(
                *self.get_movies_with_similar_plots(movie)
            ):
                plot_scores[other_movie] += distance * rating

        logger.info(f"plots {time.time()- start}")

        return actor_scores, director_scores, plot_scores

    @staticmethod
    def get_actors(movie: Movie) -> List[Actor]:
        return (
            Actor.query.join(movie_actors, Actor.id == movie_actors.c.actor_id)
            .filter(movie_actors.c.movie_id == movie.id)
            .all()
        )

    @staticmethod
    def get_movies_of_actor(actor: Actor) -> List[Movie]:
        return (
            Movie.query.join(movie_actors, Movie.id == movie_actors.c.movie_id)
            .filter(movie_actors.c.actor_id == actor.id)
            .all()
        )

    @staticmethod
    def get_director(movie: Movie) -> List[Director]:
        return (
            Director.query.join(
                movie_directors, Director.id == movie_directors.c.director_id
            )
            .filter(movie_directors.c.movie_id == movie.id)
            .first()
        )

    @staticmethod
    def get_movies_of_director(director: Director) -> List[Movie]:
        return (
            Movie.query.join(movie_directors, Movie.id == movie_directors.c.movie_id)
            .filter(movie_directors.c.director_id == director.id)
            .all()
        )

    @staticmethod
    def get_movies_with_similar_plots(
        movie: Movie, n_results=10
    ) -> Tuple[List[Movie], List[float]]:
        manager = CHROMA_Manager.get_instance()
        movie_ids, distances = manager.query(movie.id, n_results)
        movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()
        return movies, distances
