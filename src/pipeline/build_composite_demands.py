"""Build Composite Demand V3 tables from the intent and entity layers."""

from __future__ import annotations

import argparse
import logging
import re
import string
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "output" / "aba.duckdb"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "composite_demands"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "build_composite_demands.log"

INTENT_KEYWORDS_TABLE = "intent_keywords"
INTENT_SUMMARY_TABLE = "intent_summary"
INTENT_MARKET_NODES_TABLE = "intent_market_nodes"
SEMANTIC_RELATIONSHIPS_TABLE = "semantic_relationships"
DEMAND_OBJECTS_TABLE = "demand_objects"
KEYWORD_ENTITY_EDGES_TABLE = "keyword_entity_edges"

COMPOSITE_DEMANDS_TABLE = "composite_demands"
COMPOSITE_KEYWORDS_TABLE = "composite_keywords"
DEMAND_STRENGTH_V3_TABLE = "demand_strength_v3"
PARENT_LABEL_AUDIT_TABLE = "parent_label_audit"

INPUT_TABLES = [
    INTENT_KEYWORDS_TABLE,
    INTENT_SUMMARY_TABLE,
    INTENT_MARKET_NODES_TABLE,
    SEMANTIC_RELATIONSHIPS_TABLE,
    DEMAND_OBJECTS_TABLE,
    KEYWORD_ENTITY_EDGES_TABLE,
]
OUTPUT_TABLES = [
    DEMAND_STRENGTH_V3_TABLE,
    COMPOSITE_KEYWORDS_TABLE,
    COMPOSITE_DEMANDS_TABLE,
    PARENT_LABEL_AUDIT_TABLE,
]

REQUIRED_COLUMNS = {
    INTENT_KEYWORDS_TABLE: {
        "keyword_id",
        "raw_keyword",
        "normalized_keyword",
        "month",
        "search_frequency_rank",
        "intent",
        "primary_audience_type",
        "primary_audience_value",
        "niche_type",
        "niche_value",
        "recipient",
        "profession",
        "pet",
        "interest",
        "occasion",
        "holiday",
        "lifestyle",
        "theme",
        "product",
    },
    INTENT_SUMMARY_TABLE: {"intent", "best_rank"},
    INTENT_MARKET_NODES_TABLE: {"intent", "primary_audience_type", "primary_audience_value"},
    SEMANTIC_RELATIONSHIPS_TABLE: {
        "left_type",
        "left_value",
        "right_type",
        "right_value",
        "relationship_type",
        "best_rank",
    },
    DEMAND_OBJECTS_TABLE: {"demand_id", "normalized_keyword", "search_frequency_rank"},
    KEYWORD_ENTITY_EDGES_TABLE: {
        "keyword_id",
        "entity_type",
        "entity_value",
        "search_frequency_rank",
    },
}

COMPOSITE_COLUMNS = [
    "demand_id",
    "demand_name",
    "parent_entity_type",
    "parent_label_source",
    "canonical_evidence_phrase",
    "canonical_source_phrase",
    "is_parent_market",
    "intent",
    "recipient",
    "profession",
    "interest",
    "occasion",
    "holiday",
    "lifestyle",
    "theme",
    "product_count",
    "keyword_count",
    "best_rank",
    "p25_rank",
    "median_rank",
    "average_rank",
    "active_months",
    "trend",
]

logger = logging.getLogger(__name__)

SMALL_TITLE_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

DISPLAY_SINGULAR_SUFFIXES = {
    "accessories": "accessory",
    "blankets": "blanket",
    "bottles": "bottle",
    "boxes": "box",
    "cards": "card",
    "cups": "cup",
    "decorations": "decoration",
    "dresses": "dress",
    "frames": "frame",
    "gifts": "gift",
    "ideas": "idea",
    "mugs": "mug",
    "ornaments": "ornament",
    "pictures": "picture",
    "pillows": "pillow",
    "plaques": "plaque",
    "posters": "poster",
    "printables": "printable",
    "prints": "print",
    "shirts": "shirt",
    "signs": "sign",
    "stickers": "sticker",
    "tumblers": "tumbler",
}

CLUSTER_TOKEN_NORMALIZATIONS = {
    **DISPLAY_SINGULAR_SUFFIXES,
    "lovers": "lover",
    "presents": "gift",
    "present": "gift",
}

GIFT_TERMS = {"gift", "gifts", "present", "presents"}
CLUSTER_SUFFIX_NOISE = {"idea", "ideas"}
NON_MARKET_MODIFIER_TOKENS = {
    "awesome",
    "best",
    "cool",
    "cute",
    "everything",
    "good",
    "great",
    "has",
    "have",
    "idea",
    "ideas",
    "nothing",
    "stuff",
    "top",
    "trendy",
    "unique",
    "want",
    "wants",
}
SURFACE_CONNECTOR_TOKENS = {"a", "an", "for", "from", "of", "the", "to", "who", "whom", "with"}
LIKE_LOVE_TOKENS = {"like", "likes", "love", "loves"}
PERSON_REFERENCE_TOKENS = {"people", "person", "someone", "somebody"}
MARKET_CONTEXT_TOKENS = {
    "anniversary",
    "appreciation",
    "birthday",
    "christmas",
    "easter",
    "father",
    "fathers",
    "graduation",
    "halloween",
    "memorial",
    "mother",
    "mothers",
    "retirement",
    "sympathy",
    "valentine",
    "wedding",
    "xmas",
}
PLURAL_NORMALIZATION_SKIP = {
    "christmas",
    "his",
    "mothers",
    "news",
    "this",
    "xmas",
}
IRREGULAR_SINGULARS = {
    "children": "child",
    "men": "man",
    "mice": "mouse",
    "moms": "mom",
    "dads": "dad",
    "women": "woman",
}
GIFT_FOR_DISPLAY_RECIPIENTS = {
    "daughter",
    "dad",
    "father",
    "grandfather",
    "grandmother",
    "grandma",
    "grandpa",
    "husband",
    "mama",
    "mom",
    "mother",
    "papa",
    "son",
    "wife",
}
RELATIONSHIP_SOURCE_NORMALIZATIONS = {
    "child": "kids",
    "children": "kids",
    "daughter": "daughter",
    "daughters": "daughter",
    "dad": "dad",
    "dads": "dad",
    "father": "dad",
    "fathers": "dad",
    "kid": "kids",
    "kids": "kids",
    "mom": "mom",
    "moms": "mom",
    "mother": "mom",
    "mothers": "mom",
    "son": "son",
    "sons": "son",
    "toddler": "toddler",
    "toddlers": "toddler",
}
RELATIONSHIP_PREFIX_SOURCES = {"child", "children", "kid", "kids", "toddler", "toddlers"}
RELATIONSHIP_SUFFIX_SOURCES = {
    "child",
    "children",
    "daughter",
    "daughters",
    "kid",
    "kids",
    "son",
    "sons",
    "toddler",
    "toddlers",
}

