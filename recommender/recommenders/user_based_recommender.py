from recommender.querying.sql_models import Movie, Rating, OldUser
import numpy as np
from collections import defaultdict
from recommender.utils import normalize_score, l2
from typing import List, Set, Tuple, Dict


class UserBasedRecommender:
    weights = {
        "default_vec_val": 3,
        "closest_relevant_users": 5,
    }

    def __init__(self, db, distance_metric: callable = l2) -> None:
        self.db = db
        self.distance_metric = distance_metric

    @staticmethod
    def get_overlapping_users(movies: Movie) -> set[int]:
        user_ids = set()

        for movie in movies:
            if movie is None:
                continue

            different_ratings = movie.ratings
            for rating in different_ratings:
                if rating.old_user_id is not None:
                    user_ids.add(rating.old_user_id)

        return user_ids

    def get_embedding(self, user_id, sorted_movies_keys: dict[str]):
        # get user
        user = self.db.session.get(OldUser, user_id)
        rated_movies = {
            i.id: i.value
            for i in user.ratings
            if i is not None and i in sorted_movies_keys
        }
        return np.array(
            [
                normalize_score(rated_movies.get(i.id, self.weights["default_vec_val"]))
                for i in sorted_movies_keys
            ]
        )

    def find_most_simmilar(
        self, movies: List[Movie], ratings: List[float]
    ) -> Tuple[List[Movie], List[float]]:
        user_ratings = dict(zip(movies, ratings))

        sorted_movie_keys = dict.fromkeys(
            sorted(user_ratings.keys(), key=lambda x: x.id)
        )

        recommendations = self.get_recommendations(
            movies, user_ratings, sorted_movie_keys
        )

        sorted_recommendations = sorted(
            filter(
                lambda x: recommendations.get(x) > 0 and x not in user_ratings,
                recommendations,
            ),
            key=lambda x: recommendations.get(x),
            reverse=True,
        )

        recommended_movies = sorted_recommendations
        scores = [recommendations[i] for i in sorted_recommendations]

        return recommended_movies, scores

    def get_recommendations(self, movies, user_ratings, sorted_movie_keys):
        user_array = np.array(
            [normalize_score(user_ratings[key]) for key in sorted_movie_keys]
        )

        overlapping_users = self.get_overlapping_users(movies)

        user_ids, vectors = [], []

        for user_id in overlapping_users:
            user_ids.append(user_id)

            embedding = self.get_embedding(user_id, sorted_movie_keys)
            vectors.append(embedding)

        user_ids, vectors = np.array(user_ids), np.array(vectors)

        distances = np.array([self.distance_metric(vec, user_array) for vec in vectors])

        best = np.argsort(distances)

        recommendations = defaultdict(lambda: 0)

        relevant_users = user_ids[best[: self.weights["closest_relevant_users"]]]

        for user_id in relevant_users:
            user = self.db.session.get(OldUser, int(user_id))

            if user is None:
                continue

            for rating in user.ratings:
                if rating.movie is None:
                    continue
                recommendations[rating.movie] += normalize_score(rating.value)
        return recommendations
