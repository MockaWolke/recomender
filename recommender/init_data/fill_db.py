import os
import pandas as pd
from sqlalchemy.exc import IntegrityError
from recommender.querying.sql_models import (
    Movie,
    MovieGenre,
    Tag,
    IMDbData,
    Actor,
    Director,
    Rating,
    OldUser,
    Recommendation,
)
import tqdm
from loguru import logger
import numpy as np
from sqlalchemy.exc import IntegrityError
import re
import sqlalchemy
import shutil
from recommender import REPO_PATH


def parse_movies_links_and_genres(db):
    movies = pd.read_csv(REPO_PATH / "data/movies.csv")

    def get_year(string):
        res = re.findall(r"\d+", string)
        if res:
            return res[0]

        return np.NaN

    movies["year"] = movies.title.apply(get_year)
    movies.title = movies.title.str.replace(r" \(\d+\)", "", regex=True)

    links = pd.read_csv(
        REPO_PATH / "data/links.csv",
        dtype={
            "movieId": "int64",
            "imdbId": "string",
            "tmdbId": "string",
        },
    )

    links.tmdbId = links.tmdbId.fillna("")

    imdb_data = pd.read_csv(
        REPO_PATH / "data/imdb_data.csv",
    ).drop(columns=["imdbId", "tmdbId"])
    complete = movies.merge(links, how="inner", on="movieId").merge(
        imdb_data, how="inner", on="movieId"
    )

    for index in tqdm.tqdm(range(len(complete)), desc="Parsing Movies"):
        try:
            row = complete.iloc[index]

            movie_id = int(row["movieId"])

            movie = Movie(
                id=movie_id,
                title=row.title,
                imdb_id=row.imdbId,
                tmdb_id=row.tmdbId if not pd.isna(row.tmdbId) else sqlalchemy.null(),
                imdbId_link=f"https://www.imdb.com/title/tt{row.imdbId}/",
                year=int(row.year) if not pd.isna(row.year) else sqlalchemy.null(),
            )

            db.session.add(movie)

            genres = row["genres"].split("|")
            for genre in genres:
                movie_genre = MovieGenre(movie_id=movie_id, genre=genre)
                db.session.add(movie_genre)

            if not pd.isna(row.rating) and not pd.isna(row.plot_summary):
                new_imdb_data = IMDbData(
                    movie=movie,
                    rating=row.rating,
                    summary=row.plot_summary,
                )

                # Add IMDb data to the session and commit
                db.session.add(new_imdb_data)

            if not pd.isna(row.director):
                # Assuming you have a function to get or create a director
                director = get_or_create_director(row.director, db)
                movie.directors.append(director)
            else:
                logger.info(f"Director is missing for {row.title}")
            # Associate top cast with the movie
            if not pd.isna(row.top_cast):
                for actor_name in row.top_cast.split(" | "):
                    actor = get_or_create_actor(actor_name, db)
                    movie.actors.append(actor)

            db.session.commit()
        except IntegrityError as e:
            logger.info(f"Ignoring duplicate movie: {row.title} - {e}")

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except KeyboardInterrupt:
            raise

        except:
            logger.exception("Error")


def parse_tags(db):
    complete = pd.read_csv(REPO_PATH / "data/tags.csv")

    assert np.all(complete.isna().any() == False)

    for index in tqdm.tqdm(range(len(complete)), desc="Parsing Tags"):
        try:
            row = complete.iloc[index]
            movieId = int(row["movieId"])  # Assuming the first column is 'id'
            userId = int(row["userId"])  # Assuming the first column is 'id'
            tag = row["tag"]

            tagg = Tag(movie_id=movieId, user_id=userId, tag=tag)
            db.session.add(tagg)

            db.session.commit()
        except IntegrityError:
            logger.info("Ignoring tag:", tag)

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except:
            logger.exception("Error")


def parse_ratings(db):
    complete = pd.read_csv(REPO_PATH / "data/ratings.csv")

    assert np.all(complete.isna().any() == False)

    for user in tqdm.tqdm(complete.userId.unique(), desc="Creating Users"):
        try:
            old_user = OldUser(id=int(user))

            db.session.add(old_user)
            db.session.commit()

        except IntegrityError as e:
            logger.info(f"Integrity Error {e}")

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except:
            logger.exception("Error")

    for index in tqdm.tqdm(range(len(complete)), desc="Parsing Ratings"):
        try:
            row = complete.iloc[index]
            movieId = int(row["movieId"])  # Assuming the first column is 'id'
            userId = int(row["userId"])  # Assuming the first column is 'id'
            value = row["rating"]

            rating = Rating(movie_id=movieId, old_user_id=userId, value=value)

            db.session.add(rating)

            db.session.commit()
        except IntegrityError as e:
            logger.info(f"Integrity Error {e}")

            db.session.rollback()
        except KeyError:
            logger.info("Error in CSV format")

        except:
            logger.exception("Error")


def check_and_read_data(db):
    # Read movies from CSV file using pandas

    db.session.query(MovieGenre).delete()
    db.session.query(Movie).delete()
    db.session.query(Tag).delete()
    db.session.query(IMDbData).delete()
    db.session.query(Director).delete()
    db.session.query(Actor).delete()
    db.session.query(OldUser).delete()
    db.session.query(Recommendation).delete()
    db.session.query(Rating).delete()
    db.session.commit()

    # shutil.rmtree(REPO_PATH / "instance")
    # os.makedirs(REPO_PATH / "instance")

    parse_movies_links_and_genres(db)
    logger.success("Movies Done")

    parse_tags(db)
    logger.success("Tags Done")

    parse_ratings(db)
    logger.success("Ratings Done")


def get_or_create_director(name, db):
    director = db.session.query(Director).filter_by(name=name).first()
    if not director:
        director = Director(name=name)
        db.session.add(director)
        db.session.commit()
    return director


def get_or_create_actor(name, db):
    actor = db.session.query(Actor).filter_by(name=name).first()
    if not actor:
        actor = Actor(name=name)
        db.session.add(actor)
        db.session.commit()
    return actor
