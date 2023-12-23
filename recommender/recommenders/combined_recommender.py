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
        "user": 31.696782262221,
        "content": 15.069030305424,
        "user_weights": {
            "default_vec_val": 2.5,
            "closest_relevant_users": 4,
        },
        "content_weights": {
            "directors": 9.0533755974,
            "actors": 1.2301894300,
            "plots": 2.406376778502906,
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
