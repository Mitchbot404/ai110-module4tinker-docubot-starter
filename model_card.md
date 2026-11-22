# DocuBot Model Card

Experiment date: November 22, 2026. Model: `gemini-3.5-flash-lite`.
This report describes observed runs, with AI-assisted implementation and analysis.
The student should review the source documents, results, and design decisions
before submitting; this is not a claim that independent student review occurred.

## 1. System Overview

DocuBot answers developer questions from four local Markdown documents. Its goal
is to make project answers traceable to evidence and refuse unsupported questions.
Inputs are a question, the `docs/` files, and a Gemini API key for generation modes.
Outputs are either raw sourced snippets, generated text, or a refusal.

The documentation describes a sample application, not a backend implemented in
this repository. It covers token generation, routes, database configuration,
tables, and setup. It does not describe payments, JWT signing algorithms, or
password-reset implementation. The documents themselves can conflict: AUTH.md
says to refresh expired tokens, while API_REFERENCE.md requires an existing valid
token. Retrieval cannot establish which statement matches a real implementation.

## 2. Retrieval Design

1. Normalize words using lowercase alphanumeric tokens, remove common filler
   words, and map a small explicit set of aliases (auth/authentication,
   connect/connection, generated/generation, and a few plurals).
2. Build an inverted index from normalized words to filenames.
3. Use that index to select candidate documents. Split those documents at
   Markdown headings, keeping each heading with its paragraphs, examples, and lists.
4. Score each section by distinct query-word overlap. Require at least two
   distinct matches (one for a one-word query), and coverage of at least half the
   meaningful query terms. Add 0.5 per matching heading term to the ranking.
5. Return the top three sections, with deterministic filename/text tie-breaking.

The design is simple Python with no embedding service or vector database. The
heading rule preserves endpoint details better than splitting every paragraph.
The filter is a heuristic: lexical overlap does not prove that a section answers
the question. A 50% threshold allows some phrasing variation but also false matches.
This decision needs student review; stricter filtering would reject more useful
questions, while looser filtering would admit more irrelevant text.

The full corpus contains 11,722 characters. Supported sample questions retrieve
913-1,463 characters across up to three snippets. A token-generation question
retrieves 1,000 characters; the database-connection question retrieves 960.
Introduction sections can still waste part of that context budget.

## 3. Use of Gemini

- Naive: sends the entire corpus and question, without retrieval or the strict
  RAG refusal instructions.
- Retrieval only: returns source text without calling Gemini.
- RAG: retrieves first, refuses immediately on no useful matches, and otherwise
  asks Gemini to use only snippets, avoid invented details, refuse insufficient
  evidence, and identify source files.

The original starter's naive method ignored `all_text`, despite the README and
assignment describing full-corpus input. That mismatch was corrected. A separate
`starter_baseline.json` records the original no-context prompt behavior; it must
not be confused with the corrected naive mode in the six-question comparison.

An initial attempt with Gemini 2.5 Flash-Lite returned a 404 stating that it was
unavailable to new users. The completed comparisons use 3.5 Flash-Lite, which
Google lists with free-tier text input/output. No billing setup was changed.
Source: https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite

## 4. Experiments and Comparisons

Exact questions, retrieved text, and actual Gemini outputs are saved in
`comparison_results.json`. All three modes used identical wording per row.

| Question | Naive: full docs | Retrieval only | RAG |
| --- | --- | --- | --- |
| Where is the auth token generated? | Correctly names generate_access_token in auth_utils.py. | Token Generation section is first; also returns introductory/configuration text. | Correct answer and AUTH.md citation. |
| How do I connect to the database? | Explains DATABASE_URL and supplies SQLite/PostgreSQL examples. | Returns connection configuration and surrounding database context; user must extract instructions. | Concise explanation with DATABASE.md citation, but omits concrete connection-string examples. |
| Which endpoint returns all users? | Correct GET /api/users, including admin and token requirements. | Exact endpoint section plus a database helper section; raw examples are less direct. | Correct endpoint and citation, but omits the admin restriction. |
| How does a client refresh an access token? | Gives POST /api/refresh, bearer header, and response. | Returns workflow, endpoint, and validation text. | Combines endpoint and header evidence with AUTH.md and API_REFERENCE.md citations. |
| How do I configure payment processing? | Correctly says payment configuration is not documented. | Refuses; no relevant snippets. | Refuses before making an LLM call. |
| How do I renew my credentials? | Assumes credentials means access token and gives refresh instructions; helpful only if that interpretation is right. | Refuses because the remaining words do not meet the overlap threshold. | Same pre-generation refusal. |

