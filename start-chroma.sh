export $(grep -v '^#' .env | xargs)
chroma run --path chroma/ --port $CHROMA_PORT