"""
SCM Product Master Cleaner
--------------------------
AI-assisted product-name standardization using Python, Pandas and OpenAI.

Pipeline:
    Raw CSV
      -> input normalization
      -> SKU pattern detection
      -> OpenAI structured extraction
      -> result validation
      -> local cache
      -> incremental CSV output
      -> processing summary

Install:
    pip install pandas openai python-dotenv tqdm

Set your API key:
    Linux/macOS:
        export OPENAI_API_KEY="your-key"

    Windows PowerShell:
        $env:OPENAI_API_KEY="your-key"

Optional .env:
    OPENAI_API_KEY=your-key
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm


# ============================================================
# 1. PROJECT SETTINGS
# ============================================================

load_dotenv()

INPUT_FILE = Path("/content/Product List - Miri product master product list.csv")
OUTPUT_FILE = Path("ProductList_master_cleaned_v2.csv")
CACHE_FILE = Path("product_cleaning_cache.json")
LOG_FILE = Path("product_cleaning.log")

PRODUCT_COLUMN = "ProductName"

MODEL_NAME = "gpt-4o"
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 3

OUTPUT_FIELDS = ["main_product", "product_type", "SKU"]


# ============================================================
# 2. LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("scm_cleaner")


# ============================================================
# 3. OPENAI CLIENT
# ============================================================

def create_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY was not found. "
            "Set it as an environment variable or in a .env file."
        )

    return OpenAI(api_key=api_key)


client = create_client()


# ============================================================
# 4. AI INSTRUCTIONS
# ============================================================

SYSTEM_PROMPT = """
You are a product-master-data standardization specialist.

You receive ONE raw product name from a Supply Chain / retail product
master. Convert it into exactly three fields:

{
  "main_product": "",
  "product_type": "",
  "SKU": ""
}

OBJECTIVE
---------
Turn the raw product name into a useful, human-readable and standardized
product representation.

FIELD DEFINITIONS
-----------------

1. main_product
   The primary identity of the product.

   Keep brand/product identity together when that is how the product is
   naturally identified.

2. product_type
   The descriptive variant, category, flavour, form, model, fragrance,
   or other meaningful descriptor that remains after identifying the
   main product.

3. SKU
   Explicit commercial/measurement information such as:
   - weight: 50g, 100 gm, 1kg
   - volume: 500ml, 1L
   - count: 6PCS, 12 pcs
   - price: Rs.10, 10 RS, MRP 105
   - other clear numeric/unit identifiers

DECISION PROCESS
----------------
First identify obvious SKU information.
Then determine the primary product identity.
Then classify the meaningful descriptive remainder as product_type.

NORMALIZATION
-------------
- Correct obvious spelling mistakes.
- Normalize unnecessary whitespace.
- Use natural title casing for ordinary product names.
- Preserve meaningful brand spelling such as Parle-G and P BINGO.
- Do not invent a brand or product detail that is not supported by the
  input.
- Do not put the same descriptive word into product_type unless it adds
  useful classification information.
- If a field cannot reasonably be determined, return "".

IMPORTANT
---------
A product may legitimately have the same conceptual word represented in
main_product and product_type when that makes the product identity clearer.
Use practical human judgment rather than blindly splitting every word.

EXAMPLES
--------
Input: Oyester Mashroom
Output:
{"main_product":"Oyster Mushroom","product_type":"","SKU":""}

Input: Parle-G Gold Biscuits -10 RS
Output:
{"main_product":"Parle-G","product_type":"Gold Biscuits","SKU":"10 RS"}

Input: Dyna Rose -50 gm
Output:
{"main_product":"Dyna","product_type":"Rose","SKU":"50 gm"}

Input: Honey And Turmeric Soap
Output:
{"main_product":"Honey And Turmeric Soap","product_type":"Soap","SKU":""}

Input: Spicy Chilli
Output:
{"main_product":"Spicy Chilli","product_type":"","SKU":""}

Input: Banana Chips 50g
Output:
{"main_product":"Banana Chips","product_type":"Chips","SKU":"50g"}

Input: Breeze Sandle Sparsh
Output:
{"main_product":"Breeze","product_type":"Sandal Sparsh","SKU":""}

