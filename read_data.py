import pandas as pd
from sqlalchemy.exc import IntegrityError
from models import Movie, MovieGenre, Links, Tags
import tqdm
from loguru import logger
import numpy as np


def parse_movies_links_and_genres(db):
    movies = pd.read_csv("data/movies.csv")
    links = pd.read_csv(
        "data/links.csv",
        dtype={
            "movieId": "int64",
            "imdbId": "string",
            "tmdbId": "string",
        },
    )

    links.tmdbId = links.tmdbId.fillna("")

    complete = movies.merge(links, how="inner", on="movieId")

    assert np.all(complete.isna().any() == False)

    for index in tqdm.tqdm(range(len(complete)), desc="Parsing Movies"):
        try:
            row = complete.iloc[index]
            id = int(row["movieId"])  # Assuming the first column is 'id'
            title = row["title"]  # Assuming the second column is 'title'
            movie = Movie(id=id, title=title)
            db.session.add(movie)

            genres = row["genres"].split("|")  # Assuming the third column is 'genres'
            for genre in genres:
                movie_genre = MovieGenre(movie_id=id, genre=genre)
                db.session.add(movie_genre)

            links = Links(
                movie_id=id,
                imdbId=row.imdbId if row.imdbId else "",
                tmdbId=row.tmdbId if row.tmdbId else "",
                imdbId_link=f"https://www.imdb.com/title/tt{row.imdbId}/"
                if row.imdbId
                else "",
            )
            db.session.add(links)

            db.session.commit()
        except IntegrityError:
            logger.info("Ignoring duplicate movie:", title)

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except:
            logger.exception("Error")


def parse_tags(db):
    complete = pd.read_csv("data/tags.csv")

    assert np.all(complete.isna().any() == False)

    for index in tqdm.tqdm(range(len(complete)), desc="Parsing Tags"):
        try:
            row = complete.iloc[index]
            movieId = int(row["movieId"])  # Assuming the first column is 'id'
            userId = int(row["userId"])  # Assuming the first column is 'id'
            tag = row["tag"]

            tagg = Tags(movie_id=movieId, user_id=userId, tag=tag)
            db.session.add(tagg)

            db.session.commit()
        except IntegrityError:
            logger.info("Ignoring duplicate movie:", tag)

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except:
            logger.exception("Error")


def check_and_read_data(db):
    # Read movies from CSV file using pandas

    db.session.query(MovieGenre).delete()
    db.session.query(Movie).delete()
    db.session.query(Links).delete()
    db.session.query(Tags).delete()
    db.session.commit()

    parse_movies_links_and_genres(db)
    logger.success("Movies Done")
    parse_tags(db)
    logger.success("Tags Done")