MARKET_INTENTS = {
    "gift",
    "memorial",
    "appreciation",
    "retirement",
    "graduation",
    "anniversary",
    "housewarming",
    "sympathy",
}
OCCASION_ONLY_INTENTS = {"birthday", "christmas", "wedding"}
INTENT_ROLE_TOKENS = {
    "gift": {"gift", "gifts", "present", "presents"},
    "memorial": {"memorial", "remembrance", "loss"},
    "appreciation": {"appreciation", "thank", "thanks", "you", "gift", "gifts"},
    "retirement": {"retirement", "retired", "gift", "gifts"},
    "graduation": {"graduation", "graduate", "gift", "gifts"},
    "anniversary": {"anniversary", "gift", "gifts"},
    "housewarming": {"housewarming", "gift", "gifts"},
    "sympathy": {"sympathy", "gift", "gifts"},
    "birthday": {"birthday"},
    "christmas": {"christmas", "xmas"},
    "wedding": {"wedding", "bride", "groom"},
    "personalized": {"personalized", "custom"},
}
ENTITY_VALUE_TOKEN_ALIASES = {
    "mom": {"mom", "mother", "mama", "mum"},
    "dad": {"dad", "father", "papa"},
    "grandma": {"grandma", "grandmother"},
    "grandpa": {"grandpa", "grandfather"},
}
CONNECTOR_TOKENS = SMALL_TITLE_WORDS | {"who", "has", "have", "everything"}
MARKET_DIMENSION_COLUMNS = [
    "recipient",
    "profession",
    "pet",
    "interest",
    "composite_recipient",
    "composite_profession",
    "composite_interest",
    "composite_occasion",
    "composite_holiday",
    "age_group",
    "gender",
    "composite_lifestyle",
    "composite_theme",
]
AUDIENCE_ENTITY_TYPES = {"recipient", "profession", "pet", "interest", "lifestyle"}
OCCASION_ENTITY_TYPES = {"occasion", "holiday"}
PRODUCT_ENTITY_TYPES = {"product"}
FORMAT_ENTITY_TYPES = {"customization", "style", "modifier"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Composite Demand V3 tables from intent and entity evidence."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop existing composite demand tables before rebuilding.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DUCKDB_PATH,
        help="Path to data/output/aba.duckdb.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Folder for Composite Demand V3 CSV reports.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ],
        force=True,
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = connection.execute(
        """
        SELECT count(*)
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(result and result[0])


def table_columns(connection: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def optional_column_select(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
) -> str:
    if column_name in table_columns(connection, table_name):
        return column_name
    return f"NULL AS {column_name}"


def validate_inputs(connection: duckdb.DuckDBPyConnection) -> None:
    missing_tables = [table_name for table_name in INPUT_TABLES if not table_exists(connection, table_name)]
    if missing_tables:
        raise RuntimeError(
            "Missing required table(s): "
            f"{', '.join(missing_tables)}. Run the intent and semantic layers first."
        )

    for table_name, required_columns in REQUIRED_COLUMNS.items():
        missing_columns = sorted(required_columns - table_columns(connection, table_name))
        if missing_columns:
            raise RuntimeError(
                f"{table_name} is missing required columns: {', '.join(missing_columns)}"
            )


def log_input_counts(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in INPUT_TABLES:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("Input %s: %s rows", table_name, f"{row_count:,}")


def ensure_rebuild_allowed(connection: duckdb.DuckDBPyConnection, rebuild: bool) -> None:
    existing_tables = [table_name for table_name in OUTPUT_TABLES if table_exists(connection, table_name)]
    if existing_tables and not rebuild:
        raise RuntimeError(
            "Composite demand tables already exist. Rerun with --rebuild to replace only "
            f"these tables: {', '.join(existing_tables)}"
        )


def drop_output_tables(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in OUTPUT_TABLES:
        logger.info("Dropping %s if it exists", table_name)
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def title_case(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "").strip()
    return string.capwords(text) if text else ""


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value or "").strip()


def phrase_tokens(value: object) -> list[str]:
    text = clean_text(value).lower()
    return re.findall(r"[a-z0-9']+", text)


def normalize_cluster_token(token: str) -> str:
    return CLUSTER_TOKEN_NORMALIZATIONS.get(token, token)


def singularize_surface_token(token: str) -> str:
    normalized = normalize_cluster_token(token)
    if normalized in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[normalized]
    if normalized in PLURAL_NORMALIZATION_SKIP:
        return normalized
    if len(normalized) > 4 and normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if len(normalized) > 4 and (
        normalized.endswith("ches")
        or normalized.endswith("shes")
        or normalized.endswith("xes")
        or normalized.endswith("zes")
    ):
        return normalized[:-2]
    if len(normalized) > 3 and normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def remove_non_market_modifiers(tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in NON_MARKET_MODIFIER_TOKENS]


def rewrite_love_like_surface(tokens: list[str]) -> list[str]:
    output: list[str] = []
    index = 0
    while index < len(tokens):
        if (
            index + 3 < len(tokens)
            and tokens[index] in PERSON_REFERENCE_TOKENS
            and tokens[index + 1] == "who"
            and tokens[index + 2] in LIKE_LOVE_TOKENS
        ):
            subject_tokens: list[str] = []
            index += 3
            while index < len(tokens) and tokens[index] not in SURFACE_CONNECTOR_TOKENS:
                subject_tokens.append(tokens[index])
                index += 1
            output.extend(subject_tokens)
            output.append("lover")
            continue
        output.append(tokens[index])
        index += 1
    return output


def normalized_observed_tokens(value: object) -> list[str]:
    tokens = phrase_tokens(value)
    tokens = remove_non_market_modifiers(tokens)
    tokens = rewrite_love_like_surface(tokens)
    return [singularize_surface_token(token) for token in tokens if token]


def normalize_cluster_tokens(tokens: list[str]) -> list[str]:
    normalized = [normalize_cluster_token(token) for token in tokens if token]
    while normalized and normalized[-1] in CLUSTER_SUFFIX_NOISE:
        normalized.pop()
    return normalized


def canonical_gift_key_tokens(tokens: list[str]) -> list[str]:
    if "gift" not in tokens:
        return [token for token in tokens if token not in SURFACE_CONNECTOR_TOKENS]

    non_gift_tokens = [
        token for token in tokens if token != "gift" and token not in SURFACE_CONNECTOR_TOKENS
    ]
    context_tokens = [token for token in non_gift_tokens if token in MARKET_CONTEXT_TOKENS]
    market_tokens = [token for token in non_gift_tokens if token not in MARKET_CONTEXT_TOKENS]
    return market_tokens + context_tokens + ["gift"]


def normalize_relationship_source_token(token: str) -> str:
    return RELATIONSHIP_SOURCE_NORMALIZATIONS.get(normalize_cluster_token(token), "")


def clean_relationship_parent_tokens(tokens: list[str]) -> list[str]:
    cleaned = [token for token in tokens if token and token not in {"from", "to"}]
    return cleaned if "gift" in cleaned else tokens


def tokens_before(tokens: list[str], stop_index: int) -> list[str]:
    return [token for token in tokens[:stop_index] if token not in SURFACE_CONNECTOR_TOKENS]


def tokens_between(tokens: list[str], start_index: int, stop_tokens: set[str]) -> tuple[list[str], int]:
    output: list[str] = []
    index = start_index
    while index < len(tokens) and tokens[index] not in stop_tokens:
        if tokens[index] not in SURFACE_CONNECTOR_TOKENS:
            output.append(tokens[index])
        index += 1
    return output, index


def relationship_parent_tokens(tokens: list[str]) -> list[str]:
    if "gift" not in tokens:
        return tokens

    gift_index = tokens.index("gift")

    if gift_index + 3 < len(tokens) and tokens[gift_index + 1] in {"for", "to"}:
        target, next_index = tokens_between(tokens, gift_index + 2, {"from"})
        if next_index < len(tokens) and tokens[next_index] == "from" and target:
            source = next((token for token in tokens[next_index + 1 :] if normalize_relationship_source_token(token)), "")
            if source:
                return clean_relationship_parent_tokens(tokens[: gift_index + 2] + target)

    if gift_index + 4 < len(tokens) and tokens[gift_index + 1] == "from":
        source, next_index = tokens_between(tokens, gift_index + 2, {"to", "for"})
        if next_index < len(tokens) and tokens[next_index] in {"to", "for"} and source:
            target, _ = tokens_between(tokens, next_index + 1, {"from", "to", "for"})
            if target and any(normalize_relationship_source_token(token) for token in source):
                return clean_relationship_parent_tokens(tokens[:gift_index] + ["gift", "for"] + target)

    if gift_index > 0 and gift_index + 2 < len(tokens) and tokens[gift_index + 1] == "from":
        target = tokens_before(tokens, gift_index)
        source = next((token for token in tokens[gift_index + 2 :] if normalize_relationship_source_token(token)), "")
        if target and source:
            return clean_relationship_parent_tokens(target + ["gift"])

    if gift_index > 1 and "from" in tokens[:gift_index]:
        from_index = tokens.index("from")
        target = tokens_before(tokens, from_index)
        source = next((token for token in tokens[from_index + 1 : gift_index] if normalize_relationship_source_token(token)), "")
        if target and source:
            return clean_relationship_parent_tokens(target + ["gift"])

    if gift_index == 2:
        first, second = tokens[0], tokens[1]
        if first in RELATIONSHIP_PREFIX_SOURCES and second not in SURFACE_CONNECTOR_TOKENS:
            return clean_relationship_parent_tokens([second, "gift"])
        if second in RELATIONSHIP_SUFFIX_SOURCES and first not in SURFACE_CONNECTOR_TOKENS:
            return clean_relationship_parent_tokens([first, "gift"])

    return tokens


def cluster_key_from_phrase(value: object) -> str:
    tokens = normalized_observed_tokens(value)
    if not tokens:
        return ""
    tokens = relationship_parent_tokens(tokens)
    return " ".join(canonical_gift_key_tokens(tokens))


def singularize_display_tail(tokens: list[str]) -> list[str]:
    if not tokens:
        return tokens
    normalized = list(tokens)
    normalized[-1] = DISPLAY_SINGULAR_SUFFIXES.get(normalized[-1], normalized[-1])
    return normalized


def smart_title_case(value: object) -> str:
    tokens = phrase_tokens(value)
    if not tokens:
        return ""
    titled: list[str] = []
    for index, token in enumerate(tokens):
        if 0 < index < len(tokens) - 1 and token in SMALL_TITLE_WORDS:
            titled.append(token)
        else:
            titled.append(token[:1].upper() + token[1:])
    return " ".join(titled)


def target_from_gift_for_phrase(tokens: list[str]) -> list[str]:
    if len(tokens) < 3 or tokens[0] != "gift" or tokens[1] != "for":
        return []
    target: list[str] = []
    for token in tokens[2:]:
        if token == "for":
            break
        if token not in SURFACE_CONNECTOR_TOKENS:
            target.append(token)
    return target


def has_plural_surface_target(value: object) -> bool:
    tokens = rewrite_love_like_surface(remove_non_market_modifiers(phrase_tokens(value)))
    if len(tokens) < 3:
        return False
    if singularize_surface_token(tokens[0]) != "gift" or tokens[1] != "for":
        return False
    target_tokens: list[str] = []
    for token in tokens[2:]:
        if token == "for":
            break
        if token not in SURFACE_CONNECTOR_TOKENS:
            target_tokens.append(token)
    return any(
        singularize_surface_token(token) != normalize_cluster_token(token)
        for token in target_tokens
    )


def display_from_gift_for_phrase(value: object, tokens: list[str]) -> str:
    target = target_from_gift_for_phrase(tokens)
    if not target:
        return ""
    context = [
        token
        for token in tokens[2 + len(target) :]
        if token not in SURFACE_CONNECTOR_TOKENS and token in MARKET_CONTEXT_TOKENS
    ]
    last_target = target[-1]
    if (
        last_target in GIFT_FOR_DISPLAY_RECIPIENTS
        and not has_plural_surface_target(value)
        and not context
    ):
        return smart_title_case(" ".join(["gift", "for", *target]))
    return smart_title_case(" ".join(target + context + ["gift"]))


def canonical_display_phrase(value: object) -> str:
    tokens = normalized_observed_tokens(value)
    if not tokens:
        return ""
    tokens = relationship_parent_tokens(tokens)
    gift_for_display = display_from_gift_for_phrase(value, tokens)
    if gift_for_display:
        return gift_for_display
    return smart_title_case(" ".join(canonical_gift_key_tokens(tokens)))


def first_clean_value(values: pd.Series) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def clean_values(values: pd.Series) -> list[str]:
    return [text for text in (clean_text(value) for value in values) if text]


def dominant_clean_value(frame: pd.DataFrame, column: str) -> str:
    values = frame[[column, "search_frequency_rank"]].copy()
    values[column] = values[column].map(clean_text)
    values = values[values[column] != ""]
    if values.empty:
        return ""

    ranked = (
        values.groupby(column, dropna=False)
        .agg(count=(column, "size"), best_rank=("search_frequency_rank", "min"))
        .reset_index()
        .sort_values(["count", "best_rank", column], ascending=[False, True, True])
    )
    return clean_text(ranked.iloc[0][column])


def nonempty_rate(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return 0.0
    return sum(1 for value in frame[column] if clean_text(value)) / len(frame)


def positive_rate(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return sum(1 for value in frame[column] if pd.notna(value) and float(value or 0) > 0) / len(frame)


def distinct_clean_count(frame: pd.DataFrame, column: str) -> int:
    return len(set(clean_values(frame[column])))


def pipe_values(values: pd.Series) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        for part in clean_text(value).split("|"):
            text = clean_text(part)
            if text and text not in seen:
                output.append(text)
                seen.add(text)
    return output


def covered_tokens_from_values(values: list[str]) -> set[str]:
    covered: set[str] = set()
    for value in values:
        covered.update(phrase_tokens(value))
    return covered


def semantic_alias_tokens(value: object) -> set[str]:
    text = clean_text(value).lower()
    return INTENT_ROLE_TOKENS.get(text, set()) | ENTITY_VALUE_TOKEN_ALIASES.get(text, set())


def ontology_unmapped_tokens(phrase: object, profile: pd.Series) -> list[str]:
    tokens = set(phrase_tokens(phrase))
    covered = set(CONNECTOR_TOKENS)
    intent = clean_text(profile.get("dominant_intent"))
    covered.update(covered_tokens_from_values(clean_text(profile.get("ontology_entity_values")).split("|")))
    semantic_values = [
        intent,
        clean_text(profile.get("dominant_audience_value")),
        clean_text(profile.get("dominant_recipient")),
        clean_text(profile.get("dominant_profession")),
        clean_text(profile.get("dominant_interest")),
        clean_text(profile.get("dominant_occasion")),
        clean_text(profile.get("dominant_holiday")),
        clean_text(profile.get("dominant_age_group")),
        clean_text(profile.get("dominant_gender")),
        clean_text(profile.get("dominant_lifestyle")),
        clean_text(profile.get("dominant_theme")),
        clean_text(profile.get("dominant_product")),
        clean_text(profile.get("dominant_customization")),
        clean_text(profile.get("dominant_style")),
        clean_text(profile.get("dominant_modifier")),
    ]
    covered.update(covered_tokens_from_values(semantic_values))
    for value in semantic_values:
        covered.update(semantic_alias_tokens(value))
    return sorted(token for token in tokens if token not in covered)


def semantic_cluster_profile(frame: pd.DataFrame) -> pd.Series:
    keyword_count = len(frame)
    market_dimension_count = sum(
        1 for column in MARKET_DIMENSION_COLUMNS if column in frame and distinct_clean_count(frame, column)
    )
    product_rate = nonempty_rate(frame, "product")
    customization_rate = nonempty_rate(frame, "customization")
    style_rate = nonempty_rate(frame, "style")
    modifier_rate = nonempty_rate(frame, "modifier")
    edge_product_rate = positive_rate(frame, "ontology_product_roles")
    edge_format_rate = positive_rate(frame, "ontology_format_roles")
    edge_audience_rate = positive_rate(frame, "ontology_audience_roles")
    edge_occasion_rate = positive_rate(frame, "ontology_occasion_roles")
    product_role_rate = max(product_rate, edge_product_rate)
    product_format_rate = max(
        product_rate,
        customization_rate,
        style_rate,
        modifier_rate,
        edge_product_rate,
        edge_format_rate,
    )
    audience_role_rate = max(
        edge_audience_rate,
        nonempty_rate(frame, "primary_audience_value"),
        nonempty_rate(frame, "composite_recipient"),
        nonempty_rate(frame, "composite_profession"),
        nonempty_rate(frame, "composite_interest"),
        nonempty_rate(frame, "age_group"),
        nonempty_rate(frame, "gender"),
    )
    occasion_role_rate = max(
        edge_occasion_rate,
        nonempty_rate(frame, "composite_occasion"),
        nonempty_rate(frame, "composite_holiday"),
    )
    ontology_entity_values = " | ".join(pipe_values(frame["ontology_entity_values"]))

    return pd.Series(
        {
            "dominant_intent": dominant_clean_value(frame, "intent"),
            "dominant_audience_type": dominant_clean_value(frame, "primary_audience_type"),
            "dominant_audience_value": dominant_clean_value(frame, "primary_audience_value"),
            "dominant_recipient": dominant_clean_value(frame, "composite_recipient"),
            "dominant_profession": dominant_clean_value(frame, "composite_profession"),
            "dominant_interest": dominant_clean_value(frame, "composite_interest"),
            "dominant_occasion": dominant_clean_value(frame, "composite_occasion"),
            "dominant_holiday": dominant_clean_value(frame, "composite_holiday"),
            "dominant_age_group": dominant_clean_value(frame, "age_group"),
            "dominant_gender": dominant_clean_value(frame, "gender"),
            "dominant_lifestyle": dominant_clean_value(frame, "composite_lifestyle"),
            "dominant_theme": dominant_clean_value(frame, "composite_theme"),
            "dominant_product": dominant_clean_value(frame, "product"),
            "dominant_customization": dominant_clean_value(frame, "customization"),
            "dominant_style": dominant_clean_value(frame, "style"),
            "dominant_modifier": dominant_clean_value(frame, "modifier"),
            "product_evidence_rate": round(product_rate, 4),
            "customization_evidence_rate": round(customization_rate, 4),
            "product_format_rate": round(product_format_rate, 4),
            "product_role_rate": round(product_role_rate, 4),
            "audience_role_rate": round(audience_role_rate, 4),
            "occasion_role_rate": round(occasion_role_rate, 4),
            "ontology_product_rate": round(edge_product_rate, 4),
            "ontology_format_rate": round(edge_format_rate, 4),
            "ontology_audience_rate": round(edge_audience_rate, 4),
            "ontology_occasion_rate": round(edge_occasion_rate, 4),
            "ontology_entity_values": ontology_entity_values,
            "distinct_product_count": distinct_clean_count(frame, "product"),
            "market_dimension_count": market_dimension_count,
            "keyword_count_for_profile": keyword_count,
        }
    )


def classify_parent_entity_type(profile: pd.Series, phrase: object) -> tuple[str, bool, str]:
    intent = clean_text(profile.get("dominant_intent"))
    product_role_rate = float(profile.get("product_role_rate") or 0.0)
    product_format_rate = float(profile.get("product_format_rate") or 0.0)
    audience_role_rate = float(profile.get("audience_role_rate") or 0.0)
    occasion_role_rate = float(profile.get("occasion_role_rate") or 0.0)
    market_dimension_count = int(profile.get("market_dimension_count") or 0)
    unmapped_tokens = ontology_unmapped_tokens(phrase, profile)
    has_audience = audience_role_rate > 0.0 or market_dimension_count >= 1
    has_occasion = occasion_role_rate > 0.0 or intent in OCCASION_ONLY_INTENTS
    has_market_intent = intent in MARKET_INTENTS
    has_product_role = product_role_rate >= 0.5
    has_format_role = product_format_rate >= 0.5

    if intent == "decor":
        return "decor_category", False, "excluded_decor_intent_from_ontology_metadata"

    if intent == "apparel":
        return "apparel", False, "excluded_apparel_intent_from_ontology_metadata"

    if has_product_role:
        return "product_type", False, "excluded_product_role_composition"
    if has_format_role:
        return "fulfillment_modifier", False, "excluded_format_role_composition"

    if intent in OCCASION_ONLY_INTENTS and not has_market_intent:
        return "occasion", False, "excluded_occasion_composition_without_market_intent"

    if has_market_intent and has_audience and has_occasion and not unmapped_tokens:
        return "market", True, "accepted_audience_occasion_market_intent_composition"
    if has_market_intent and has_audience and not unmapped_tokens:
        return "market", True, "accepted_audience_market_intent_composition"

    if has_market_intent and has_audience and unmapped_tokens:
        return "unknown", False, "excluded_unmapped_ontology_terms_in_market_phrase"

    if market_dimension_count == 1 and intent in {"unknown", ""}:
        return "audience", False, "excluded_audience_only_cluster"
    if market_dimension_count == 0:
        return "unknown", False, "excluded_insufficient_market_semantics"

    return "unknown", False, "excluded_ambiguous_parent_semantics"


def semantic_parent_name_from_evidence(row: pd.Series) -> str:
    return composite_name(
        pd.Series(
            {
                "intent": row.get("intent"),
                "audience_type": row.get("primary_audience_type"),
                "audience_value": row.get("primary_audience_value"),
                "interest": row.get("composite_interest"),
                "holiday": row.get("composite_holiday"),
                "occasion": row.get("composite_occasion"),
                "lifestyle": row.get("composite_lifestyle"),
                "theme": row.get("composite_theme"),
            }
        )
    )


def composite_name(row: pd.Series) -> str:
    intent = clean_text(row["intent"])
    audience_type = clean_text(row["audience_type"])
    audience = clean_text(row["audience_value"])
    interest = clean_text(row["interest"])
    holiday = clean_text(row["holiday"])
    occasion = clean_text(row["occasion"])
    lifestyle = clean_text(row["lifestyle"])
    theme = clean_text(row["theme"])

    if audience_type == "interest" and interest == audience:
        interest = ""

    audience_name = title_case(audience)
    if not audience_name:
        audience_name = "Unspecified"

    if intent == "gift":
        if holiday:
            return f"{title_case(holiday)} {audience_name} Gift"
        if interest:
            return f"{audience_name} {title_case(interest)} Gift"
        if lifestyle:
            return f"{audience_name} {title_case(lifestyle)} Gift"
        if theme:
            return f"{audience_name} {title_case(theme)} Gift"
        if occasion:
            return f"{title_case(occasion)} {audience_name} Gift"
        return f"{audience_name} Gift"

    if intent == "appreciation":
        return f"{audience_name} Appreciation"
    if intent == "memorial":
        return f"{audience_name} Memorial"
    if intent == "personalized":
        if interest:
            return f"Personalized {audience_name} {title_case(interest)}"
        return f"Personalized {audience_name}"
    if intent == "christmas":
        if interest:
            return f"Christmas {audience_name} {title_case(interest)}"
        return f"Christmas {audience_name}"
    if intent and intent != "unknown":
        if interest:
            return f"{audience_name} {title_case(interest)} {title_case(intent)}"
        return f"{audience_name} {title_case(intent)}"

    if interest:
        return f"{audience_name} {title_case(interest)} Demand"
    if lifestyle:
        return f"{audience_name} {title_case(lifestyle)} Demand"
    if theme:
        return f"{audience_name} {title_case(theme)} Demand"
    return f"{audience_name} Demand"


def create_composite_evidence_stage(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Creating composite demand evidence stage")
    customization_select = optional_column_select(connection, INTENT_KEYWORDS_TABLE, "customization")
    style_select = optional_column_select(connection, INTENT_KEYWORDS_TABLE, "style")
    modifier_select = optional_column_select(connection, INTENT_KEYWORDS_TABLE, "modifier")
    age_group_select = optional_column_select(connection, INTENT_KEYWORDS_TABLE, "age_group")
    gender_select = optional_column_select(connection, INTENT_KEYWORDS_TABLE, "gender")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE composite_evidence_stage AS
        WITH edge_rollup AS (
            SELECT
                keyword_id,
                string_agg(DISTINCT entity_type, '|') AS ontology_entity_types,
                string_agg(DISTINCT entity_value, '|') AS ontology_entity_values,
                sum(CASE WHEN entity_type IN ('recipient', 'profession', 'pet', 'interest', 'lifestyle')
                    THEN 1 ELSE 0 END) AS ontology_audience_roles,
                sum(CASE WHEN entity_type IN ('occasion', 'holiday')
                    THEN 1 ELSE 0 END) AS ontology_occasion_roles,
                sum(CASE WHEN entity_type = 'product'
                    THEN 1 ELSE 0 END) AS ontology_product_roles,
                sum(CASE WHEN entity_type IN ('customization', 'style', 'modifier')
                    THEN 1 ELSE 0 END) AS ontology_format_roles
            FROM {KEYWORD_ENTITY_EDGES_TABLE}
            GROUP BY keyword_id
        ),
        usable_keywords AS (
            SELECT
                keywords.keyword_id,
                keywords.raw_keyword,
                keywords.normalized_keyword,
                keywords.month,
                keywords.search_frequency_rank,
                keywords.intent,
                keywords.primary_audience_type,
                keywords.primary_audience_value,
                keywords.niche_type,
                keywords.niche_value,
                keywords.recipient,
                keywords.profession,
                keywords.pet,
                keywords.interest,
                keywords.occasion,
                keywords.holiday,
                keywords.lifestyle,
                keywords.theme,
                keywords.product,
                {customization_select},
                {style_select},
                {modifier_select},
                {age_group_select},
                {gender_select},
                coalesce(edge_rollup.ontology_entity_types, '') AS ontology_entity_types,
                coalesce(edge_rollup.ontology_entity_values, '') AS ontology_entity_values,
                coalesce(edge_rollup.ontology_audience_roles, 0) AS ontology_audience_roles,
                coalesce(edge_rollup.ontology_occasion_roles, 0) AS ontology_occasion_roles,
                coalesce(edge_rollup.ontology_product_roles, 0) AS ontology_product_roles,
                coalesce(edge_rollup.ontology_format_roles, 0) AS ontology_format_roles
            FROM {INTENT_KEYWORDS_TABLE} AS keywords
            LEFT JOIN edge_rollup
              ON keywords.keyword_id = edge_rollup.keyword_id
            WHERE keywords.intent <> 'unknown'
              AND keywords.primary_audience_type IS NOT NULL
              AND keywords.primary_audience_value IS NOT NULL
        ),
        normalized AS (
            SELECT
                *,
                CASE
                    WHEN primary_audience_type = 'profession' THEN primary_audience_value
                    ELSE NULL
                END AS composite_profession,
                CASE
                    WHEN primary_audience_type = 'recipient' THEN primary_audience_value
                    WHEN primary_audience_type = 'pet' THEN primary_audience_value
                    ELSE NULL
                END AS composite_recipient,
                CASE
                    WHEN intent IN ('appreciation', 'memorial') THEN NULL
                    WHEN niche_type = 'interest' THEN niche_value
                    WHEN primary_audience_type = 'interest' THEN primary_audience_value
                    ELSE NULL
                END AS composite_interest,
                CASE
                    WHEN intent = 'appreciation' THEN 'appreciation'
                    WHEN niche_type = 'occasion' THEN niche_value
                    ELSE occasion
                END AS composite_occasion,
                CASE
                    WHEN intent = 'christmas' THEN 'christmas'
                    WHEN holiday IS NOT NULL THEN holiday
                    ELSE NULL
                END AS composite_holiday,
                CASE WHEN niche_type = 'lifestyle' THEN niche_value ELSE lifestyle END
                    AS composite_lifestyle,
                CASE WHEN niche_type = 'theme' THEN niche_value ELSE theme END
                    AS composite_theme
            FROM usable_keywords
        )
        SELECT
            concat(
                intent,
                '|',
                coalesce(composite_recipient, ''),
                '|',
                coalesce(composite_profession, ''),
                '|',
                coalesce(composite_interest, ''),
                '|',
                coalesce(composite_occasion, ''),
                '|',
                coalesce(composite_holiday, ''),
                '|',
                coalesce(composite_lifestyle, ''),
                '|',
                coalesce(composite_theme, '')
            ) AS composite_key,
            *
        FROM normalized
        """
    )
    row_count = connection.execute("SELECT count(*) FROM composite_evidence_stage").fetchone()[0]
    logger.info("Composite evidence stage: %s rows", f"{row_count:,}")


def count_distinct_clean(values: pd.Series) -> int:
    cleaned = {clean_text(value) for value in values}
    cleaned.discard("")
    return len(cleaned)


def trend_label(row: pd.Series, latest_month: object) -> str:
    first_rank = row.get("first_best_rank")
    last_rank = row.get("last_best_rank")
    if row.get("active_months") == 1 and row.get("last_month") == latest_month:
        return "emerging"
    if pd.isna(first_rank) or float(first_rank) == 0:
        return "stable"

    rank_delta_pct = (float(first_rank) - float(last_rank)) * 100.0 / float(first_rank)
    if rank_delta_pct >= 10:
        return "growing"
    if rank_delta_pct <= -10:
        return "declining"
    return "stable"


def create_composite_metric_stage(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info("Creating composite demand metric stage")
    evidence = connection.execute("SELECT * FROM composite_evidence_stage").df()
    if evidence.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    evidence["search_frequency_rank"] = pd.to_numeric(
        evidence["search_frequency_rank"], errors="coerce"
    )
    evidence["parent_cluster_key"] = evidence["normalized_keyword"].map(cluster_key_from_phrase)
    evidence["canonical_source_candidate"] = evidence["normalized_keyword"].map(clean_text)
    evidence["display_candidate"] = evidence["normalized_keyword"].map(canonical_display_phrase)
    evidence["old_parent"] = evidence.apply(semantic_parent_name_from_evidence, axis=1)
    evidence = evidence[
        (evidence["parent_cluster_key"] != "")
        & (evidence["canonical_source_candidate"] != "")
        & (evidence["display_candidate"] != "")
    ].copy()

    candidate_stats = (
        evidence.groupby(
            ["parent_cluster_key", "canonical_source_candidate", "display_candidate"],
            dropna=False,
        )
        .agg(
            candidate_best_rank=("search_frequency_rank", "min"),
            candidate_average_rank=("search_frequency_rank", "mean"),
            candidate_frequency=("normalized_keyword", "size"),
            candidate_active_months=("month", count_distinct_clean),
            candidate_source_count=("raw_keyword", count_distinct_clean),
        )
        .reset_index()
    )
    candidate_stats["candidate_token_count"] = candidate_stats["display_candidate"].map(
        lambda value: len(phrase_tokens(value))
    )
    candidate_stats["candidate_char_count"] = candidate_stats["display_candidate"].map(
        lambda value: len(clean_text(value))
    )
    canonical_labels = (
        candidate_stats.sort_values(
            [
                "parent_cluster_key",
                "candidate_best_rank",
                "candidate_frequency",
                "candidate_average_rank",
                "candidate_active_months",
                "candidate_source_count",
                "candidate_token_count",
                "candidate_char_count",
                "canonical_source_candidate",
            ],
            ascending=[True, True, False, True, False, False, True, True, True],
            na_position="last",
        )
        .drop_duplicates("parent_cluster_key")
        .rename(
            columns={
                "canonical_source_candidate": "canonical_source_phrase",
                "display_candidate": "demand_name",
            }
        )
    )

    evidence = evidence.merge(
        canonical_labels[["parent_cluster_key", "demand_name", "canonical_source_phrase"]],
        on="parent_cluster_key",
        how="left",
    )
    evidence["evidence_phrase"] = evidence["canonical_source_phrase"]

    grouped = evidence.groupby("parent_cluster_key", dropna=False)
    metrics = grouped.agg(
        product_count=("product", count_distinct_clean),
        keyword_count=("normalized_keyword", "size"),
        best_rank=("search_frequency_rank", "min"),
        p25_rank=("search_frequency_rank", lambda values: values.quantile(0.25)),
        median_rank=("search_frequency_rank", "median"),
        average_rank=("search_frequency_rank", "mean"),
        active_months=("month", count_distinct_clean),
        distinct_keyword_count=("normalized_keyword", count_distinct_clean),
        first_month=("month", "min"),
        last_month=("month", "max"),
    ).reset_index()

    metrics = metrics[
        (metrics["distinct_keyword_count"] >= 2) | (metrics["best_rank"] <= 100000)
    ].copy()
    valid_cluster_keys = set(metrics["parent_cluster_key"])
    evidence = evidence[evidence["parent_cluster_key"].isin(valid_cluster_keys)].copy()

    if evidence.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    canonical_labels = canonical_labels[
        canonical_labels["parent_cluster_key"].isin(valid_cluster_keys)
    ].copy()
    cluster_profiles = (
        evidence.groupby("parent_cluster_key", dropna=False)
        .apply(semantic_cluster_profile)
        .reset_index()
        .merge(
            canonical_labels[["parent_cluster_key", "demand_name", "canonical_source_phrase"]],
            on="parent_cluster_key",
            how="left",
        )
    )
    cluster_profiles["canonical_evidence_phrase"] = cluster_profiles["canonical_source_phrase"]
    classifications = cluster_profiles.apply(
        lambda row: classify_parent_entity_type(row, row.get("demand_name")),
        axis=1,
        result_type="expand",
    )
    classifications.columns = ["parent_entity_type", "is_parent_market", "classification_reason"]
    cluster_profiles = pd.concat([cluster_profiles, classifications], axis=1)
    cluster_profiles["parent_label_source"] = "dominant_observed_phrase"

    representative = (
        evidence.sort_values(
            ["parent_cluster_key", "search_frequency_rank", "month", "normalized_keyword"],
            ascending=[True, True, True, True],
            na_position="last",
        )
        .drop_duplicates("parent_cluster_key")
        [
            [
                "parent_cluster_key",
                "intent",
                "primary_audience_type",
                "primary_audience_value",
                "composite_recipient",
                "composite_profession",
                "composite_interest",
                "composite_occasion",
                "composite_holiday",
                "composite_lifestyle",
                "composite_theme",
                "customization",
                "style",
                "modifier",
            ]
        ]
        .rename(
            columns={
                "primary_audience_type": "audience_type",
                "primary_audience_value": "audience_value",
                "composite_recipient": "recipient",
                "composite_profession": "profession",
                "composite_interest": "interest",
                "composite_occasion": "occasion",
                "composite_holiday": "holiday",
                "composite_lifestyle": "lifestyle",
                "composite_theme": "theme",
            }
        )
    )

    month_best = (
        evidence.groupby(["parent_cluster_key", "month"], dropna=False)["search_frequency_rank"]
        .min()
        .reset_index(name="month_best_rank")
    )
    first_best = (
        metrics[["parent_cluster_key", "first_month"]]
        .merge(
            month_best,
            left_on=["parent_cluster_key", "first_month"],
            right_on=["parent_cluster_key", "month"],
            how="left",
        )
        [["parent_cluster_key", "month_best_rank"]]
        .rename(columns={"month_best_rank": "first_best_rank"})
    )
    last_best = (
        metrics[["parent_cluster_key", "last_month"]]
        .merge(
            month_best,
            left_on=["parent_cluster_key", "last_month"],
            right_on=["parent_cluster_key", "month"],
            how="left",
        )
        [["parent_cluster_key", "month_best_rank"]]
        .rename(columns={"month_best_rank": "last_best_rank"})
    )

    metrics = (
        metrics.merge(
            canonical_labels[["parent_cluster_key", "demand_name", "canonical_source_phrase"]],
            on="parent_cluster_key",
        )
        .merge(representative, on="parent_cluster_key")
        .merge(first_best, on="parent_cluster_key", how="left")
        .merge(last_best, on="parent_cluster_key", how="left")
        .merge(
            cluster_profiles[
                [
                    "parent_cluster_key",
                    "parent_entity_type",
                    "parent_label_source",
                    "canonical_evidence_phrase",
                    "is_parent_market",
                    "classification_reason",
                ]
            ],
            on="parent_cluster_key",
            how="left",
        )
    )
    latest_month = evidence["month"].max()
    metrics["trend"] = metrics.apply(lambda row: trend_label(row, latest_month), axis=1)
    evidence = evidence.merge(
        cluster_profiles[
            [
                "parent_cluster_key",
                "parent_entity_type",
                "parent_label_source",
                "canonical_evidence_phrase",
                "is_parent_market",
                "classification_reason",
            ]
        ],
        on="parent_cluster_key",
        how="left",
    )

    cluster_sizes = (
        evidence.groupby("parent_cluster_key", dropna=False)["normalized_keyword"]
        .nunique()
        .reset_index(name="cluster_size")
    )
    audit = (
        evidence.groupby(
            [
                "old_parent",
                "demand_name",
                "canonical_source_phrase",
                "parent_cluster_key",
                "parent_entity_type",
                "is_parent_market",
                "classification_reason",
            ],
            dropna=False,
        )
        .agg(evidence_phrase=("evidence_phrase", first_clean_value))
        .reset_index()
        .merge(cluster_sizes, on="parent_cluster_key", how="left")
        .rename(columns={"demand_name": "new_parent"})
    )
    split_counts = audit.groupby("old_parent", dropna=False)["new_parent"].nunique().to_dict()
    audit["mapping_reason"] = audit.apply(
        lambda row: (
            "unchanged_canonical_observed_label"
            if row["old_parent"] == row["new_parent"]
            else (
                "split_semantic_parent_into_observed_phrase_clusters"
                if split_counts.get(row["old_parent"], 0) > 1
                else "replaced_semantic_reconstruction_with_observed_cluster_label"
            )
        ),
        axis=1,
    )
    audit["reason"] = audit.apply(
        lambda row: (
            f"{row['classification_reason']}; {row['mapping_reason']}"
            if bool(row["is_parent_market"])
            else row["classification_reason"]
        ),
        axis=1,
    )
    audit = audit[
        [
            "old_parent",
            "new_parent",
            "canonical_source_phrase",
            "parent_entity_type",
            "is_parent_market",
            "reason",
            "evidence_phrase",
            "cluster_size",
        ]
    ]

    metrics = metrics[metrics["is_parent_market"] == True].copy()
    evidence = evidence[evidence["is_parent_market"] == True].copy()

    metrics = metrics[
        [
            "parent_cluster_key",
            "demand_name",
            "parent_entity_type",
            "parent_label_source",
            "canonical_evidence_phrase",
            "canonical_source_phrase",
            "is_parent_market",
            "intent",
            "audience_type",
            "audience_value",
            "recipient",
            "profession",
            "interest",
            "occasion",
            "holiday",
            "lifestyle",
            "theme",
            "product_count",
            "keyword_count",
            "best_rank",
            "p25_rank",
            "median_rank",
            "average_rank",
            "active_months",
            "distinct_keyword_count",
            "first_month",
            "last_month",
            "trend",
        ]
    ]
    logger.info("Composite phrase clusters: %s rows", f"{len(metrics):,}")
    return metrics, evidence, audit


def build_composite_demands(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    metrics, clustered_evidence, audit = create_composite_metric_stage(connection)
    if metrics.empty:
        raise RuntimeError("No composite demands were produced from intent_keywords")

    metrics = metrics.sort_values(
        ["best_rank", "p25_rank", "keyword_count", "parent_cluster_key"],
        ascending=[True, True, False, True],
        na_position="last",
    ).reset_index(drop=True)
    metrics.insert(0, "demand_id", [f"CD{index:06d}" for index in range(1, len(metrics) + 1)])

    connection.register("composite_metric_frame", metrics)
    connection.register("composite_clustered_evidence_frame", clustered_evidence)
    connection.register("parent_label_audit_frame", audit)
    connection.execute(
        f"""
        CREATE TABLE {COMPOSITE_DEMANDS_TABLE} AS
        SELECT
            demand_id,
            demand_name,
            parent_entity_type,
            parent_label_source,
            canonical_evidence_phrase,
            canonical_source_phrase,
            is_parent_market,
            intent,
            recipient,
            profession,
            interest,
            occasion,
            holiday,
            lifestyle,
            theme,
            product_count,
            keyword_count,
            best_rank,
            p25_rank,
            median_rank,
            round(average_rank, 2) AS average_rank,
            active_months,
            trend
        FROM composite_metric_frame
        ORDER BY demand_id
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE composite_id_map AS
        SELECT parent_cluster_key, demand_id
        FROM composite_metric_frame
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE composite_clustered_evidence_stage AS
        SELECT *
        FROM composite_clustered_evidence_frame
        """
    )
    connection.execute(
        f"""
        CREATE TABLE {PARENT_LABEL_AUDIT_TABLE} AS
        SELECT
            old_parent,
            new_parent,
            canonical_source_phrase,
            parent_entity_type,
            is_parent_market,
            reason,
            evidence_phrase,
            cluster_size
        FROM parent_label_audit_frame
        ORDER BY old_parent, new_parent, evidence_phrase
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {COMPOSITE_DEMANDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", COMPOSITE_DEMANDS_TABLE, f"{row_count:,}")
    audit_count = connection.execute(f"SELECT count(*) FROM {PARENT_LABEL_AUDIT_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", PARENT_LABEL_AUDIT_TABLE, f"{audit_count:,}")
    return metrics


def build_composite_keywords(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", COMPOSITE_KEYWORDS_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {COMPOSITE_KEYWORDS_TABLE} AS
        SELECT
            id_map.demand_id,
            evidence.raw_keyword,
            evidence.normalized_keyword,
            evidence.month,
            evidence.search_frequency_rank
        FROM composite_clustered_evidence_stage AS evidence
        JOIN composite_id_map AS id_map
          ON evidence.parent_cluster_key = id_map.parent_cluster_key
        ORDER BY
            id_map.demand_id,
            evidence.search_frequency_rank ASC NULLS LAST,
            evidence.month,
            evidence.normalized_keyword
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {COMPOSITE_KEYWORDS_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", COMPOSITE_KEYWORDS_TABLE, f"{row_count:,}")
    return int(row_count)


def build_demand_strength_v3(connection: duckdb.DuckDBPyConnection) -> int:
    logger.info("Building %s", DEMAND_STRENGTH_V3_TABLE)
    connection.execute(
        f"""
        CREATE TABLE {DEMAND_STRENGTH_V3_TABLE} AS
        WITH max_rank AS (
            SELECT greatest(coalesce(max(search_frequency_rank), 1), 2) AS value
            FROM composite_clustered_evidence_stage
        ),
        scored AS (
            SELECT
                demands.*,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(demands.best_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS best_rank_score,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(demands.p25_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS p25_rank_score,
                least(
                    100.0,
                    greatest(
                        0.0,
                        100.0
                        * (
                            1.0
                            - (
                                ln(greatest(CAST(demands.median_rank AS DOUBLE), 1.0))
                                / ln(CAST(max_rank.value AS DOUBLE))
                            )
                        )
                    )
                ) AS median_rank_score,
                least(100.0, demands.active_months * 25.0) AS active_month_score
            FROM {COMPOSITE_DEMANDS_TABLE} AS demands
            CROSS JOIN max_rank
        )
        SELECT
            demand_id,
            demand_name,
            parent_entity_type,
            parent_label_source,
            canonical_evidence_phrase,
            canonical_source_phrase,
            is_parent_market,
            intent,
            recipient,
            profession,
            interest,
            occasion,
            holiday,
            lifestyle,
            theme,
            product_count,
            keyword_count,
            best_rank,
            p25_rank,
            median_rank,
            average_rank,
            active_months,
            trend,
            round(
                (best_rank_score * 0.45)
                + (p25_rank_score * 0.30)
                + (median_rank_score * 0.15)
                + (active_month_score * 0.10),
                2
            ) AS strength_score
        FROM scored
        ORDER BY
            strength_score DESC,
            best_rank ASC NULLS LAST,
            p25_rank ASC NULLS LAST,
            demand_id
        """
    )
    row_count = connection.execute(f"SELECT count(*) FROM {DEMAND_STRENGTH_V3_TABLE}").fetchone()[0]
    logger.info("Built %s with %s rows", DEMAND_STRENGTH_V3_TABLE, f"{row_count:,}")
    return int(row_count)


def export_query_to_csv(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    output_path: Path,
    chunk_size: int = 100_000,
) -> int:
    cursor = connection.execute(query)
    columns = [description[0] for description in cursor.description]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    write_header = True
    while True:
        frame = cursor.fetch_df_chunk(chunk_size)
        if frame.empty:
            break
        frame.to_csv(
            output_path,
            mode="w" if write_header else "a",
            header=write_header,
            index=False,
        )
        total_rows += len(frame)
        write_header = False

    if write_header:
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)

    return total_rows


def export_reports(connection: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    logger.info("Exporting Composite Demand CSVs to %s", display_path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "composite_demands.csv": f"SELECT * FROM {COMPOSITE_DEMANDS_TABLE} ORDER BY demand_id",
        "composite_keywords.csv": f"""
            SELECT *
            FROM {COMPOSITE_KEYWORDS_TABLE}
            ORDER BY demand_id, search_frequency_rank ASC NULLS LAST, month, normalized_keyword
        """,
        "top_composite_demands.csv": f"""
            SELECT *
            FROM {DEMAND_STRENGTH_V3_TABLE}
            ORDER BY
                strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
        "demand_strength_v3.csv": f"""
            SELECT *
            FROM {DEMAND_STRENGTH_V3_TABLE}
            ORDER BY
                strength_score DESC,
                best_rank ASC NULLS LAST,
                p25_rank ASC NULLS LAST,
                demand_id
        """,
        "parent_label_audit.csv": f"""
            SELECT
                old_parent,
                new_parent,
                canonical_source_phrase,
                parent_entity_type,
                is_parent_market,
                reason,
                evidence_phrase,
                cluster_size
            FROM {PARENT_LABEL_AUDIT_TABLE}
            ORDER BY old_parent, new_parent, evidence_phrase
        """,
    }

    for file_name, query in exports.items():
        row_count = export_query_to_csv(connection, query, output_dir / file_name)
        logger.info("Exported %s with %s rows", file_name, f"{row_count:,}")


def log_summary(connection: duckdb.DuckDBPyConnection) -> None:
    logger.info("Composite Demand summary")
    for table_name in [
        COMPOSITE_DEMANDS_TABLE,
        COMPOSITE_KEYWORDS_TABLE,
        DEMAND_STRENGTH_V3_TABLE,
        PARENT_LABEL_AUDIT_TABLE,
    ]:
        row_count = connection.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]
        logger.info("  %s: %s rows", table_name, f"{row_count:,}")

    logger.info("Top composite demands:")
    for row in connection.execute(
        f"""
        SELECT demand_id, demand_name, best_rank, p25_rank, median_rank, active_months, strength_score, trend
        FROM {DEMAND_STRENGTH_V3_TABLE}
        ORDER BY strength_score DESC, best_rank ASC NULLS LAST
        LIMIT 10
        """
    ).fetchall():
        logger.info(
            "  %s | %s | best=%s | p25=%s | median=%s | active=%s | strength=%s | %s",
            row[0],
            row[1],
            row[2],
            round(float(row[3]), 2) if row[3] is not None else None,
            round(float(row[4]), 2) if row[4] is not None else None,
            row[5],
            row[6],
            row[7],
        )


def build_composite_demand_layer(database_path: Path, output_dir: Path, rebuild: bool) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path)) as connection:
        validate_inputs(connection)
        log_input_counts(connection)
        ensure_rebuild_allowed(connection, rebuild)
        if rebuild:
            drop_output_tables(connection)

        create_composite_evidence_stage(connection)
        build_composite_demands(connection)
        build_composite_keywords(connection)
        build_demand_strength_v3(connection)
        export_reports(connection, output_dir)
        log_summary(connection)


def main() -> None:
    configure_logging()
    args = parse_args()
    logger.info("Starting Composite Demand build")
    build_composite_demand_layer(
        database_path=args.database.resolve(),
        output_dir=args.output_dir.resolve(),
        rebuild=args.rebuild,
    )
    logger.info("Composite Demand build complete")
    logger.info("Build log: %s", display_path(LOG_PATH))


if __name__ == "__main__":
    main()
