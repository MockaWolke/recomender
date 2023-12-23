# api.app
from movie_recommender import (
    REPO_PATH,
    MIN_SCORE,
    MAX_RECOMENDATIOSN,
    Back_Ground_Timeout,
    RECOMMENDATIONS_CACHE_TIME,
    RECOMMENDATIONS_CACHED_N_USERS,
)
from flask import render_template, request, jsonify
from flask_user import login_required
from flask_login import current_user
from collections import namedtuple
from movie_recommender.querying.sql_models import (
    Movie,
    Rating,
    User,
    Recommendation,
)
from movie_recommender.init_data.fill_db import check_and_read_data
from loguru import logger
from movie_recommender.querying.querying_and_validation import (
    validate_ratings,
    get_unique_genres,
    check_if_vadlid_ratings,
    validate_selected_genres,
)

from movie_recommender.apps import create_app_slimm
from movie_recommender.querying import CHROMA_Manager
from loguru import logger
from movie_recommender.python_queue import BackgroundTaskQueue
from flask_user import UserManager
from cachetools import TTLCache
from dataclasses import dataclass
import json
import os
import time
import datetime

logger.add(REPO_PATH / "api.log", rotation="5mb")

app, db = create_app_slimm()

# get example movies
with open(REPO_PATH / "rating_movies.json") as f:
    rating_movies = json.load(f)


EXAMPLE_MOVIES = Movie.query.filter(Movie.title.in_(rating_movies)).all()

logger.info(f"We have so many {len(EXAMPLE_MOVIES)} rating movies")

UNIQUE_GENRES = get_unique_genres(db)
UNIQUE_GENRES_SET = set(UNIQUE_GENRES.values())

user_manager = UserManager(app, db, User)  # initialize Flask-User management
chroma_manager = CHROMA_Manager.get_instance()
BackgroundTaskQueue.get_instance(timeout=Back_Ground_Timeout)
assert BackgroundTaskQueue.get_instance().timeout == Back_Ground_Timeout

logger.info(f"Starting API at {datetime.datetime.now()}")


recommendations_cache = TTLCache(
    RECOMMENDATIONS_CACHED_N_USERS, RECOMMENDATIONS_CACHE_TIME
)

logger.info(f"Cache started {datetime.datetime.now()}")


@dataclass
class MovieInfo:
    title: str
    genres: list[str]
    tags: list[str]
    imdb_link: str
    id: int
    imdbid: str
    score: float = 0
    rounded_score: str = ""
    image_path: str = ""

    def __post_init__(self):
        path = f"images/{self.imdbid}.jpg"

        if os.path.exists(REPO_PATH / "movie_recommender/static/" / path):
            self.image_path = path


@app.cli.command("initdb")
def initdb_command():
    global db
    """Creates the database tables."""
    check_and_read_data(db)
    logger.success("Initialized the database.")


@app.cli.command("fillchroma")
def initdb_command():
    chroma_manager.fill()
    logger.success("Initialized the chroma.")


@app.cli.command("chromafull")
def initdb_command():
    full = chroma_manager.isfull

    if isinstance(full, set):
        logger.info(f"Chroma missing these ids: {full}")
    else:
        logger.success("Chroma is full")


# The Home page is accessible to anyone
@app.route("/")
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route("/movies")
@login_required  # User must be authenticated
def rating_page():
    movies = [
        MovieInfo(
            title=movie.title,
            genres=[i.genre for i in movie.genres],
            tags=[i.tag for i in movie.tags],
            imdb_link=movie.imdbId_link,
            id=movie.id,
            imdbid=movie.imdb_id,
        )
        for movie in EXAMPLE_MOVIES
    ]

    return render_template("movies.html", movies=movies, max_tags=5)


@app.post("/save_ratings")
@login_required  # User must be authenticated
def save_ratings():
    data = request.json  # Get JSON data from the request
    ratings_values = data.get("ratings")

    if not ratings_values:
        return jsonify({"error": "No ratings provided"}), 400

    try:
        ratings = validate_ratings(db, ratings_values)
    except TypeError:
        return jsonify({"error": "False ratings provided"}), 400

    Rating.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()  # Commit the deletion

    for movie_id, value in ratings.items():
        # Create a new Rating object
        new_rating = Rating(
            user_id=current_user.id,
            movie_id=movie_id,  # Ensure this corresponds with your movies
            value=float(value),
        )
        db.session.add(new_rating)
    user = db.session.query(User).get(current_user.id)
    user.recommendations_ready = False
    db.session.commit()

    background_task_queue = BackgroundTaskQueue.get_instance()
    print("timeout", background_task_queue.timeout)

    job_id = background_task_queue.add_task(user_id=current_user.id)

    # clear chache
    recommendations_cache.pop(current_user.id, None)

    logger.info(f"Queue started at {job_id}")

    return jsonify(
        {"message": "Ratings saved successfully", "recommendation_job_id": job_id}
    )


@app.get("/recommendation_status")
def task_result() -> dict[str, object]:
    job_id = request.cookies.get("recommendation_job_id")

    status = BackgroundTaskQueue.get_instance().task_status.get(job_id)

    if status is None:
        return jsonify({"ok": False, "error": "Job not found"})

    if status == "error":
        return jsonify(
            {"ok": False, "error": "Oh now, we have had an error in the background ):"}
        )

    return jsonify({"ready": status == "success", "ok": True})


@app.route("/recommendations")
@login_required  # Use
def recommend_page():
    if not check_if_vadlid_ratings(db, current_user.id):
        return render_template("missing_recommendations.html")

    try:
        selected_genres = validate_selected_genres(request.args, UNIQUE_GENRES)

    except:
        logger.exception("s")
        return "False Args"
    logger.info(f"Selected genres {selected_genres}")

    user = db.session.query(User).get(current_user.id)

    if user.recommendations_ready == False:
        return render_template("recommendations_loading.html")

    if current_user.id in recommendations_cache:
        logger.debug("Loading from Cache")
        cached_recommendations: list[MovieInfo] = recommendations_cache[current_user.id]
        logger.debug("Loaded")

    else:
        recommendations = Recommendation.query.filter(
            Recommendation.user_id == current_user.id
        ).all()

        cached_recommendations: list[MovieInfo] = []

        for recommendation in recommendations:
            score = recommendation.score

            if score < MIN_SCORE:  # keeps cache small
                continue

            movie = recommendation.movie
            reco = MovieInfo(
                title=movie.title,
                score=score,
                rounded_score=f"{score*0.01:.2f}",
                genres=[i.genre for i in movie.genres],
                tags=[i.tag for i in movie.tags],
                imdb_link=movie.imdbId_link,
                id=movie.id,
                imdbid=movie.imdb_id,
            )

            cached_recommendations.append(reco)

        # add to chache
        recommendations_cache[current_user.id] = cached_recommendations

    response_data = []

    for reco in cached_recommendations:
        if selected_genres is None or selected_genres.issubset(reco.genres):
            response_data.append(reco)

    response_data = response_data[:MAX_RECOMENDATIOSN]

    return render_template(
        f"recommendations.html",
        response_data=response_data,
        max_tags=5,
        unique_genres=UNIQUE_GENRES,
        selected_genres=selected_genres
        if selected_genres is not None
        else UNIQUE_GENRES_SET,
        selected_all=request.args.get("genres") is None,
    )


# Start development web server
if __name__ == "__main__":
    app.run(port=5000, debug=True)
