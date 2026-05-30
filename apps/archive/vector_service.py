# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Vector indexing service using LanceDB for case-isolated semantic search.

Provides serverless, local vector storage and retrieval for document chunks,
with strict multi-tenant isolation by case UUID. Each case receives its own
LanceDB database at ``media/cases/{case_uuid}/lancedb/``, ensuring zero data
leakage between cases.

Embeddings are generated entirely via a local sentence-transformers pipeline
(``all-MiniLM-L6-v2``) so that confidential legal data never leaves the
server.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

import lancedb
from django.conf import settings


class VectorIndexService:
    """
    Serverless vector indexing engine using LanceDB with case isolation.

    Each case gets its own LanceDB database stored at::

        media/cases/{case_uuid}/lancedb/

    All chunks from documents within a case are stored in the
    ``document_chunks`` table within that case's isolated database, ensuring
    strict data compartmentalization between cases.

    Embeddings are generated locally via sentence-transformers
    (``all-MiniLM-L6-v2``) to prevent confidential legal data from being
    transmitted to external endpoints.

    Attributes:
        case_uuid: The UUID of the case this service instance is bound to.
        CHUNK_SIZE: Character window size for text chunking.
        CHUNK_OVERLAP: Overlap between consecutive chunks.
        TABLE_NAME: Standardised LanceDB table name (``document_chunks``).
    """

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TABLE_NAME: str = "document_chunks"

    _FRONTMATTER_RE: re.Pattern = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL
    )
    _META_LINE_RE: re.Pattern = re.compile(r"^\s*(\w+)\s*:\s*(.*?)\s*$")

    def __init__(self, case_uuid: str) -> None:
        """
        Initialise the vector service for a specific case.

        Args:
            case_uuid: The UUID string of the case to bind this service to.
                       All vector operations will be scoped to this case's
                       isolated LanceDB database.
        """
        self.case_uuid: str = str(case_uuid)
        self._db_path: str = str(
            Path(settings.LANCE_DB_BASE) / "cases" / self.case_uuid / "lancedb"
        )
        self._db: Optional[lancedb.DBConnection] = None
        self._model: Any = None

    def _get_db(self) -> lancedb.DBConnection:
        """
        Return (or create) the LanceDB database connection for this case.

        The database directory is created on first access if it does not
        already exist.

        Returns:
            An active LanceDB ``DBConnection`` instance scoped to this case.
        """
        if self._db is None:
            os.makedirs(self._db_path, exist_ok=True)
            self._db = lancedb.connect(self._db_path)
        return self._db

    def _get_embedding_model(self) -> Any:
        """
        Lazy-load the sentence-transformers embedding model.

        The model is loaded once and cached on the instance to prevent
        redundant downloads and keep initialisation overhead to a single
        call.

        Returns:
            A ``SentenceTransformer`` model instance (``all-MiniLM-L6-v2``).
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    @staticmethod
    def _parse_frontmatter(text: str) -> dict[str, str]:
        """
        Extract YAML frontmatter metadata from a digital twin file.

        Uses lightweight regex parsing to extract ``key: value`` pairs from
        the ``---`` delimited header. Avoids introducing third-party
        frontmatter parsing libraries.

        Args:
            text: The full content of a digital twin markdown file.

        Returns:
            A dictionary mapping frontmatter keys to their string values.
            Returns an empty dict if no valid frontmatter is found.
        """
        match = VectorIndexService._FRONTMATTER_RE.match(text)
        if not match:
            return {}
        frontmatter: dict[str, str] = {}
        for line in match.group(1).split("\n"):
            m = VectorIndexService._META_LINE_RE.match(line)
            if m:
                frontmatter[m.group(1)] = m.group(2).strip().strip("\"'")
        return frontmatter

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        """
        Remove the YAML frontmatter section from a digital twin file.

        Args:
            text: The full content of a digital twin markdown file.

        Returns:
            The markdown body with the frontmatter section removed.
        """
        return VectorIndexService._FRONTMATTER_RE.sub("", text, count=1)

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """
        Slice narrative text into overlapping chunks for vector indexing.

        Uses a sliding window of ``CHUNK_SIZE`` characters with
        ``CHUNK_OVERLAP`` characters of overlap between consecutive windows.
        Chunk boundaries are adjusted backward to the nearest preceding
        newline character to preserve contextual paragraph integrity.

        Args:
            text: The narrative text body (frontmatter already removed).

        Returns:
            A list of text chunk strings with leading/trailing whitespace
            stripped. Empty chunks are discarded.
        """
        if not text:
            return []
        chunks: list[str] = []
        start: int = 0
        text_len: int = len(text)

        while start < text_len:
            end: int = min(start + VectorIndexService.CHUNK_SIZE, text_len)
            if end < text_len:
                last_newline: int = text.rfind("\n", start, end)
                if last_newline > start:
                    end = last_newline
            chunk: str = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_len:
                break
            start = end - VectorIndexService.CHUNK_OVERLAP

        return chunks

    def index_digital_twin(
        self, file_path: str, document_instance
    ) -> int:
        """
        Index a digital twin markdown file into the case-isolated LanceDB.

        The pipeline performs the following steps:

        1. Reads the ``.md`` twin file from the filesystem.
        2. Parses the YAML frontmatter to recover the original
           ``virtual_path`` and ``original_name``.
        3. Strips the frontmatter and slices the narrative body into
           overlapping chunks.
        4. Embeds each chunk via the local sentence-transformer pipeline.
        5. Persists each chunk as a row in the ``document_chunks`` table
           with mandatory metadata columns.

        Metadata columns stored per row:

        * ``id``: UUID string unique to the chunk.
        * ``document_uuid``: The relational UUID of the source document.
        * ``virtual_path``: The original hierarchical folder tree path
          parsed from the YAML frontmatter.
        * ``text_content``: The raw narrative text fragment.
        * ``vector``: The 384-dimensional embedding vector.

        Args:
            file_path: Absolute filesystem path to the ``.md`` digital twin.
            document_instance: The Django model instance (e.g.
                ``RawDocument`` or ``ArchiveDocument``) that owns this twin.
                Must have a ``uuid`` or ``id`` attribute.

        Returns:
            The number of chunks successfully indexed.

        Raises:
            FileNotFoundError: If the twin file does not exist at
                ``file_path``.
            IOError: If the twin file cannot be read.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content: str = f.read()

        frontmatter: dict[str, str] = self._parse_frontmatter(content)
        narrative: str = self._strip_frontmatter(content)
        chunks: list[str] = self._chunk_text(narrative)

        virtual_path: str = frontmatter.get("virtual_path", "")
        doc_uuid: str = str(
            getattr(document_instance, "uuid", None)
            or getattr(document_instance, "id", "")
        )

        db: lancedb.DBConnection = self._get_db()
        model: Any = self._get_embedding_model()

        batch: list[dict[str, Any]] = []
        for chunk_text in chunks:
            vec: list[float] = model.encode(chunk_text).tolist()
            batch.append({
                "id": str(uuid.uuid4()),
                "document_uuid": doc_uuid,
                "virtual_path": virtual_path,
                "text_content": chunk_text,
                "vector": vec,
            })

        if self.TABLE_NAME not in db.table_names():
            db.create_table(self.TABLE_NAME, data=batch)
        else:
            table = db.open_table(self.TABLE_NAME)
            table.add(batch)

        return len(batch)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Perform a semantic vector search against the case's document chunks.

        Encodes the query string and retrieves the ``top_k`` most similar
        chunks from the case-isolated LanceDB table using cosine distance.

        Args:
            query: Natural language query string.
            top_k: Number of nearest neighbours to return (default 5).

        Returns:
            A list of result dictionaries, each containing the stored
            metadata columns and a ``_distance`` field indicating the cosine
            distance from the query vector.

        Raises:
            FileNotFoundError: If the LanceDB table has not been created yet
                (no documents indexed for this case).
        """
        model: Any = self._get_embedding_model()
        db: lancedb.DBConnection = self._get_db()
        table = db.open_table(self.TABLE_NAME)
        query_vec: list[float] = model.encode(query).tolist()
        results: list[dict[str, Any]] = (
            table.search(query_vec).limit(top_k).to_list()
        )
        return results
