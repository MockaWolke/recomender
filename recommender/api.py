from flask import Flask, render_template
from flask_user import login_required, UserManager

from recommender.sql_models import db, User, Movie
from recommender.fill_db import check_and_read_data
from dotenv import load_dotenv
from loguru import logger
from recommender import REPO_PATH
from recommender.chroma import CHROMA_Manager
import os

os.chdir(REPO_PATH)


# Class-based application configuration
class ConfigClass(object):
    """Flask application config"""

    # Flask settings
    SECRET_KEY = "This is an INSECURE secret!! DO NOT use this in production!!"

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{REPO_PATH}/movie_recommender.sqlite"  # File-based SQL database
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Movie Recommender"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = True  # Simplify register form


# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + ".ConfigClass")  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management
chroma_manager = CHROMA_Manager.get_instance()


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
def movies_page():
    # String-based templates

    # first 10 movies
    movies = Movie.query.limit(10).all()

    # only Romance movies
    # movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == 'Romance')).limit(10).all()

    # only Romance AND Horror movies
    # movies = Movie.query\
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Romance')) \
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Horror')) \
    #     .limit(10).all()

    return render_template("movies.html", movies=movies, max_tags=5)


# Start development web server
if __name__ == "__main__":
    app.run(port=5000, debug=True)
