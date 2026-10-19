"""Local retrieval: TF-IDF + cosine similarity over data/knowledge/*.md. No external API."""
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings

MIN_SCORE = 0.12


@dataclass
class Chunk:
    doc: str
    title: str
    category: str
    section: str
    text: str


def _category(stem: str) -> str:
    if stem.startswith("fabric_"):
        return "Fabric care"
    return {"general_laundry_safety": "Laundry safety", "washing_symbols": "Washing symbols",
            "detergent_guidance": "Detergent guidance", "drying_methods": "Drying methods",
            "ironing_temperatures": "Ironing temperatures"}.get(stem, "General")


def load_chunks(kdir: Path) -> list[Chunk]:
    chunks = []
    for f in sorted(Path(kdir).glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M)
        title = title.group(1).strip() if title else f.stem
        for part in re.split(r"^## ", text, flags=re.M)[1:]:
            head, _, body = part.partition("\n")
            chunks.append(Chunk(f.name, title, _category(f.stem), head.strip(), body.strip()))
    return chunks


class Retriever:
    def __init__(self, kdir: Path | None = None):
        self.chunks = load_chunks(kdir or settings.knowledge_dir)
        self.vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        corpus = [f"{c.title} {c.section} {c.text}" for c in self.chunks]
        self.matrix = self.vec.fit_transform(corpus) if corpus else None

    def search(self, query: str, k: int = 3, min_score: float = MIN_SCORE) -> list[dict]:
        if not self.chunks or not query.strip():
            return []
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        order = sims.argsort()[::-1][:k]
        return [{"document": self.chunks[i].doc, "title": self.chunks[i].title, "category": self.chunks[i].category,
                 "section": self.chunks[i].section, "text": self.chunks[i].text, "score": round(float(sims[i]), 3)}
                for i in order if sims[i] >= min_score]


@lru_cache
def get_retriever() -> Retriever:
    return Retriever()
