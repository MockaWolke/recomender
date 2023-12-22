# apps.api
from recommender import REPO_PATH
from flask import Flask
from recommender.querying.sql_models import db, User
import os
import celery
from celery import Celery

os.chdir(REPO_PATH)


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


def create_app_slimm():
    app = Flask(__name__)

    app.config.from_object(__name__ + ".ConfigClass")  # configuration
    app.app_context().push()  # create an app context before initializing db
    db.init_app(app)  # initialize database
    db.create_all()  # create database if necessary

    return app, db


def create_app():
    app = Flask(__name__)

    app.config.from_object(__name__ + ".ConfigClass")  # configuration
    app.app_context().push()  # create an app context before initializing db
    db.init_app(app)  # initialize database
    db.create_all()  # create database if necessary
    user_manager = UserManager(app, db, User)  # initialize Flask-User management
    chroma_manager = CHROMA_Manager.get_instance()
    chroma_manager.cache_embeddings()

    return (
        app,
        chroma_manager,
        user_manager,
    )


def create_celery(app=None):
    celery = Celery(
        app.import_name,
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# app, chroma_manager, user_manager = create_app()
# celery_app = create_celery(app)
