from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("abix.semantic_search")

_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf",
    ".sh", ".bash", ".zsh", ".fish",
    ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".kt",
    ".rb", ".php", ".sql", ".r", ".m", ".swift",
    ".csv", ".tsv", ".xml", ".log",
    ".env", ".gitignore", ".dockerignore", "Makefile", "Dockerfile",
}

_MAX_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50


@dataclass
class SearchResult:
    path: str
    score: float
    snippet: str
    chunk_index: int = 0


class SemanticSearchEngine:
    def __init__(
        self,
        persist_dir: str = "data/chroma",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._embedding_model_name = embedding_model
        self._collection = None
        self._embedder = None
        self._init_done = False

    def _ensure_init(self) -> None:
        if self._init_done:
            return
        self._init_done = True
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="abix_files",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialized at %s", self._persist_dir)
        except ImportError:
            logger.warning("chromadb not installed — semantic search unavailable")
            self._collection = None
        except Exception as e:
            logger.warning("ChromaDB init failed: %s", e)
            self._collection = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self._embedding_model_name)
            logger.info("Loaded embedding model: %s", self._embedding_model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed — using Chroma default embeddings")
            self._embedder = None
        except Exception as e:
            logger.warning("Embedding model load failed: %s", e)
            self._embedder = None

    def _should_index(self, path: Path) -> bool:
        if path.suffix.lower() in _TEXT_EXTENSIONS:
            return True
        if path.name in ("Makefile", "Dockerfile", "README", "LICENSE"):
            return True
        return False

    def _chunk_text(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + _MAX_CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - _CHUNK_OVERLAP
            if start + _CHUNK_OVERLAP >= len(text):
                break
        return chunks if chunks else [text[:_MAX_CHUNK_SIZE].strip()]

    def _file_hash(self, path: Path) -> str:
        try:
            stat = path.stat()
            key = f"{path}:{stat.st_size}:{int(stat.st_mtime)}"
            return hashlib.md5(key.encode()).hexdigest()
        except Exception:
            return ""

    def index_directory(self, dir_path: str, max_files: int = 500) -> int:
        self._ensure_init()
        if self._collection is None:
            return 0

        search_path = Path(dir_path).expanduser().resolve()
        if not search_path.exists():
            return 0

        indexed = 0
        for item in search_path.rglob("*"):
            if indexed >= max_files:
                break
            if not item.is_file() or not self._should_index(item):
                continue

            try:
                text = item.read_text(errors="ignore")
                if not text.strip():
                    continue
            except Exception:
                continue

            file_id = self._file_hash(item)
            doc_id = f"{item}:{file_id}"
            try:
                existing = self._collection.get(ids=[doc_id])
                if existing and existing["ids"]:
                    continue
            except Exception:
                pass

            chunks = self._chunk_text(text)
            for i, chunk in enumerate(chunks[:5]):
                chunk_id = f"{doc_id}:chunk{i}"
                try:
                    self._collection.upsert(
                        ids=[chunk_id],
                        documents=[chunk],
                        metadatas=[{
                            "file_path": str(item),
                            "file_name": item.name,
                            "chunk_index": i,
                            "file_hash": file_id,
                        }],
                    )
                except Exception as e:
                    logger.debug("Failed to index chunk: %s", e)

            indexed += 1

        logger.info("Indexed %d files from %s", indexed, dir_path)
        return indexed

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        self._ensure_init()
        if self._collection is None:
            return []

        try:
            count = self._collection.count()
            if count == 0:
                return []
        except Exception:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k * 2, 20),
            )
        except Exception as e:
            logger.warning("ChromaDB query failed: %s", e)
            return []

        search_results: list[SearchResult] = []
        seen_files: set[str] = set()

        if not results or not results.get("documents"):
            return []

        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            file_path = meta.get("file_path", "")
            if file_path in seen_files:
                continue
            seen_files.add(file_path)

            score = 1.0 - dist if dist <= 1.0 else max(0.0, 1.0 - dist / 2.0)

            search_results.append(SearchResult(
                path=file_path,
                score=score,
                snippet=doc[:200],
                chunk_index=meta.get("chunk_index", 0),
            ))

            if len(search_results) >= top_k:
                break

        return search_results

    def clear_index(self) -> None:
        self._ensure_init()
        if self._collection is not None:
            try:
                self._client.delete_collection("abix_files")
                self._collection = self._client.get_or_create_collection(
                    name="abix_files",
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("Cleared semantic search index")
            except Exception as e:
                logger.warning("Failed to clear index: %s", e)
