
# 🧠 SCM Product Master Data Cleaning using GenAI

An AI-assisted **Supply Chain Management (SCM) product master data cleaning pipeline** built with **Python, Pandas, and OpenAI API**.

The project transforms messy and inconsistent product names into standardized structured fields:

- `main_product`
- `product_type`
- `SKU`

It combines traditional Python data-processing techniques with Generative AI to automate product-name standardization and reduce repetitive manual data-cleaning work.

---

## 📌 Project Overview

Product master data in retail and supply-chain systems often contains inconsistent naming conventions, spelling mistakes, mixed casing, unnecessary spaces, and SKU information embedded inside product names.

For example:

```text
Oyester Mashroom
Parle-G Gold Biscuits -10 RS
Lays Classic 50g
P BINGO CHIPS MRP 105
```

The pipeline converts these unstructured names into structured information.

### Example

**Input**

```text
Parle-G Gold Biscuits -10 RS
```

**Output**

```json
{
  "main_product": "Parle-G",
  "product_type": "Gold Biscuits",
  "SKU": "10 RS"
}
```

---

# 🚀 Problem Statement

The raw product master data can contain:

- Inconsistent product naming
- Spelling mistakes
- Mixed uppercase/lowercase text
- Random or duplicate spaces
- Brand and product variants combined together
- Weight information such as `50g`, `1kg`
- Volume information such as `500ml`, `1L`
- Quantity information such as `6PCS`
- Price information such as `Rs.10` or `MRP 105`

Manual standardization of a large product master is:

- Time-consuming
- Repetitive
- Difficult to maintain consistently
- Not efficient for large datasets

This project automates the process using an AI-assisted ETL workflow.

---

# 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Pipeline development |
| Pandas | CSV processing and data manipulation |
| OpenAI API | AI-based product extraction |
| GPT-4o | Product-name analysis |
| JSON | Structured AI responses |
| Regex | SKU pattern detection |
| tqdm | Progress tracking |
| python-dotenv | Secure API-key configuration |
| Logging | Error and execution tracking |

---

# 🏗️ Project Architecture

```text
                 Raw Product CSV
                        │
                        ▼
              ┌──────────────────┐
              │  Load & Validate │
              │      Data        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Input Normalizer │
              │ spaces / blanks  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   SKU Pattern    │
              │    Detection     │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Cache Lookup   │
              └──────┬─────┬─────┘
                     │     │
                Found│     │Not Found
                     │     ▼
                     │  ┌──────────────┐
                     │  │  OpenAI API  │
                     │  │   GPT-4o     │
                     │  └──────┬───────┘
                     │         │
                     │         ▼
                     │  ┌──────────────┐
                     │  │ JSON Parsing │
                     │  │ & Validation │
                     │  └──────┬───────┘
                     │         │
                     └────┬────┘
                          ▼
                 ┌──────────────────┐
                 │ Incremental CSV │
                 │     Saving      │
                 └────────┬─────────┘
                          │
                          ▼
                  Cleaned Product
                       Master
```

---

# 🔄 ETL Workflow

## 1. Extract

The pipeline reads the raw product master CSV using Pandas.

It validates:

- File availability
- Required product-name column
- Empty or invalid product values

---

## 2. Transform

Each product name goes through multiple processing stages.

### Input Normalization

The pipeline cleans basic formatting before sending the product to the AI:

```text
"  Lays     Classic   50g  "
```

becomes:

```text
"Lays Classic 50g"
```

---

### SKU Pattern Detection

A preprocessing layer identifies likely SKU information using regular expressions.

Examples:

```text
50g
100 gm
1kg
500ml
6PCS
Rs.10
10 RS
MRP 105
```

The detected value is provided to the AI as an additional hint.

---

### Generative AI Processing

The OpenAI API analyzes the complete product name and determines:

```text
main_product
product_type
SKU
```

The model is instructed to correct obvious spelling mistakes while avoiding unsupported product information.

---

## 3. Load

