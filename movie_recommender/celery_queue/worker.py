from loguru import logger
from movie_recommender.querying.sql_models import Rating, Recommendation, User
from movie_recommender.recommenders.content_based_recommender import (
    ContentBasedRecommender,
)
from movie_recommender.recommenders.user_based_recommender import UserBasedRecommender
import time
from movie_recommender.apps import celery_app, db
from sqlalchemy.orm import scoped_session, sessionmaker
from movie_recommender import REPO_PATH


def specific_only(record):
    return "celery" in record["extra"]


logger.add(REPO_PATH / "celery.log", rotation="1mb", filter=specific_only)
celery_logger = logger.bind(specific=True)
celery_logger.info("Celery here")


@celery_app.task
def generate_recommendations(user_id):
    celery_logger.info(f"got something {user_id}")

    success = False

    try:
        session = scoped_session(sessionmaker(bind=db.engine))

        user = session.query(User).get(user_id)
        if user is None:
            celery_logger.error(f"User with ID {user_id} not found.")
            raise Exception()
        user.recommendations_ready = False
        session.commit()

        session.query(Recommendation).filter_by(user_id=user_id).delete()
        session.commit()

        ratings = session.query(Rating).filter_by(user_id=user_id).all()

        if not ratings:
            celery_logger.info(f"No ratings found for user ID {user_id}.")
            raise Exception()

        movies, ratings = zip(*[(r.movie, r.value) for r in ratings])
        ratings = [(val - 3) ** 3 for val in ratings]

        start = time.time()
        recommender = ContentBasedRecommender()
        recommendations, scores = recommender.find_most_simmilar(movies, ratings)

        celery_logger.info(f"Recommendation took {time.time() - start}")

        for movie, score in zip(recommendations, scores):
            movie = session.merge(movie)
            new_recommendation = Recommendation(
                user_id=user_id, movie_id=movie.id, score=float(score), movie=movie
            )
            session.add(new_recommendation)

        user.recommendations_ready = True
        session.commit()
        success = True

    except Exception as e:
        celery_logger.error(f"Error generating recommendations: {e}")
    finally:
        session.close()

    return success
