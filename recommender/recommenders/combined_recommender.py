from .content_based_recommender import ContentBasedRecommender
from .user_based_recommender import UserBasedRecommender
from recommender.utils import normalize_score, l2
from typing import List, Set, Dict, Tuple
from recommender.querying.sql_models import Movie
from collections import defaultdict
from loguru import logger
import time


class CombinedRecommender:
    weights = {
        "user": 1.2,
        "content": 4,
        "user_weights": {
            "default_vec_val": 3,
            "closest_relevant_users": 5,
        },
        "content_weights": {
            "directors": 1,
            "actors": 0.2,
            "plots": 1.2,
        },
    }

    def __init__(self, db, distance_metric=l2) -> None:
        UserBasedRecommender.weights = self.weights["user_weights"]
        ContentBasedRecommender.weights = self.weights["content_weights"]

        self.user_based_recommender = UserBasedRecommender(
            db, distance_metric=distance_metric
        )
        self.content_based_recommender = ContentBasedRecommender()

    def find_most_simmilar(
        self, movies: List[Movie], ratings: List[float]
    ) -> Tuple[List[Movie], List[float]]:
        start = time.time()
        user_based = self.user_based_recommender.find_most_simmilar(movies, ratings)
        logger.debug(f"User Based Recommendation took {time.time() - start}")

        start = time.time()
        content_based = self.content_based_recommender.find_most_simmilar(
            movies, ratings
        )
        logger.debug(f"Content Based Recommendation took {time.time() - start}")

        recommendations = defaultdict(lambda: 0)

        for movie, score in zip(*user_based):
            recommendations[movie] += score * self.weights["user"]

        for movie, score in zip(*content_based):
            recommendations[movie] += score * self.weights["content"]

        sorted_recommendations = sorted(
            filter(
                lambda x: recommendations.get(x) > 0,
                recommendations,
            ),
            key=lambda x: recommendations.get(x),
            reverse=True,
        )

        scores = [recommendations[i] for i in sorted_recommendations]
        return sorted_recommendations, scores
