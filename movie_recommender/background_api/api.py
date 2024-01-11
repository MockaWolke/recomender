from fastapi import FastAPI, status
from loguru import logger
import time
from movie_recommender import REPO_PATH
import os
from pydantic import BaseModel
from movie_recommender.querying.sql_models import Rating, Recommendation, User
from movie_recommender.recommenders import CombinedRecommender
import datetime
from movie_recommender import REPO_PATH
from loguru import logger
from movie_recommender.apps import create_app_slimm

os.chdir(REPO_PATH)

background_api = FastAPI()

logger.add(REPO_PATH / "backgroundjobs.log", rotation="3mb", level="DEBUG")

logger.info(f"Starting Background Api at {datetime.datetime.now()}")
logger.add("some debug bessame")

app, db = create_app_slimm()
logger.add("another")


def generate_recommendations(db, user_id):
    logger.debug(f"Received Job for user {user_id}")

    try:
        user = db.session.query(User).get(user_id)
        if user is None:
            message = f"User with ID {user_id} not found."

            logger.error(message)

        user.recommendations_ready = False
        db.session.commit()

        db.session.query(Recommendation).filter_by(user_id=user_id).delete()
        db.session.commit()

        ratings = db.session.query(Rating).filter_by(user_id=user_id).all()

        if not ratings:
            message = f"No ratings found for user ID {user_id}."
            logger.error(message)

        movies, ratings = zip(*[(r.movie, r.value) for r in ratings])
        ratings = [(val - 3) ** 3 for val in ratings]

        logger.debug("Start recommender")

        recommender = CombinedRecommender(db)
        recommendations, scores = recommender.find_most_simmilar(movies, ratings)

        logger.debug("Start computed recommendations")

        for movie, score in zip(recommendations, scores):
            new_recommendation = Recommendation(
                user_id=user_id, movie_id=movie.id, score=float(score), movie=movie
            )
            db.session.add(new_recommendation)

        user.recommendations_ready = True
        logger.success(f"Finished User {user_id}")
        db.session.commit()
        db.session.close()
        return True
    except Exception as e:
        message = f"Error generating recommendations: {e}"
        logger.error(message)
        logger.exception(message)
        db.session.close()

    return False


class HealthCheck(BaseModel):
    """Response model to validate and return when performing a health check."""

    status: str = "OK"


@background_api.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    """
    ## Perform a Health Check
    Endpoint to perform a healthcheck on. This endpoint can primarily be used Docker
    to ensure a robust container orchestration and management is in place. Other
    services which rely on proper functioning of the API service will not deploy if this
    endpoint returns any other HTTP status code except 200 (OK).
    Returns:
        HealthCheck: Returns a JSON response with the health status
    """
    logger.debug("received health request")

    return HealthCheck(status="OK")


@background_api.post("/calculate_recommendations/")
def api_fix_spelling(user_id: int) -> bool:
    logger.debug(f"received job for user {user_id}")

    return generate_recommendations(db, user_id)
