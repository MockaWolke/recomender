from flask_sqlalchemy import SQLAlchemy
from flask_user import UserMixin

db = SQLAlchemy()


# Define the User data-model.
# NB: Make sure to add flask_user UserMixin as this adds additional fields and properties required by Flask-User
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column("is_active", db.Boolean(), nullable=False, server_default="1")

    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(
        db.String(100, collation="NOCASE"), nullable=False, unique=True
    )
    password = db.Column(db.String(255), nullable=False, server_default="")
    email_confirmed_at = db.Column(db.DateTime())

    # User information
    first_name = db.Column(
        db.String(100, collation="NOCASE"), nullable=False, server_default=""
    )
    last_name = db.Column(
        db.String(100, collation="NOCASE"), nullable=False, server_default=""
    )
    # tags = db.relationship("Tags", backref="user", lazy=True, uselist=True)


class Movie(db.Model):
    __tablename__ = "movies"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False, unique=True)
    imdb_data_id = db.Column(db.Integer, db.ForeignKey("imdb_data.id"))
    year = db.Column(db.Integer, nullable=True)
    imdb_id = db.Column(db.String(255))
    tmdb_id = db.Column(db.String(255), nullable=True)
    imdbId_link = db.Column(db.String(255))

    genres = db.relationship("MovieGenre", backref="movie", lazy="dynamic")
    tags = db.relationship("Tag", backref="movie", lazy="dynamic")

    actors = db.relationship(
        "Actor", secondary="movie_actors", backref=db.backref("movies", lazy="dynamic")
    )
    directors = db.relationship(
        "Director",
        secondary="movie_directors",
        backref=db.backref("movies", lazy="dynamic"),
    )
    imdb_data = db.relationship(
        "IMDbData",
        back_populates="movie",
        uselist=False,
    )


class IMDbData(db.Model):
    __tablename__ = "imdb_data"
    id = db.Column(db.Integer, primary_key=True)
    movie = db.relationship("Movie", back_populates="imdb_data", uselist=False)
    rating = db.Column(db.Float)
    summary = db.Column(db.Text)


class MovieGenre(db.Model):
    __tablename__ = "movie_genres"
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"))
    genre = db.Column(db.String(255), nullable=False)


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"))
    tag = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)


class Actor(db.Model):
    __tablename__ = "actors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)


class Director(db.Model):
    __tablename__ = "directors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)


movie_actors = db.Table(
    "movie_actors",
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id"), primary_key=True),
    db.Column("actor_id", db.Integer, db.ForeignKey("actors.id"), primary_key=True),
)

movie_directors = db.Table(
    "movie_directors",
    db.Column("movie_id", db.Integer, db.ForeignKey("movies.id"), primary_key=True),
    db.Column(
        "director_id", db.Integer, db.ForeignKey("directors.id"), primary_key=True
    ),
)
