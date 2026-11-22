"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re

STOP_WORDS = set('a an the is are was were be been to of for in on at by with and or do does did i we you it this that these those how where what which when any there from can my all'.split())


def words(text):
    """Normalize punctuation and a few common word forms; ignore filler words."""
    aliases = {'auth': 'authentication', 'tokens': 'token',
               'generated': 'generation', 'generates': 'generation',
               'connect': 'connection', 'lists': 'list', 'returns': 'return',
               'fields': 'column', 'columns': 'column', 'tables': 'table'}
    return {aliases.get(word, word) for word in re.findall(r'[a-z0-9]+', text.lower())
            if word not in STOP_WORDS}

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in sorted(glob.glob(pattern)):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        Build an inverted index mapping normalized words to source filenames.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }

        Tokenization is shared with scoring so query and document terms agree.
        """
        index = {}
        for filename, text in documents:
            for word in words(text):
                index.setdefault(word, []).append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        Count distinct normalized query words present in the text.
        Repeating a word does not inflate its score.
        """
        return len(words(query) & words(text))

    def retrieve(self, query, top_k=3):
        """
        Find candidate documents, then score their heading-delimited sections.
        Require two distinct matches (one for a one-word query) and at least
        half of the meaningful query terms. Add a small heading-match bonus.
        Return at most top_k (filename, section) pairs in descending rank.
        """
        if top_k <= 0:
            return []
        query_words = words(query)
        if not query_words:
            return []
        candidates = set()
        for word in query_words:
            candidates.update(self.index.get(word, []))

        results = []
        for filename, text in self.documents:
            if filename not in candidates:
                continue
            # Keep each heading with its paragraphs, code examples, and lists.
            for section in re.split(r'(?m)(?=^#{1,6} )', text):
                section = section.strip()
                if not section:
                    continue
                score = self.score_document(query, section)
                # A lone incidental word is weak evidence for a longer question.
                minimum = min(2, len(query_words))
                if score >= minimum and score / len(query_words) >= 0.5:
                    heading = section.splitlines()[0]
                    # Prefer a matching topic heading over incidental body mentions.
                    rank = score + 0.5 * self.score_document(query, heading)
                    results.append((rank, filename, section))
        results.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [(filename, section) for _, filename, section in results[:top_k]]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
