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


# <div class="ipc-poster ipc-poster--baseAlt ipc-poster--dynamic-width ipc-sub-grid-item ipc-sub-grid-item--span-2" role="group" data-testid="hero-media__poster"><div class="ipc-media ipc-media--poster-27x40 ipc-image-media-ratio--poster-27x40 ipc-media--baseAlt ipc-media--poster-l ipc-poster__poster-image ipc-media__img" style="width:100%"><img alt="Matthew McConaughey in Interstellar (2014)" class="ipc-image" loading="eager" src="https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_QL75_UX190_CR0,0,190,281_.jpg" srcset="https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_QL75_UX190_CR0,0,190,281_.jpg 190w, https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_QL75_UX285_CR0,0,285,422_.jpg 285w, https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_QL75_UX380_CR0,0,380,562_.jpg 380w" sizes="50vw, (min-width: 480px) 34vw, (min-width: 600px) 26vw, (min-width: 1024px) 16vw, (min-width: 1280px) 16vw" width="190"></div><div class="ipc-watchlist-ribbon ipc-focusable ipc-watchlist-ribbon--l ipc-watchlist-ribbon--baseAlt ipc-watchlist-ribbon--onImage ipc-poster__watchlist-ribbon hero-media__watchlist" aria-label="add to watchlist" role="button" tabindex="0"><svg class="ipc-watchlist-ribbon__bg" width="24px" height="34px" viewBox="0 0 24 34" xmlns="http://www.w3.org/2000/svg" role="presentation"><polygon class="ipc-watchlist-ribbon__bg-ribbon" fill="#000000" points="24 0 0 0 0 32 12.2436611 26.2926049 24 31.7728343"></polygon><polygon class="ipc-watchlist-ribbon__bg-hover" points="24 0 0 0 0 32 12.2436611 26.2926049 24 31.7728343"></polygon><polygon class="ipc-watchlist-ribbon__bg-shadow" points="24 31.7728343 24 33.7728343 12.2436611 28.2926049 0 34 0 32 12.2436611 26.2926049"></polygon></svg><div class="ipc-watchlist-ribbon__icon" role="presentation"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" class="ipc-icon ipc-icon--add ipc-icon--inline" viewBox="0 0 24 24" fill="currentColor" role="presentation"><path d="M18 13h-5v5c0 .55-.45 1-1 1s-1-.45-1-1v-5H6c-.55 0-1-.45-1-1s.45-1 1-1h5V6c0-.55.45-1 1-1s1 .45 1 1v5h5c.55 0 1 .45 1 1s-.45 1-1 1z"></path></svg></div></div><a class="ipc-lockup-overlay ipc-focusable" href="/title/tt0816692/mediaviewer/rm4043724800/?ref_=tt_ov_i" aria-label="View ’Interstellar’ Poster"><div class="ipc-lockup-overlay__screen"></div></a></div>


def fetch_imdb_image(imdb_id, timeout=4):
    try:
        # Fetch the main page content
        main_page_response = requests.get(
            f"https://www.imdb.com/title/tt{imdb_id}/",
            headers=headers,
            timeout=timeout,
        )
        main_page_response.raise_for_status()
        main_page_soup = BeautifulSoup(main_page_response.content, "html.parser")
        poster_box = main_page_soup.find("div", {"data-testid": "hero-media__poster"})

        if poster_box is None:
            raise ("did not find hero media")

        image_element = poster_box.find("img")

        if image_element is None:
            raise Exception("Image element not found in poster box")

        # Extract the source URL of the image
        image_url = image_element.get("src")

        if image_url is None:
            raise Exception("Image URL not found")

        image_response = requests.get(image_url, timeout=timeout)
        image_response.raise_for_status()

        return image_response.content

    except requests.RequestException as e:
        logger.info(
            f"Network error occurred: {e} for https://www.imdb.com/title/tt{imdb_id}/"
        )
    except AttributeError as e:
        logger.info(
            f"Failed to parse IMDb page - the page structure may have changed.\n{e} \n for https://www.imdb.com/title/tt{imdb_id}/"
        )


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


def img_wrapper(queue, args):
    result = fetch_imdb_image(args, timeout=5)
    queue.put(result)


def wrapper(queue, args):
    result = fetch_imdb_data(args)
    queue.put(result)


if __name__ == "__main__":
    # Example Usage
    imdb_info = fetch_imdb_data("0114709")
    print(imdb_info)
