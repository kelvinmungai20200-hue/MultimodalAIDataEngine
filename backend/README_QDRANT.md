Local Qdrant (docker-compose) quickstart

This project includes a docker-compose configuration to run a local Qdrant instance for development and testing of the vector DB integration.

Files created/updated:
- docker-compose.yml (project root)

Quickstart

1. Start Qdrant

   From the project root:

       docker-compose up -d qdrant

   This will start Qdrant and expose the HTTP API on http://localhost:6333.

2. Configure the backend to talk to Qdrant

   Set the environment variables for your backend process (example for Linux/macOS):

       export QDRANT_URL=http://localhost:6333
       export QDRANT_COLLECTION=multimodal_embeddings

   On Windows (PowerShell):

       $env:QDRANT_URL = "http://localhost:6333"
       $env:QDRANT_COLLECTION = "multimodal_embeddings"

3. (Optional) Create a collection with an appropriate vector size

   Qdrant collections require a vector size. Choose a size that matches your embedding model (e.g., 384 for all-MiniLM-L6-v2, 1536 for some OpenAI models).

   Example (create collection with vector size 384 and cosine distance):

       curl -s -X PUT "http://localhost:6333/collections/multimodal_embeddings" \
         -H "Content-Type: application/json" \
         -d '{"vectors": {"size": 384, "distance": "Cosine"}}'

   If you don't create the collection manually, qdrant-client may create it with defaults depending on the client version; explicit creation is recommended to control vector size and distance.

4. Run the worker or call the embedding function

   With QDRANT_URL set, the embedding worker will attempt to upsert vectors to Qdrant when embeddings are generated. You can test manually by calling the process_asset_embedding(...) function or by running the provided worker script.

Troubleshooting

- Data directory: The compose file mounts ./data/qdrant for persistence. Ensure the project user has write permissions to that path.
- Ports: If 6333 is already in use, adjust docker-compose.yml and QDRANT_URL accordingly.
- Version: The compose uses qdrant/qdrant:latest. For reproducible development, pin to a specific tag.

Tuning retry/backoff for vector DB operations

Two environment variables control retry behavior for vector DB operations (upsert and existence checks):

- VECTOR_DB_MAX_RETRIES (default: 3)
- VECTOR_DB_BACKOFF_BASE (default: 0.5 seconds)

Recommended values:
- CI / short runs: VECTOR_DB_MAX_RETRIES=1, VECTOR_DB_BACKOFF_BASE=0.1
  (fast failure in CI so developers get quick feedback)
- Production / resilient runs: VECTOR_DB_MAX_RETRIES=3-5, VECTOR_DB_BACKOFF_BASE=0.5-1.0
  (more retries and longer backoff to handle transient network or service hiccups)

These variables are read by the vector_db abstraction (backend/app/vector_db.py) and control exponential backoff with jitter.

Next steps

- Add a lightweight healthcheck in CI to start Qdrant and run a few vector upserts during integration tests.
- Add a reconcile CLI to re-upsert embeddings into the vector DB when missing (I can scaffold this next).
