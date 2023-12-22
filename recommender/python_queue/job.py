from recommender.querying.sql_models import Rating, Recommendation, User
from recommender.recommenders import CombinedRecommender
import time
from recommender import REPO_PATH
import sys
from loguru import logger
from flask_sqlalchemy import SQLAlchemy
from recommender.apps import create_app_slimm

logger.add(REPO_PATH / "backgroundjobs.log", rotation="3mb")


def generate_recommendations(db, user_id):
    try:
        user = db.session.query(User).get(user_id)
        if user is None:
            message = f"User with ID {user_id} not found."

            print(message, file=sys.stderr)
            logger.error(message)
            sys.exit(1)

        user.recommendations_ready = False
        db.session.commit()

        db.session.query(Recommendation).filter_by(user_id=user_id).delete()
        db.session.commit()

        ratings = db.session.query(Rating).filter_by(user_id=user_id).all()

        if not ratings:
            message = f"No ratings found for user ID {user_id}."
            print(message, file=sys.stderr)
            logger.error(message)
            sys.exit(1)

        movies, ratings = zip(*[(r.movie, r.value) for r in ratings])
        ratings = [(val - 3) ** 3 for val in ratings]

        recommender = CombinedRecommender(db)
        recommendations, scores = recommender.find_most_simmilar(movies, ratings)

        for movie, score in zip(recommendations, scores):
            new_recommendation = Recommendation(
                user_id=user_id, movie_id=movie.id, score=float(score), movie=movie
            )
            db.session.add(new_recommendation)

        user.recommendations_ready = True
        logger.success(f"Finished User {user_id}")
        db.session.commit()

    except Exception as e:
        message = f"Error generating recommendations: {e}"
        print(message, file=sys.stderr)
        logger.error(message)
        sys.exit(1)

    db.session.close()


if __name__ == "__main__":
    start_time = time.time()

    app, db = create_app_slimm()

    logger.debug(f"Starting Database took {time.time() - start_time}")

    generate_recommendations(db, sys.argv[1])
    sys.exit(0)