Cleaned records are written incrementally to a CSV file.

Instead of waiting for the entire dataset to finish, the pipeline saves records in batches.

Default batch size:

```python
BATCH_SIZE = 50
```

This reduces the risk of losing already processed data if the process is interrupted.

---

# 🧠 Prompt Engineering

The project uses a structured system prompt that defines:

- Field definitions
- Product identification rules
- SKU identification rules
- Spelling correction
- Normalization requirements
- Edge-case handling
- Examples

The AI follows a logical sequence:

```text
Identify SKU
     ↓
Identify main product
     ↓
Identify product type
     ↓
Normalize spelling/casing
     ↓
Return JSON
```

---

# 📦 Example Transformations

### Example 1

**Input**

```text
Oyester Mashroom
```

**Output**

```json
{
  "main_product": "Oyster Mushroom",
  "product_type": "",
  "SKU": ""
}
```

---

### Example 2

**Input**

```text
Dyna Rose -50 gm
```

**Output**

```json
{
  "main_product": "Dyna",
  "product_type": "Rose",
  "SKU": "50 gm"
}
```

---

### Example 3

**Input**

```text
Lays Classic 50g
```

**Output**

```json
{
  "main_product": "Lays",
  "product_type": "Classic",
  "SKU": "50g"
}
```

---

### Example 4

**Input**

```text
P BINGO CHIPS MRP 105
```

**Output**

```json
{
  "main_product": "P BINGO",
  "product_type": "CHIPS",
  "SKU": "MRP 105"
}
```

---

### Example 5

**Input**

```text
Phynail
```

**Output**

```json
{
  "main_product": "Phenyl",
  "product_type": "",
  "SKU": ""
}
```

---

# ⚡ Key Features

### 1. AI-Based Product Cleaning

Uses Generative AI to understand messy product descriptions instead of relying only on fixed rules.

### 2. Structured JSON Output

The API response is requested in JSON format:

```json
{
  "main_product": "",
  "product_type": "",
  "SKU": ""
}
```

### 3. SKU Detection

A regex preprocessing layer provides hints for common:

- Weight
- Volume
- Quantity
- Price
- MRP

patterns.

### 4. Duplicate Processing Cache

Processed product names are stored locally in:

```text
product_cleaning_cache.json
```

If the same product appears again, the cached result can be reused instead of making another API request.

This can reduce unnecessary API usage for datasets containing repeated product names.

### 5. Retry Mechanism

Temporary API failures are handled through multiple attempts.

The retry delay increases between attempts:

```text
Attempt 1
   ↓
Wait
   ↓
Attempt 2
   ↓
Wait longer
   ↓
Attempt 3
```

### 6. Resume Capability

If processing stops before completion, the pipeline checks the existing output file and continues from the previously processed position.

### 7. Incremental Saving

Results are written in batches rather than keeping the entire processed dataset in memory.

### 8. Logging

Pipeline events and errors are recorded in:

```text
product_cleaning.log
```

### 9. Processing Summary

At completion, the script reports:

```text
Processed rows
Cache hits
API calls
API errors
Output file
Cache file
Log file
```

---

# 📁 Project Structure

```text
SCM-Product-Master-GenAI/
│
├── SCM_Product_Master_GenAI_Cleaner_v2.py
├── README.md
│
├── product_cleaning_cache.json
├── product_cleaning.log
│
├── ProductList_master_cleaned_v2.csv
│
└── data/
    └── Product List - Miri product master product list.csv
```

> Input data, generated output files, cache files, and API keys should generally not be committed to a public GitHub repository if they contain private or sensitive information.

---