The corrected full-corpus baseline performed well on the clear supported questions.
The experiment does not support claiming that naive generation always hallucinates
or that RAG is always more complete. RAG's benefit here is smaller, explicit evidence
and source attribution. The users-endpoint result shows that summarization can
still lose an important qualification.

The naive credentials answer illustrates a weakly grounded interpretation: the
docs support refreshing a token, but the question does not establish whether the
user means a token or a password. It confidently selects the token meaning rather
than clarifying. No clear invented project fact was observed in the six corrected
naive outputs. The original no-context starter baseline also asked for project
details rather than fabricating a function name. These outcomes are reported
honestly even though the activity anticipates examples of confident guessing.

The starter evaluation reports 0.875 (displayed as 0.88): seven source hits out of
eight queries. Its payment query has no expected source and is counted as a miss,
even though refusing it is desirable. Thus all seven supported sample questions
had a source hit and the unrelated payment query was refused. This is a file-hit
check, not an answer-accuracy score. The generic `users` expectation also overlaps
`users table`, making that check permissive. Raw output: `retrieval_evaluation.txt`.

## 5. Failure Cases and Guardrails

1. **Omitted access restriction:** for 'Which endpoint returns all users?', RAG
   returned GET /api/users but omitted that only admins may use it. The retrieved
   source included that restriction. A more useful answer should retain it.
2. **False refusal on synonyms:** 'Where is the JWT minted?' returns 'I do not
   know based on these docs.' in both retrieval and RAG. AUTH.md actually names
   the token-generation function and calls its output a JSON Web Token. The
   current aliases do not map JWT/minted to those terms. Recorded in
   `failure_case.json`; the RAG refusal was tested without calling Gemini.
3. **Related text without an answer:** 'How do I encrypt the database connection?'
   passes the retrieval threshold on database/connection and returns configuration
   text, although encryption setup is absent. This was observed in retrieval only;
   no claim is made about a Gemini response to this question. Ideally retrieval
   would detect insufficient evidence or the downstream model would refuse.

DocuBot should refuse for missing topics (payment processing), or when matching
text does not establish the requested fact (database transport encryption or JWT
signing algorithm). It should also refuse empty inputs and filler-only questions.
The implemented guardrails reject weak overlap and empty results, cap the snippet
count, and ask Gemini to avoid unsupported claims. Tests verify that an unrelated
question is refused before Gemini is called. These checks do not guarantee factuality.

## 6. Limitations and Future Improvements

Current limitations:
- Word matching misses unseen synonyms and abbreviations.
- Related keywords can pass the filter without answering the question.
- Sections vary in size; headings inside unindented code fences could split text.
- RAG can omit important restrictions or repeat contradictions from the source.
- The small evaluation set and one generation per question do not measure broad
  reliability, variability, or resistance to malicious document instructions.

Useful next improvements:
- Expand aliases based on a separate test set, then measure false refusals as well
  as false matches instead of tuning only on demonstration questions.
- Improve ranking and section context so introductions and adjacent-but-unhelpful
  sections do not crowd out precise evidence.
- Check answers for required qualifiers and surface conflicting source statements.

Validation: six offline unit tests passed, the CLI started successfully with the
local key, and six three-mode comparisons completed. Generated responses are
nondeterministic; a later run may differ.

## 7. Responsible Use

Careless use could lead developers to implement wrong authentication behavior,
miss access restrictions, or copy sample settings into a real deployment. Source
citations make inspection easier but do not certify that documentation is current.

- Inspect the cited section and real project code before acting on an answer.
- Treat example values as examples, and never commit API keys or other secrets.
- Investigate contradictions and missing evidence rather than filling gaps by guesswork.
- Review this implementation and its guardrail choices before submitting the assignment.
