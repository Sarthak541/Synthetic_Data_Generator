# Staging Table Creator & Data Generator for PAS

This project reads DDL definitions from an Excel file, creates staging tables in a PostgreSQL database, and populates them with synthetic life insurance data generated using a locally running LLM (`gemma3` via OpenAI-compatible API).

---

## Features

- Parses DDL from Excel sheets
- Generates PostgreSQL `CREATE TABLE` statements
- Creates tables dynamically in the database
- Uses `gemma3` model to generate realistic JSON records
- Handles `NOT NULL` fields with fallback values
- Inserts generated records into the appropriate table

---

## Requirements

- Python 3.8+
- PostgreSQL instance (local or remote)
- Local LLM endpoint (e.g., [Ollama](https://ollama.com/) with `gemma3` model)
- Python packages:

```bash
pip install pandas openai sqlalchemy psycopg2
```

## Configuration

- Excel File Path: Update the path to your Excel file in the script:
```bash
EXCEL_FILE_PATH = "DDL_File.xlsx"
```
- PostgreSQL Connection String:  Change to your own username, password, and database name
```bash
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/exampleDatabase"
```
- LLM Client (OpenAI-compatible): Change the model/api key to your own setup.  For this setup ollama is being used to run an llm locally, so there is no api-key.
```bash
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy-key"
)
```

## LLM Prompt Format
Here is the prompt to generate data with the synthetic data generator.  Can be changed to suit different use cases.
```bash
You are a data generator specializing in Life and Annuity insurance data...
Generate ONLY a valid JSON object...
Ensure all data is present for each column...
```

## License
This project is for testing and skill development purpose. Not intended for production use.
