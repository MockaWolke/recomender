Dependencies

Redis at the moment
`redis-server`

Selery
`celery -A recommender.celery_queue.worker.celery_app worker --loglevel=info`

Server
`python recommender/api.py`
