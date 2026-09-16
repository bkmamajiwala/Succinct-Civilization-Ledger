import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSearchEngine:
    def __init__(self):
        self.entries = []
        self.model = None
        self.faiss = None
        self.index = None
        self.embeddings = None
        self.vectorizer = None
        self.tfidf = None
        enabled = os.getenv("ENABLE_SENTENCE_TRANSFORMERS", "false").lower() == "true"
        if enabled:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.faiss = faiss
            except Exception:
                self.model = None

    def rebuild(self, entries):
        self.entries = entries
        texts = [self._entry_text(entry) for entry in entries]
        if not texts:
            return
        if self.model:
            vectors = self.model.encode(texts, normalize_embeddings=True).astype("float32")
            self.embeddings = vectors
            self.index = self.faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)
        else:
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self.tfidf = self.vectorizer.fit_transform(texts)

    def search(self, query, civilization_id=None, limit=10):
        if not query or not self.entries:
            return []
        candidate_indexes = list(range(len(self.entries)))
        if civilization_id is not None:
            candidate_indexes = [i for i, entry in enumerate(self.entries) if entry["civilization_id"] == civilization_id]
        if not candidate_indexes:
            return []

        if self.model and self.index:
            query_vector = self.model.encode([query], normalize_embeddings=True).astype("float32")
            scores, indexes = self.index.search(query_vector, min(len(self.entries), max(limit * 4, limit)))
            ranked = [(int(i), float(s)) for i, s in zip(indexes[0], scores[0]) if int(i) in candidate_indexes]
        else:
            query_vector = self.vectorizer.transform([query])
            sims = cosine_similarity(query_vector, self.tfidf).ravel()
            ranked = [(i, float(sims[i])) for i in candidate_indexes]
            ranked.sort(key=lambda item: item[1], reverse=True)

        return [
            {**self.entries[i], "similarity": round(score, 4), "snippet": self.entries[i]["description"][:220]}
            for i, score in ranked[:limit]
        ]

    def _entry_text(self, entry):
        return f"{entry['civilization_name']} {entry['domain']} {entry['entry_type']} {entry['description']}"
