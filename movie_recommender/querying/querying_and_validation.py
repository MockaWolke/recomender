from loguru import logger
from movie_recommender.querying.sql_models import Movie, MovieGenre, Rating
from movie_recommender import MIN_RATING_LEN
from typing import List, Set, Tuple, Dict, Union
from urllib.parse import unquote


def validate_ratings(db, args: dict) -> dict[int, int]:
    ratings = {}

    for movie_id, rat in args.items():
        movie_id = int(movie_id)

        if db.session.query(Movie.id).filter_by(id=movie_id).first() is None:
            logger.debug(f"ratings to short {movie_id}")
            raise TypeError()

        ratings[movie_id] = int(rat)

    return args


def check_if_vadlid_ratings(db, user_id: int) -> bool:
    return Rating.query.filter_by(user_id=user_id).count() >= MIN_RATING_LEN


def get_unique_genres(db) -> Dict[str, str]:
    """Retrieve all unique genres from the MovieGenre table."""
    unique_genres = db.session.query(MovieGenre.genre).distinct().all()

    genres = [genre[0] for genre in unique_genres if genre[0] != "(no genres listed)"]
    clean = {i.replace("-", "").lower(): i for i in sorted(genres)}

    return clean


def validate_selected_genres(
    args, unique_genres: Dict[str, str]
) -> Union[Set[str], None]:
    selected_genres = args.get("genres")

    if selected_genres is None:
        return None

    selected_genres = unquote(selected_genres)
    print("selected", selected_genres)

    selected_genres = selected_genres.split(",")

    valid = set()

    for val in selected_genres:
        if val not in unique_genres:
            logger.error(f"{val} not in unique genres {list(unique_genres.keys())}")
            raise ValueError()

        valid.add(unique_genres[val])

    logger.info(str(valid))

    return valid