Input: Lays Classic 50g
Output:
{"main_product":"Lays","product_type":"Classic","SKU":"50g"}

Input: Super Garam Masala Jeet - Rs.1
Output:
{"main_product":"Super Garam Masala","product_type":"Jeet","SKU":"Rs.1"}

Input: Phynail
Output:
{"main_product":"Phenyl","product_type":"","SKU":""}

Input: Airtel - 10
Output:
{"main_product":"Airtel","product_type":"","SKU":"10"}

Input: P BINGO CHIPS MRP 105
Output:
{"main_product":"P BINGO","product_type":"CHIPS","SKU":"MRP 105"}

Input: CEAM BON(6PCS)RKS
Output:
{"main_product":"CEAM BON","product_type":"","SKU":"6PCS"}

Input: Flattened Rice
Output:
{"main_product":"Flattened Rice","product_type":"Rice","SKU":""}

Return JSON only.
"""


# ============================================================
# 5. BASIC TEXT NORMALIZATION
# ============================================================

def normalize_input(value: Any) -> str:
    """Prepare a raw CSV value without changing its business meaning."""
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


# ============================================================
# 6. SKU HINT EXTRACTION
# ============================================================

SKU_PATTERN = re.compile(
    r"""
    (?ix)
    (
        \b(?:mrp|rs|rs\.)\s*\.?\s*\d+(?:\.\d+)?\b
        |
        \b\d+(?:\.\d+)?\s*(?:rs|pcs?|pc|kg|kgs|g|gm|gms|gram|grams|
        mg|ml|ltr|litre|litres|l|w)\b
        |
        \(\s*\d+\s*(?:pcs?|pc)\s*\)
        |
        \b\d+(?:\.\d+)?\s*rs\b
    )
    """,
)


def detect_sku_hint(text: str) -> str:
    """
    Detect likely SKU/measurement tokens before the AI call.
    This is only a hint; the AI remains responsible for final classification.
    """
    matches = SKU_PATTERN.findall(text)

    if not matches:
        return ""

    return matches[-1].strip()


# ============================================================
# 7. CACHE HANDLING
# ============================================================

def load_cache() -> dict[str, dict[str, str]]:
    if not CACHE_FILE.exists():
        return {}

    try:
        with CACHE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache could not be loaded: %s", exc)

    return {}


def save_cache(cache: dict[str, dict[str, str]]) -> None:
    temporary_file = CACHE_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)

    temporary_file.replace(CACHE_FILE)


# ============================================================
# 8. RESULT VALIDATION
# ============================================================

def validate_result(result: Any) -> dict[str, str]:
    """
    Make the model response safe for the CSV pipeline.
    Only the three expected fields are retained.
    """
    if not isinstance(result, dict):
        raise ValueError("AI response is not a JSON object.")

    cleaned = {}

    for field in OUTPUT_FIELDS:
        value = result.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            value = str(value)

        cleaned[field] = value.strip()

    return cleaned


# ============================================================
# 9. AI CLEANING
# ============================================================

def clean_product(product_name: str) -> dict[str, str]:
    """
    Send one normalized product name to OpenAI with retry handling.
    """
    sku_hint = detect_sku_hint(product_name)

    user_instruction = (
        f"Raw product name:\n{product_name}\n\n"
        f"Possible SKU hint detected by the preprocessing layer: "
        f"{sku_hint or 'none'}\n\n"
        "Analyze the original product name and return the final JSON."
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_instruction},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("Empty response returned by API.")

            parsed = json.loads(content)
            return validate_result(parsed)

        except Exception as exc:
            logger.warning(
                "Attempt %s/%s failed for '%s': %s",
                attempt,
                MAX_RETRIES,
                product_name,
                exc,
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                logger.error(
                    "Final failure for product '%s': %s",
                    product_name,
                    exc,
                )

    return {
        "main_product": "API_ERROR",
        "product_type": "",
        "SKU": "",
    }


# ============================================================
# 10. FILE / RESUME HELPERS
# ============================================================

def load_source_data() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(INPUT_FILE)

    if PRODUCT_COLUMN not in dataframe.columns:
        raise KeyError(
            f"Column '{PRODUCT_COLUMN}' not found. "
            f"Available columns: {list(dataframe.columns)}"
        )

    return dataframe


def get_resume_position() -> int:
    """
    Resume based on completed output rows.
    The output is written in the same row order as the source.
    """
    if not OUTPUT_FILE.exists():
        return 0

    try:
        existing = pd.read_csv(OUTPUT_FILE)
        return len(existing)

    except pd.errors.EmptyDataError:
        return 0

    except Exception as exc:
        logger.warning(
            "Unable to inspect existing output: %s", exc
        )
        return 0


def initialize_output(columns: list[str]) -> None:
    if OUTPUT_FILE.exists():
        return

    empty = pd.DataFrame(columns=columns)
    empty.to_csv(OUTPUT_FILE, index=False)


# ============================================================
# 11. BATCH WRITING
# ============================================================

def append_batch(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    batch_df = pd.DataFrame(rows)

    batch_df.to_csv(
        OUTPUT_FILE,
        mode="a",
        header=False,
        index=False,
    )


# ============================================================
# 12. MAIN ETL PROCESS
# ============================================================

def run_pipeline() -> None:
    print("=" * 60)
    print("SCM PRODUCT MASTER CLEANING PIPELINE")
    print("=" * 60)

    logger.info("Pipeline started.")

    source_df = load_source_data()

    print(f"Source rows: {len(source_df):,}")

    initialize_output(
        list(source_df.columns) + OUTPUT_FIELDS
    )

    cache = load_cache()
    resume_at = get_resume_position()

    if resume_at > len(source_df):
        print(
            "Output contains more rows than the source. "
            "Please verify the output file before continuing."
        )
        return

    if resume_at == len(source_df):
        print("All source rows are already processed.")
        return

    pending = source_df.iloc[resume_at:].copy()

    print(f"Resume position: {resume_at:,}")
    print(f"Rows remaining: {len(pending):,}")
    print(f"Cached products: {len(cache):,}")
    print("-" * 60)

    current_batch: list[dict[str, Any]] = []
    cache_changed = False

    stats = {
        "processed": 0,
        "cache_hits": 0,
        "api_calls": 0,
        "api_errors": 0,
    }

    for _, row in tqdm(
        pending.iterrows(),
        total=len(pending),
        desc="Cleaning products",
    ):
        raw_value = row[PRODUCT_COLUMN]
        product_name = normalize_input(raw_value)

        if not product_name:
            cleaned = {
                "main_product": "",
                "product_type": "",
                "SKU": "",
            }
        elif product_name in cache:
            cleaned = validate_result(cache[product_name])
            stats["cache_hits"] += 1
        else:
            stats["api_calls"] += 1
            cleaned = clean_product(product_name)

            if cleaned["main_product"] == "API_ERROR":
                stats["api_errors"] += 1
            else:
                cache[product_name] = cleaned
                cache_changed = True

        output_row = row.to_dict()
        output_row.update(cleaned)
        current_batch.append(output_row)

        stats["processed"] += 1

        if len(current_batch) >= BATCH_SIZE:
            append_batch(current_batch)

            if cache_changed:
                save_cache(cache)
                cache_changed = False

            logger.info(
                "Saved batch. Processed=%s, API calls=%s, cache hits=%s",
                stats["processed"],
                stats["api_calls"],
                stats["cache_hits"],
            )

            current_batch.clear()

    # Save final partial batch
    if current_batch:
        append_batch(current_batch)

    if cache_changed:
        save_cache(cache)

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Processed rows : {stats['processed']:,}")
    print(f"Cache hits     : {stats['cache_hits']:,}")
    print(f"API calls      : {stats['api_calls']:,}")
    print(f"API errors     : {stats['api_errors']:,}")
    print(f"Output file    : {OUTPUT_FILE}")
    print(f"Cache file     : {CACHE_FILE}")
    print(f"Log file       : {LOG_FILE}")
    print("=" * 60)

    logger.info("Pipeline completed: %s", stats)


# ============================================================
# 13. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        print("\nProcess stopped by user.")
        logger.info("Pipeline interrupted by user.")
    except Exception as exc:
        print(f"\nPipeline failed: {exc}")
        logger.exception("Pipeline terminated with an error.")
