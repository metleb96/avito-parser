import json
from sentence_transformers import SentenceTransformer, util

print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

print("Loading data...")
with open('vectorized_data.json', 'r', encoding='utf-8') as f:
    vector_data = json.load(f)
print(f"Loaded {len(vector_data)} items.")

query = "колпак"
print(f"Query: {query}")

query_embedding = model.encode(query, convert_to_tensor=True)
corpus_embeddings = [item['embedding'] for item in vector_data]

print("Searching...")
hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=5)

print("Results:")
for hit in hits[0]:
    idx = hit['corpus_id']
    print(f"Score: {hit['score']:.4f} | Title: {vector_data[idx]['Title']}")
