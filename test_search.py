import json
import logging
from sentence_transformers import SentenceTransformer, util
import torch

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("Loading model...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Model loaded.")

print("Loading data...")
try:
    with open('vectorized_data.json', 'r', encoding='utf-8') as f:
        vector_data = json.load(f)
    print(f"Loaded {len(vector_data)} items.")
except FileNotFoundError:
    logger.error("Файл vectorized_data.json не найден. Сначала запустите парсер и процессор.")
    exit(1)

query = "колпак"
print(f"Query: {query}")

query_embedding = model.encode(query, convert_to_tensor=True)
corpus_embeddings = torch.tensor([item['embedding'] for item in vector_data])

print("Searching...")
hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=5)

print("Results:")
for hit in hits[0]:
    idx = hit['corpus_id']
    # Используем правильные ключи из данных
    title = vector_data[idx].get('Название', vector_data[idx].get('Title', 'No Title'))
    print(f"Score: {hit['score']:.4f} | Title: {title}")
