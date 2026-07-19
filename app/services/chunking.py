"""
Document Chunking Service
Splits documents into optimal chunks for vector embedding.
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


class DocumentChunker:
    """Splits documents into chunks for vector embedding."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, document_id: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        chunks = []
        text = text.strip()

        if len(text) <= self.chunk_size:
            return [DocumentChunk(
                chunk_id=f"{document_id}_0",
                document_id=document_id,
                text=text,
                chunk_index=0,
                start_char=0,
                end_char=len(text),
                metadata=metadata,
            )]

        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = ""
        chunk_index = 0
        start_char = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        chunk_id=f"{document_id}_{chunk_index}",
                        document_id=document_id,
                        text=current_chunk.strip(),
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=start_char + len(current_chunk),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    start_char += len(current_chunk) - self.chunk_overlap

                if len(para) > self.chunk_size:
                    words = para.split()
                    sub_chunk = ""
                    for word in words:
                        if len(sub_chunk) + len(word) + 1 <= self.chunk_size:
                            sub_chunk = f"{sub_chunk} {word}" if sub_chunk else word
                        else:
                            if sub_chunk:
                                chunks.append(DocumentChunk(
                                    chunk_id=f"{document_id}_{chunk_index}",
                                    document_id=document_id,
                                    text=sub_chunk.strip(),
                                    chunk_index=chunk_index,
                                    start_char=start_char,
                                    end_char=start_char + len(sub_chunk),
                                    metadata=metadata,
                                ))
                                chunk_index += 1
                                start_char += len(sub_chunk) - self.chunk_overlap
                            sub_chunk = word
                    current_chunk = sub_chunk
                else:
                    current_chunk = para

        if current_chunk and current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{document_id}_{chunk_index}",
                document_id=document_id,
                text=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + len(current_chunk),
                metadata=metadata,
            ))

        return chunks

    def chunk_document(self, document_id: str, text: str, tables: List[Any] = None, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Chunk a full document including tables."""
        metadata = metadata or {}
        all_chunks = []

        text_chunks = self.chunk_text(text, document_id, {**metadata, "content_type": "text"})
        all_chunks.extend(text_chunks)

        if tables:
            for i, table in enumerate(tables):
                table_text = self._table_to_text(table)
                table_chunks = self.chunk_text(
                    table_text,
                    f"{document_id}_table_{i}",
                    {**metadata, "content_type": "table", "table_index": i}
                )
                all_chunks.extend(table_chunks)

        return all_chunks

    def _table_to_text(self, table: Any) -> str:
        """Convert table data to readable text."""
        if isinstance(table, list):
            if table and isinstance(table[0], dict):
                headers = list(table[0].keys())
                lines = [" | ".join(headers)]
                lines.append(" | ".join(["---"] * len(headers)))
                for row in table:
                    lines.append(" | ".join(str(row.get(h, "")) for h in headers))
                return "\n".join(lines)
            else:
                return "\n".join(str(row) for row in table)
        return str(table)
