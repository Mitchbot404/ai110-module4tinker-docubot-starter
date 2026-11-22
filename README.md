# DocuBot

DocuBot is a small documentation assistant that helps answer developer questions about a codebase.  
It can operate in three different modes:

1. **Naive LLM mode**  
   Sends the entire documentation corpus to a Gemini model and asks it to answer the question.

2. **Retrieval only mode**  
   Uses a simple indexing and scoring system to retrieve relevant snippets without calling an LLM.

3. **RAG mode (Retrieval Augmented Generation)**  
   Retrieves relevant snippets, then asks Gemini to answer using only those snippets.

The docs folder contains realistic developer documents (API reference, authentication notes, database notes), but these files are **just text**. They support retrieval experiments and do not require students to set up any backend systems.

---

## Setup

### 1. Install Python dependencies

    pip install -r requirements.txt

### 2. Configure environment variables

Copy the example file:

    cp .env.example .env

Then edit `.env` to include your Gemini API key:

    GEMINI_API_KEY=your_api_key_here

If you do not set a Gemini key, you can still run retrieval only mode.

---

## Running DocuBot

Start the program:

    python main.py

Choose a mode:

- **1**: Naive LLM (Gemini reads the full docs)  
- **2**: Retrieval only (no LLM)  
- **3**: RAG (retrieval + Gemini)

You can use built in sample queries or type your own.

---

## Running Retrieval Evaluation (optional)

    python evaluation.py

This prints simple retrieval hit rates for sample queries.

---

## Modifying the Project

You will primarily work in:

- `docubot.py`  
  Implement or improve the retrieval index, scoring, and snippet selection.

- `llm_client.py`  
  Adjust the prompts and behavior of LLM responses.

- `dataset.py`  
  Add or change sample queries for testing.

---

## Requirements

- Python 3.9+
- A Gemini API key for LLM features (only needed for modes 1 and 3)
- No database, no server setup, no external services besides LLM calls

## This implementation

Retrieval indexes normalized words, searches heading-delimited sections, and
returns up to three snippets. It filters weak matches before RAG calls Gemini.
The simple word-overlap guardrail is a heuristic, not proof that an answer exists.

Naive mode now actually includes the full documentation in its prompt. The
starter implementation accepted `all_text` but ignored it, contradicting this
README and the activity instructions. RAG keeps the starter's evidence-only
prompt and file citations. The model is pinned to `gemini-3.5-flash-lite`:
Google rejected `gemini-2.5-flash-lite` for this new account.

### Windows commands

From the project folder (the local environment is named `venv`):

```powershell
.\venv\Scripts\python.exe main.py
.\venv\Scripts\python.exe -m unittest -v
.\venv\Scripts\python.exe evaluation.py
```

To reproduce the six-question comparison, run:

```powershell
.\venv\Scripts\python.exe compare_modes.py
```

This last command uses the Gemini API. It spaces requests, stops on an API
error, and saves completed comparisons in `comparison_results.json`. Existing
rows are skipped; rename that file if you deliberately want a fresh run.
Review your project's current free-tier eligibility and quotas before rerunning.
Never commit `.env`; it is ignored by Git.

See `model_card.md` for the experiment analysis and limitations.

`python compare_modes.py --starter-baseline` makes one separate API call with
the original starter's no-documentation prompt and saves `starter_baseline.json`.
It is separate from the corrected full-corpus comparisons.
