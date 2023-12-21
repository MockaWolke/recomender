# api.app
from recommender import REPO_PATH, MIN_SCORE, MAX_RECOMENDATIOSN
from loguru import logger

from flask import render_template, request, jsonify
from flask_user import login_required
from flask_login import current_user
from recommender.querying.sql_models import (
    Movie,
    Rating,
    User,
    Recommendation,
    recommendations_movie,
)
from recommender.init_data.fill_db import check_and_read_data
from loguru import logger
from recommender.querying.querying_and_validation import (
    validate_ratings,
    get_unique_genres,
    check_if_vadlid_ratings,
    validate_selected_genres,
)

from recommender.apps import app, chroma_manager, db
from recommender.celery_queue.worker import generate_recommendations

EXAMPLE_MOVIES = Movie.query.limit(5).all()
UNIQUE_GENRES = get_unique_genres(db)
UNIQUE_GENRES_SET = set(UNIQUE_GENRES.values())


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
    return render_template("movies.html", movies=EXAMPLE_MOVIES, max_tags=5)


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

    job_id = generate_recommendations.delay(current_user.id).id
    logger.info(f"Queue started at {job_id}")

    return jsonify(
        {"message": "Ratings saved successfully", "recommendation_job_id": job_id}
    )


@app.get("/recommendation_status")
def task_result() -> dict[str, object]:
    user = db.session.query(User).get(current_user.id)
    if user is None:
        return jsonify({"ok": False, "error": "User not found"}), 404

    return jsonify({"ready": user.recommendations_ready, "ok": True})


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

    recommendations = Recommendation.query.filter(
        Recommendation.user_id == current_user.id
    ).all()

    def in_selected_movies(movie: Movie):
        if selected_genres is None:
            return True

        genres = set(i.genre for i in movie.genres.all())
        return selected_genres.issubset(genres)

    movies_and_scores = []

    for recommendation in recommendations:
        movie = recommendation.movie
        score = recommendation.score

        if score > MIN_SCORE and in_selected_movies(movie):
            movies_and_scores.append((movie, f"{score:.2f}"))

    movies_and_scores = movies_and_scores[:MAX_RECOMENDATIOSN]

    return render_template(
        f"recommendations.html",
        movies_and_scores=movies_and_scores,
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
