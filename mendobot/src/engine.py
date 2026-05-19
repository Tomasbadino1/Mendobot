"""Lógica de procesamiento para consultas conversacionales."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.data_manager import DataManager


# CU-01 E1: no forzar respuesta si la similitud global es baja o hay empate ambiguo.
_MENSAJE_SIN_CONFIANZA = "No encontré la informacion pedida. ¿Podés reformular la consulta?"
_MIN_RAW_DEFAULT = 0.19
_MIN_RAW_FAQ = 0.13
_MIN_RAW_GLOBAL = 0.12
_AMBIGUOUS_SCORE_CEIL = 0.36
_AMBIGUOUS_GAP_MIN = 0.022
_INTENT_FAQ_BOOST = 4.2
_INTENT_CAREER_WEIGHT = 0.38
_INSTITUTIONAL_INTENT_RE = re.compile(
    r"\b(sede|sedes|donde|modalidad|lugar|ubicacion|ubicación|campus|direccion|dirección|domicilio)\b"
)
_COMO_ES_INTENT_RE = re.compile(r"\bcomo\s+es\b")
_ECONOMIC_INTENT_RE = re.compile(
    r"\b(cuota|cuotas|pago|pagos|dinero|costo|precio|matricula|matricular|arancel|mensual(?:es)?|economico|economica|financier[oa]|pesos|sale|cuesta)\b"
)
_TRAMITES_INTENT_RE = re.compile(
    r"\b(inscripci[oó]n|requisitos|papeles|documentaci[oó]n|tramites|tr[aá]mites|anal[ií]tico|partida|dni\b|cursillo|nivelatorio|legalizad[oa]|constancia)\b"
)
_INTENT_PRIORITY_FAQ_BOOST = 6.5
_INTENT_PRIORITY_OTHERS_WEIGHT = 0.32
_FOLLOWUP_MAX_LEN = 48
_FOLLOWUP_MAX_WORDS = 8


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
        self._candidates: list[dict[str, Any]] = []
        self._last_topic: str | None = None
        self._context_career_label: str | None = None
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

    def _extract_careers(self, data: dict[str, Any]) -> list[dict[str, Any]]:
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

    @staticmethod
    def _career_admin_search_blob(career: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("horario", "estado_inscripcion"):
            val = career.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val)
        for key in (
            "objetivos_formativos",
            "competencias_tecnicas",
            "roles_laborales",
            "documentacion_requerida",
        ):
            blob = MendoBotEngine._join_keyword_list(career.get(key))
            if blob:
                parts.append(blob)
        cp = career.get("cursillo_preuniversitario")
        if isinstance(cp, dict):
            parts.extend(str(v) for v in cp.values() if str(v).strip())
        inf = career.get("informacion_economica")
        if isinstance(inf, dict):
            parts.extend(str(v) for v in inf.values() if str(v).strip())
        pk_t = MendoBotEngine._join_keyword_list(career.get("palabras_clave_tramites"))
        if pk_t:
            parts.append(pk_t)
        return " ".join(parts)

    @staticmethod
    def _join_keyword_list(value: Any) -> str:
        if not isinstance(value, list):
            return ""
        return " ".join(str(x) for x in value if str(x).strip())

    def _extract_faq_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        faq_data = data.get("faq", data.get("faqs", []))
        faq_items: list[dict[str, Any]] = []
        if isinstance(faq_data, list):
            for item in faq_data:
                if isinstance(item, dict):
                    question = str(item.get("pregunta", item.get("question", "")))
                    answer = str(item.get("respuesta", item.get("answer", "")))
                    if question and answer:
                        entry: dict[str, Any] = {"pregunta": question, "respuesta": answer}
                        tema = item.get("tema")
                        if isinstance(tema, str) and tema.strip():
                            entry["tema"] = tema.strip().lower()
                        pk = item.get("palabras_clave")
                        if isinstance(pk, list) and pk:
                            entry["palabras_clave"] = pk
                        faq_items.append(entry)
        return faq_items

    _YEAR_LABELS = {
        "primer_ano": "Primer año",
        "segundo_ano": "Segundo año",
        "tercer_ano": "Tercer año",
    }
    _YEAR_QUERY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        ("tercer_ano", re.compile(r"\b(tercer|tercero|tercera|3er|3°)\b")),
        ("segundo_ano", re.compile(r"\b(segundo|segunda|2do|2°)\b")),
        ("primer_ano", re.compile(r"\b(primer|primero|1er|1°)\b")),
    ]

    @classmethod
    def _materias_to_text(cls, materias: Any) -> str:
        if isinstance(materias, list):
            return " ".join(str(m) for m in materias)
        if isinstance(materias, dict):
            tokens: list[str] = []
            for key, label in cls._YEAR_LABELS.items():
                items = materias.get(key)
                if isinstance(items, list):
                    tokens.append(label)
                    tokens.extend(str(m) for m in items)
            return " ".join(tokens)
        return ""

    @classmethod
    def _detect_year_filter(cls, consulta: str) -> str | None:
        normalized = cls._normalize(consulta)
        for year_key, pattern in cls._YEAR_QUERY_PATTERNS:
            if pattern.search(normalized):
                return year_key
        return None

    @classmethod
    def _format_year_plan_response(cls, career: dict[str, Any], year_key: str) -> str | None:
        materias = career.get("materias")
        if not isinstance(materias, dict):
            return None
        items = materias.get(year_key)
        if not isinstance(items, list) or not items:
            return None
        nombre = str(career.get("nombre", career.get("name", "Carrera")))
        label = cls._YEAR_LABELS[year_key]
        materia_names = ", ".join(str(m) for m in items)
        return f"{label} de {nombre}: {materia_names}."

    @classmethod
    def _format_plan_response(
        cls, career: dict[str, Any], year_keys: list[str] | None = None
    ) -> str:
        nombre = str(career.get("nombre", career.get("name", "Carrera")))
        duracion = str(career.get("duracion", ""))
        parts = [f"Plan de estudios de {nombre}."]
        if duracion:
            parts.append(f"Duración: {duracion}.")
        materias = career.get("materias")
        if isinstance(materias, dict):
            keys = year_keys if year_keys else list(cls._YEAR_LABELS.keys())
            for key in keys:
                label = cls._YEAR_LABELS.get(key, key)
                items = materias.get(key)
                if isinstance(items, list) and items:
                    materia_names = ", ".join(str(m) for m in items)
                    parts.append(f"{label}: {materia_names}.")
        elif isinstance(materias, list) and materias:
            materia_names = ", ".join(str(m) for m in materias)
            parts.append(f"Materias: {materia_names}.")
        return " ".join(parts)

    def _build_semantic_index(self) -> None:
        # RNF-01: índice TF-IDF precalculado al iniciar (<3s por consulta).
        data = self.data_manager.cargar_datos()
        candidates: list[dict[str, Any]] = []

        for career in self._extract_careers(data):
            career_id = str(career.get("id", ""))
            nombre = str(career.get("nombre", career.get("name", "Carrera")))
            descripcion = str(career.get("descripcion", career.get("description", "")))
            modalidad = str(career.get("modalidad", ""))
            duracion = str(career.get("duracion", ""))
            sedes = (
                " ".join(str(sede) for sede in career.get("sedes", []))
                if isinstance(career.get("sedes"), list)
                else ""
            )
            materias = self._materias_to_text(career.get("materias"))
            pk_desc = self._join_keyword_list(career.get("palabras_clave_descripcion"))
            pk_mat = self._join_keyword_list(career.get("palabras_clave_materias"))
            admin_blob = self._career_admin_search_blob(career)
            searchable_text = " ".join(
                part
                for part in [
                    nombre,
                    descripcion,
                    modalidad,
                    duracion,
                    sedes,
                    materias,
                    pk_desc,
                    admin_blob,
                    "oferta academica carrera",
                ]
                if part
            )
            response = f"{nombre}: {descripcion}".strip()
            candidates.append(
                {"text": searchable_text, "response": response, "kind": "career", "career_id": career_id}
            )

            plan_text = " ".join(
                part
                for part in [
                    nombre,
                    duracion,
                    materias,
                    pk_mat,
                    admin_blob,
                    "plan de estudios materias duracion correlativas",
                ]
                if part
            )
            candidates.append(
                {
                    "text": plan_text,
                    "response": self._format_plan_response(career),
                    "kind": "plan",
                    "career_id": career_id,
                }
            )

            materias_dict = career.get("materias")
            if isinstance(materias_dict, dict):
                for year_key, label in self._YEAR_LABELS.items():
                    year_items = materias_dict.get(year_key, [])
                    if not isinstance(year_items, list) or not year_items:
                        continue
                    year_text = " ".join(
                        part
                        for part in [
                            nombre,
                            label,
                            " ".join(str(m) for m in year_items),
                            pk_mat,
                            admin_blob,
                            "materias plan estudios",
                        ]
                        if part
                    )
                    year_response = self._format_year_plan_response(career, year_key)
                    if year_response:
                        candidates.append(
                            {
                                "text": year_text,
                                "response": year_response,
                                "kind": "plan_year",
                                "career_id": career_id,
                                "year_key": year_key,
                            }
                        )

        for faq in self._extract_faq_items(data):
            pk_blob = self._join_keyword_list(faq.get("palabras_clave"))
            searchable_text = " ".join(
                part
                for part in [
                    faq["pregunta"],
                    pk_blob,
                    faq.get("tema", ""),
                    "faq consulta frecuente",
                ]
                if part
            ).strip()
            faq_q = f"{faq['pregunta']} {pk_blob}".lower()
            tema = str(faq.get("tema", "")).lower()
            if tema == "economico":
                faq_intent = "faq_economico"
            elif tema in ("cursillo", "documentacion", "tramites"):
                faq_intent = "faq_tramites"
            elif tema == "perfil_laboral":
                faq_intent = "faq_perfil"
            elif tema == "sedes" or any(
                w in faq_q
                for w in ("sede", "donde", "ubic", "lugar", "campus", "direcc", "contacto", "domicilio")
            ):
                faq_intent = "faq_ubicacion"
            elif tema == "modalidad" or any(
                w in faq_q
                for w in ("modalidad", "presencial", "virtual", "aula", "cursado", "online", "distancia", "asistencia")
            ):
                faq_intent = "faq_modalidad"
            else:
                faq_intent = "faq_otro"
            candidates.append(
                {
                    "text": searchable_text,
                    "response": faq["respuesta"],
                    "kind": "faq",
                    "faq_intent": faq_intent,
                    "career_id": "",
                }
            )

        self._candidates = candidates
        if not candidates:
            return

        documents = [self._normalize(item["text"]) for item in candidates]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        self._candidate_vectors = self._vectorizer.fit_transform(documents)

    def _career_by_id(self, data: dict[str, Any], career_id: str) -> dict[str, Any] | None:
        for career in self._extract_careers(data):
            if str(career.get("id", "")) == career_id:
                return career
        return None

    @classmethod
    def _has_institutional_intent(cls, normalized: str) -> bool:
        if _INSTITUTIONAL_INTENT_RE.search(normalized):
            return True
        if _COMO_ES_INTENT_RE.search(normalized):
            return True
        return False

    @classmethod
    def _institutional_subintent(cls, normalized: str) -> str | None:
        if re.search(
            r"\b(sede|sedes|donde|ubicacion|ubicación|lugar|campus|direccion|dirección|domicilio)\b",
            normalized,
        ):
            return "ubicacion"
        if re.search(
            r"\b(modalidad|presencial|virtual|aula|online|cursado|distancia|asistencia)\b",
            normalized,
        ) or re.search(r"\bir\s+a\s+clase\b", normalized):
            return "modalidad"
        if _COMO_ES_INTENT_RE.search(normalized):
            return "como_es"
        return None

    def _default_career_keywords(self) -> str:
        data = self.data_manager.cargar_datos()
        careers = self._extract_careers(data)
        if not careers:
            return "desarrollo software"
        return str(careers[0].get("nombre", careers[0].get("name", "carrera")))

    def _maybe_expand_followup(self, consulta_usuario: str) -> str | None:
        if self._last_topic != "materias":
            return None
        raw = consulta_usuario.strip()
        if len(raw) > _FOLLOWUP_MAX_LEN:
            return None
        normalized = self._normalize(raw)
        n_words = len(normalized.split())
        if n_words > _FOLLOWUP_MAX_WORDS:
            return None
        yk = self._detect_year_filter(consulta_usuario)
        if yk is None:
            return None
        if n_words > 3 and not re.search(r"\by\b", normalized):
            return None
        label = self._YEAR_LABELS[yk]
        tail = self._context_career_label or self._default_career_keywords()
        return f"materias del {label.lower()} plan de estudios {tail}"

    @classmethod
    def _has_economic_intent(cls, normalized: str) -> bool:
        if _ECONOMIC_INTENT_RE.search(normalized):
            return True
        if "50" in normalized and "%" in normalized:
            return True
        return False

    @classmethod
    def _has_tramites_intent(cls, normalized: str) -> bool:
        return bool(_TRAMITES_INTENT_RE.search(normalized))

    @classmethod
    def _has_perfil_intent(cls, normalized: str) -> bool:
        return bool(
            re.search(
                r"\b(empleo|trabajo|laboral|egreso|full\s*stack|qa\b|mobile|backend|frontend|competencias|bases\s+de\s+datos|poo\b)\b",
                normalized,
            )
        )

    def _prioritize_faq_intent(
        self, similarities: np.ndarray, target_intent: str, non_match_faq_weight: float = 0.42
    ) -> np.ndarray:
        boosted = np.asarray(similarities, dtype=np.float64).copy()
        for i, cand in enumerate(self._candidates):
            if cand.get("kind") != "faq":
                boosted[i] *= _INTENT_PRIORITY_OTHERS_WEIGHT
                continue
            if cand.get("faq_intent") == target_intent:
                boosted[i] *= _INTENT_PRIORITY_FAQ_BOOST
            else:
                boosted[i] *= non_match_faq_weight
        return boosted

    def _scores_institutional_boost(
        self, similarities: np.ndarray, normalized_query: str
    ) -> np.ndarray:
        boosted = np.asarray(similarities, dtype=np.float64).copy()
        sub = self._institutional_subintent(normalized_query)
        for i, cand in enumerate(self._candidates):
            if cand.get("kind") != "faq":
                boosted[i] *= _INTENT_CAREER_WEIGHT
                continue
            intent_tag = cand.get("faq_intent", "faq_otro")
            if sub == "ubicacion" and intent_tag == "faq_ubicacion":
                boosted[i] *= _INTENT_FAQ_BOOST * 1.35
            elif sub == "modalidad" and intent_tag == "faq_modalidad":
                boosted[i] *= _INTENT_FAQ_BOOST * 1.35
            elif sub == "como_es":
                boosted[i] *= _INTENT_FAQ_BOOST * 1.1
            elif sub is None:
                boosted[i] *= _INTENT_FAQ_BOOST
            else:
                boosted[i] *= _INTENT_FAQ_BOOST * 0.85
        return boosted

    def _apply_query_intent_scores(
        self, similarities: np.ndarray, normalized_query: str
    ) -> np.ndarray:
        # RF-03 / RF-04: sede y modalidad vía refuerzo institucional cuando corresponde.
        if self._has_economic_intent(normalized_query):
            return self._prioritize_faq_intent(similarities, "faq_economico")
        if self._has_tramites_intent(normalized_query):
            return self._prioritize_faq_intent(similarities, "faq_tramites")
        if self._has_institutional_intent(normalized_query):
            return self._scores_institutional_boost(similarities, normalized_query)
        if self._has_perfil_intent(normalized_query):
            return self._prioritize_faq_intent(similarities, "faq_perfil")
        return np.asarray(similarities, dtype=np.float64).copy()

    def _confidence_acceptable(
        self,
        raw_chosen: float,
        raw_top1: float,
        raw_top2: float,
        kind: str | None,
        relaxed_faq_ambiguity: bool,
    ) -> bool:
        if raw_top1 < _MIN_RAW_GLOBAL:
            return False
        if kind == "faq":
            floor = (_MIN_RAW_FAQ - 0.02) if relaxed_faq_ambiguity else max(_MIN_RAW_FAQ + 0.04, 0.17)
            if raw_chosen < floor:
                return False
        elif raw_chosen < _MIN_RAW_DEFAULT:
            return False
        ambiguous = raw_top1 < _AMBIGUOUS_SCORE_CEIL and (raw_top1 - raw_top2) < _AMBIGUOUS_GAP_MIN
        if ambiguous:
            if relaxed_faq_ambiguity and kind == "faq" and raw_chosen >= (_MIN_RAW_FAQ - 0.02):
                return True
            return False
        return True

    @staticmethod
    def _top_two_global_scores(similarities: np.ndarray) -> tuple[float, float]:
        flat = similarities.ravel()
        if flat.size == 0:
            return 0.0, 0.0
        if flat.size == 1:
            return float(flat[0]), 0.0
        part = np.partition(flat, -2)[-2:]
        return float(max(part)), float(min(part))

    def _update_topic_context(self, best_idx: int, year_key: str | None) -> None:
        kind = self._candidates[best_idx].get("kind")
        if kind in {"plan", "plan_year"} or year_key is not None:
            self._last_topic = "materias"
            data = self.data_manager.cargar_datos()
            cid = str(self._candidates[best_idx].get("career_id", ""))
            career = self._career_by_id(data, cid) if cid else None
            if career is None:
                careers = self._extract_careers(data)
                career = careers[0] if careers else None
            if career:
                self._context_career_label = str(
                    career.get("nombre", career.get("name", ""))
                )
        elif kind == "faq":
            self._last_topic = "institutional"
        elif kind == "career":
            self._last_topic = "carrera"
        else:
            self._last_topic = None

    def _resolve_year_filtered_message(
        self, consulta_usuario: str, best_idx: int, year_key: str
    ) -> str | None:
        data = self.data_manager.cargar_datos()
        best = self._candidates[best_idx]
        career_id = str(best.get("career_id", ""))
        career = self._career_by_id(data, career_id) if career_id else None
        if career is None:
            careers = self._extract_careers(data)
            career = careers[0] if careers else None
        if career is None:
            return None

        if best.get("kind") == "faq":
            return None
        return self._format_year_plan_response(career, year_key)

    def buscar_respuesta(self, consulta_usuario: str) -> dict[str, Any]:
        # implements: RF-01, RF-02, RF-03, RF-04
        if not consulta_usuario.strip() or self._vectorizer is None or self._candidate_vectors is None:
            return {
                "found": False,
                "message": _MENSAJE_SIN_CONFIANZA,
                "animate_avatar": False,
            }

        resolved = self._maybe_expand_followup(consulta_usuario)
        query_for_match = (resolved or consulta_usuario).strip()

        year_key = self._detect_year_filter(query_for_match)
        normalized_query = self._normalize(query_for_match)
        economic_intent = self._has_economic_intent(normalized_query)
        tramites_intent = self._has_tramites_intent(normalized_query) and not economic_intent
        institutional_intent = self._has_institutional_intent(normalized_query)
        perfil_intent = self._has_perfil_intent(normalized_query)
        relaxed_faq = (
            economic_intent or tramites_intent or institutional_intent or perfil_intent
        )

        query_vector = self._vectorizer.transform([normalized_query])
        raw_similarities = np.asarray(
            cosine_similarity(query_vector, self._candidate_vectors)[0], dtype=np.float64
        )
        adjusted = self._apply_query_intent_scores(raw_similarities, normalized_query)
        best_idx = int(adjusted.argmax())
        raw_chosen = float(raw_similarities.ravel()[best_idx])
        raw_g1, raw_g2 = self._top_two_global_scores(raw_similarities)

        kind = self._candidates[best_idx].get("kind")
        if not self._confidence_acceptable(
            raw_chosen, raw_g1, raw_g2, kind, relaxed_faq
        ):
            return {
                "found": False,
                "message": _MENSAJE_SIN_CONFIANZA,
                "animate_avatar": False,
            }

        if year_key:
            year_message = self._resolve_year_filtered_message(
                consulta_usuario, best_idx, year_key
            )
            if year_message is None:
                data = self.data_manager.cargar_datos()
                careers = self._extract_careers(data)
                if careers:
                    year_message = self._format_year_plan_response(careers[0], year_key)
            if year_message:
                self._update_topic_context(best_idx, year_key)
                return {
                    "found": True,
                    "message": year_message,
                    "animate_avatar": True,
                }

        self._update_topic_context(best_idx, year_key)
        return {
            "found": True,
            "message": str(self._candidates[best_idx]["response"]),
            "animate_avatar": True,
        }

    def answer(self, user_query: str) -> dict[str, Any]:
        """Responde una consulta textual para CU-01."""
        return self.buscar_respuesta(user_query)
