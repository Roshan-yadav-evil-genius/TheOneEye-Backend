from sentence_transformers import SentenceTransformer,CrossEncoder
from pathlib import Path


CACHE_FOLDER = Path.cwd() / "bin" / "sentence_transformers_cache"


model = SentenceTransformer("BAAI/bge-large-en-v1.5",cache_folder=CACHE_FOLDER.as_posix())
model.save("./bin/models/bge-large-en-v1.5")

model = SentenceTransformer("BAAI/bge-small-en-v1.5",cache_folder=CACHE_FOLDER.as_posix())
model.save("./bin/models/bge-small-en-v1.5")

model = CrossEncoder("BAAI/bge-reranker-large",cache_folder=CACHE_FOLDER.as_posix())
model.save("./bin/models/bge-reranker-large")