# ⚙️ Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd SCM-Product-Master-GenAI
```

Install dependencies:

```bash
pip install pandas openai python-dotenv tqdm
```

---

# 🔐 API Key Configuration

The project reads the OpenAI API key from an environment variable.

### Linux / macOS

```bash
export OPENAI_API_KEY="your-api-key"
```

### Windows PowerShell

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

### Using `.env`

Create a file named:

```text
.env
```

Add:

```text
OPENAI_API_KEY=your-api-key
```

Do **not** upload your `.env` file or API key to GitHub.

Add this to `.gitignore`:

```text
.env
*.log
product_cleaning_cache.json
ProductList_master_cleaned_v2.csv
```

---

# ▶️ Running the Project

Update the input configuration if required:

```python
INPUT_FILE = Path(
    "/content/Product List - Miri product master product list.csv"
)

PRODUCT_COLUMN = "ProductName"
```

Then run:

```bash
python SCM_Product_Master_GenAI_Cleaner_v2.py
```

The cleaned output will be generated as:

```text
ProductList_master_cleaned_v2.csv
```

---

# 📊 Output Structure

The original columns from the source CSV are preserved.

Three additional columns are added:

```text
main_product
product_type
SKU
```

Example:

| ProductName | main_product | product_type | SKU |
|---|---|---|---|
| Lays Classic 50g | Lays | Classic | 50g |
| Dyna Rose -50 gm | Dyna | Rose | 50 gm |
| Phynail | Phenyl | | |
| Airtel - 10 | Airtel | | 10 |

---

# 🔁 Resume-Safe Processing

The pipeline checks whether the output file already exists.

For example:

```text
Source rows:       10,000
Already processed: 4,000
Remaining:         6,000
```

The pipeline can continue from the existing output position instead of starting from zero.

---

# 💾 Caching Strategy

The cache uses the original normalized product name as the lookup key.

Example:

```json
{
  "Lays Classic 50g": {
    "main_product": "Lays",
    "product_type": "Classic",
    "SKU": "50g"
  }
}
```

If the same normalized product name appears again, the stored result can be reused.

---

# 🛡️ Error Handling

The pipeline handles several common failure scenarios:

- Missing input file
- Missing product column
- Empty product values
- Invalid JSON response
- API errors
- Temporary API failures
- Interrupted processing
- Existing output files
- Invalid cache files

Failed API records are marked separately instead of silently being treated as successful results.

---

# 📈 Business Use Case

This type of product standardization can be useful in SCM and retail analytics workflows.

Clean product master data can support:

- Product-level reporting
- SKU-level analysis
- Inventory reporting
- Sales analysis
- SCM dashboards
- Product grouping
- Data-quality improvement

For example, inconsistent records such as:

```text
Oyester Mashroom
Oyster Mushroom
OYESTER MUSHROOM
```

can be standardized into a more consistent representation for downstream analysis.

---

# 🎯 Skills Demonstrated

This project demonstrates practical experience with:

- Python
- Pandas
- ETL pipeline development
- Data cleaning
- Data standardization
- Generative AI
- OpenAI API integration
- Prompt engineering
- JSON parsing
- Regular expressions
- API error handling
- Retry strategies
- Caching
- Incremental processing
- Resume-safe workflows
- Logging
- Supply Chain analytics

---

# 🔮 Possible Future Improvements

Potential extensions include:

- Batch API processing
- Asynchronous API requests
- Human-review queue for ambiguous products
- Product-category classification
- Brand extraction
- Duplicate-product detection
- Data-quality scoring
- Database integration
- Power BI dashboard for cleaned product data
- Automated quality reports
- Configurable SKU rules
- Confidence/validation scoring

---

# 👨‍💻 Project Objective

The objective of this project is to demonstrate how **Generative AI can be integrated into a practical Python ETL workflow** to solve a real-world data-cleaning problem.

Rather than using AI only for text generation, the project applies it to **structured data transformation and Supply Chain product-master standardization**.

---

## 📌 Project Summary

**Raw SCM Product Data → Python Preprocessing → SKU Detection → OpenAI GPT-4o → JSON Validation → Caching → Incremental CSV → Clean Product Master**

This workflow demonstrates the combination of **Data Analytics, Python automation, ETL concepts, and Generative AI** in a practical business-data use case.