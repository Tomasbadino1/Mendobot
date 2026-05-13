"""Lógica de procesamiento para consultas conversacionales."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data_manager import DataManager


class MendoBotEngine:
    """Motor mínimo para CU-01 (consulta de carrera)."""

    _STOPWORDS = {
        "de",
        "la",
        "el",
        "en",
        "y",
        "a",
        "del",
        "las",
        "los",
        "un",
        "una",
        "que",
        "por",
        "para",
        "con",
        "es",
        "se",
        "al",
        "como",
    }

    def __init__(self, data_manager: DataManager) -> None:
        self.data_manager = data_manager
        self._vectorizer: TfidfVectorizer | None = None
        self._candidate_vectors = None
        self._candidates: list[dict[str, str]] = []
        self._build_semantic_index()

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", ascii_only).strip()

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        normalized = cls._normalize(text)
        tokens = re.findall(r"[a-z0-9]+", normalized)
        return [token for token in tokens if token not in cls._STOPWORDS]

    def _extract_careers(self) -> list[dict[str, Any]]:
        data = self.data_manager._data
        careers: list[dict[str, Any]] = []

        careers_by_key = data.get("careers")
        if isinstance(careers_by_key, dict):
            for key, value in careers_by_key.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("id", key)
                    item.setdefault("nombre", value.get("name", key))
                    careers.append(item)

        careers_list = data.get("carreras")
        if isinstance(careers_list, list):
            for career in careers_list:
                if isinstance(career, dict):
                    careers.append(career)

        return careers

    def _extract_faq_items(self) -> list[dict[str, str]]:
        data = self.data_manager._data
        faq_data = data.get("faq", data.get("faqs", []))
        faq_items: list[dict[str, str]] = []
        if isinstance(faq_data, list):
            for item in faq_data:
                if isinstance(item, dict):
                    question = str(item.get("pregunta", item.get("question", "")))
                    answer = str(item.get("respuesta", item.get("answer", "")))
                    if question and answer:
                        faq_items.append({"pregunta": question, "respuesta": answer})
        return faq_items

    def _build_semantic_index(self) -> None:
        # Implements: RF-01, CU-01
        # Precomputamos vectores TF-IDF una sola vez para cumplir RNF-01 (<3s).
        candidates: list[dict[str, str]] = []

        for career in self._extract_careers():
            nombre = str(career.get("nombre", career.get("name", "Carrera")))
            descripcion = str(career.get("descripcion", career.get("description", "")))
            modalidad = str(career.get("modalidad", ""))
            duracion = str(career.get("duracion", ""))
            sedes = (
                " ".join(str(sede) for sede in career.get("sedes", []))
                if isinstance(career.get("sedes"), list)
                else ""
            )
            searchable_text = " ".join(
                part for part in [nombre, descripcion, modalidad, duracion, sedes, "oferta academica plan estudio"]
                if part
            )
            response = f"{nombre}: {descripcion}".strip()
            candidates.append({"text": searchable_text, "response": response})

        for faq in self._extract_faq_items():
            searchable_text = f"{faq['pregunta']} faq consulta frecuente".strip()
            candidates.append({"text": searchable_text, "response": faq["respuesta"]})

        self._candidates = candidates
        if not candidates:
            return

        documents = [self._normalize(item["text"]) for item in candidates]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._candidate_vectors = self._vectorizer.fit_transform(documents)

    def answer(self, user_query: str) -> dict[str, Any]:
        """Responde una consulta textual para CU-01."""
        # Implements: RF-01, CU-01
        if not user_query.strip() or self._vectorizer is None or self._candidate_vectors is None:
            return {
                "found": False,
                "message": "No encontré esa carrera. ¿Podés reformular la consulta?",
                "animate_avatar": False,
            }

        normalized_query = self._normalize(user_query)
        query_vector = self._vectorizer.transform([normalized_query])
        similarities = cosine_similarity(query_vector, self._candidate_vectors)[0]
        best_idx = int(similarities.argmax())
        best_score = float(similarities[best_idx])

        if best_score >= 0.14:
            return {
                "found": True,
                "message": self._candidates[best_idx]["response"],
                "animate_avatar": True,
            }

        return {
            "found": False,
            "message": "No encontré esa carrera. ¿Podés reformular la consulta?",
            "animate_avatar": False,
        }
