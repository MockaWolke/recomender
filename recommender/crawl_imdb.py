from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import Optional

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}


class IMDbDataPydantic(BaseModel):
    rating: float
    director: Optional[str] = None
    top_cast: list[str]
    plot_summary: str


def get_director(soup):
    for s in soup.find_all(class_="ipc-metadata-list__item"):
        if "Director" not in s.text:
            continue

        return s.find(
            "a", class_="ipc-metadata-list-item__list-content-item--link"
        ).text


def fetch_imdb_data(imdb_id, timeout=4):
    try:
        # Fetch the main page content
        main_page_response = requests.get(
            f"https://www.imdb.com/title/tt{imdb_id}/",
            headers=headers,
            timeout=timeout,
        )
        main_page_response.raise_for_status()
        main_page_soup = BeautifulSoup(main_page_response.content, "html.parser")

        # Extract the rating
        rating = main_page_soup.find("span", class_="sc-bde20123-1 cMEQkK")

        if rating is None:
            raise AttributeError("rating wrong")

        rating = rating.text

        try:
            # Extract the director's name
            director = get_director(main_page_soup)
            if director is None:
                logger.info(
                    f"Could not find director for https://www.imdb.com/title/tt{imdb_id}/plotsummary/"
                )

        except:
            raise AttributeError("director wrong")

        try:
            cast_list = main_page_soup.find_all(
                "div", {"data-testid": "title-cast-item"}
            )
            # Extract top cast names
            top_cast = [
                cast.find("a", {"data-testid": "title-cast-item__actor"}).text
                for cast in cast_list
            ]

        except:
            raise AttributeError("cast list wrong")

        summary_response = requests.get(
            f"https://www.imdb.com/title/tt{imdb_id}/plotsummary/",
            headers=headers,
            timeout=timeout,
        )
        summary_response.raise_for_status()

        try:
            # Fetch the plot summary
            summary_soup = BeautifulSoup(summary_response.content, "html.parser")
            plot_summary = summary_soup.find("div", class_="sc-f65f65be-0 bBlII").text

        except:
            raise ValueError("summaries wrong")

        return IMDbDataPydantic(
            rating=rating,
            director=director,
            top_cast=top_cast,
            plot_summary=plot_summary,
        )

    except requests.RequestException as e:
        logger.info(
            f"Network error occurred: {e} for https://www.imdb.com/title/tt{imdb_id}/"
        )
    except AttributeError as e:
        logger.info(
            f"Failed to parse IMDb page - the page structure may have changed.\n{e} \n for https://www.imdb.com/title/tt{imdb_id}/"
        )


def wrapper(queue, args):
    result = fetch_imdb_data(args)
    queue.put(result)


if __name__ == "__main__":
    # Example Usage
    imdb_info = fetch_imdb_data("0114709")
    print(imdb_info)
