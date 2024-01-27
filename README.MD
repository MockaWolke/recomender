# Movie Recommender

## INSTALLATION

To install the required packages, run:

```bash
pip install -r requirements.txt
```

## USAGE

Initialize the database:
`flask initdb`

Fill the Chroma index with movie data:
`flask fillchroma`

Start the Flask development server:
`flask run`

Open your web browser and go to http://localhost:5000.

Register a new user or login with an existing account.

Rate the example movies displayed on the homepage by selecting a rating from 1 to 5.

Save your ratings. The background recommender will process your ratings and generate recommendations.

Visit the recommendations page to see personalized movie recommendations based on your ratings.

## FEATURES

### Hybrid Recommendation System

The application uses both collaborative filtering and content-based recommendation algorithms to provide personalized movie recommendations to users. The recommender takes into account user ratings and movie content similarity to generate relevant and personalized recommendations.

Collaborative filtering is used to find users who have similar tastes and preferences as the current user. The algorithm identifies users who have rated movies similarly to the current user and recommends movies that those similar users have rated highly.

Content-based filtering is used to recommend movies based on their genres, actors, directors, and plot summaries. This information was crawled from imdb and saved in the database. The recommender identifies movies that have similar attributes or content to the movies that the user has rated highly and recommends those movies.

The optimized the influence of genres, authors, plot descriptions and similar users, such that the recommender system follows our taste. You can see more [here.](notebooks/optimize_weights.ipynb)

### Genre Filter

Users can filter recommendations based on specific movie genres. They can select preferred genres to refine the recommendations and discover movies of their interest.

### Caching

The application utilizes a cache to store and retrieve recommendations, reducing processing time for subsequent requests.

### Chroma

We implemented Chroma index as an embedding of movie plots enhancing the content-based recommendation process.

### Asynchronous Tasks

To compute the movie recommendations we implenented a Task Queue. We first used Celery & Redis, but for ease of deployment we simply wrote us our own background queue as a seperate python api. (movie_recommender/background_api)

### Testing

- For easier development and deployment, we wrote several Pytest tests, which can be run with:

`pytest -W ignore`

### Debugging

Both the main and background api generate logfiles.
