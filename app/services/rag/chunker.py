import os
import re
import sys

# Ye line tumhare 'civicos' folder ko Python path mein add kar degi
# taaki 'app.services.rag.loader' ko access kar sakein
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.services.rag.loader import load_pdf

HEADING_PATTERN = re.compile(
    r"^(?:Section|Clause|Chapter|Part|Article)\b"
    r"|^\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9 ]+$"
    r"|^[A-Z\s]{10,}$"
)


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped and HEADING_PATTERN.match(stripped))


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _split_into_sections(text: str) -> list[str]:
    lines = text.splitlines()
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if _is_heading(line):
            if current:
                sections.append("\n".join(current).strip())
            current = [line.strip()]
        else:
            current.append(line.strip())

    if current:
        sections.append("\n".join(current).strip())

    return [section for section in sections if section]


def _split_long_sentence(sentence: str, chunk_size: int, overlap: int) -> list[str]:
    words = sentence.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        chunks.append(chunk)
        if end == len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _build_section_text(section: str) -> str:
    lines = section.splitlines()
    heading = lines[0].strip() if _is_heading(lines[0]) else ""
    if heading:
        body = " ".join(line.strip() for line in lines[1:] if line.strip())
        return f"{heading}\n\n{body}".strip()
    return " ".join(line.strip() for line in lines if line.strip())


def _get_overlap_sentences(current: list[str], overlap: int, sentence: str) -> list[str]:
    overlap_sentences: list[str] = []
    overlap_len = 0
    for sent in reversed(current):
        if overlap_len + len(sent) <= overlap:
            overlap_sentences.insert(0, sent)
            overlap_len += len(sent) + 1
        else:
            break
    return overlap_sentences if overlap_sentences else [sentence]


def _build_sentence_chunks(sentences: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_len + len(sentence) <= chunk_size or not current:
            current.append(sentence)
            current_len += len(sentence) + 1
            continue

        chunks.append(" ".join(current).strip())
        current = _get_overlap_sentences(current, overlap, sentence)
        current_len = sum(len(sent) + 1 for sent in current)

        if len(sentence) > chunk_size:
            long_chunks = _split_long_sentence(sentence, chunk_size, overlap)
            if long_chunks:
                if current and current != [sentence]:
                    current = []
                    current_len = 0
                chunks.extend(long_chunks)

    if current:
        chunks.append(" ".join(current).strip())

    return [chunk for chunk in chunks if chunk]


def _chunk_section(section: str, chunk_size: int, overlap: int) -> list[str]:
    section = _normalize_text(section)
    if not section:
        return []

    text = _build_section_text(section)
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    return _build_sentence_chunks(sentences, chunk_size, overlap)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    sections = _split_into_sections(text)
    result: list[str] = []

    for section in sections:
        section_chunks = _chunk_section(section, chunk_size, overlap)
        result.extend(section_chunks)

    return result


if __name__ == "__main__":
    # Ab ye path sahi se dhoondhega
    pdf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "documents", "scheme.pdf"
    )
    text = load_pdf(pdf_path)
    chunks = chunk_text(text)
    print(f"Total chunks: {len(chunks)}")
    print(f"First chunk: {chunks[0][:100]}...")
