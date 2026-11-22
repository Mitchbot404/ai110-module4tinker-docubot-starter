"""Save real, bounded comparisons. Run explicitly: python compare_modes.py.

Makes up to 12 Gemini calls; stops on any API error. No automatic retries here.
Existing results are preserved so interrupted runs can resume.
"""
import json
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
from docubot import DocuBot
from llm_client import GeminiClient, GEMINI_MODEL_NAME

QUERIES = [
    'Where is the auth token generated?',
    'How do I connect to the database?',
    'Which endpoint returns all users?',
    'How does a client refresh an access token?',
    'How do I configure payment processing?',
    'How do I renew my credentials?',
]

def main():
    load_dotenv()
    bot = DocuBot(llm_client=GeminiClient())
    path = Path('comparison_results.json')
    results = json.loads(path.read_text(encoding='utf8')) if path.exists() else []
    for query in QUERIES:
        if any(row['query'] == query for row in results):
            continue
        row = {'query': query, 'model': GEMINI_MODEL_NAME,
               'naive_context': 'full corpus',
               'retrieval': bot.answer_retrieval_only(query)}
        for mode in ('naive', 'rag'):
            answer = (bot.llm_client.naive_answer_over_full_docs(query, bot.full_corpus_text())
                      if mode == 'naive' else bot.answer_rag(query))
            if answer.startswith(('Unable to generate', 'API error')):
                # Avoid writing raw exceptions that could include request details.
                print('Stopped: Gemini request failed. Completed rows preserved.', flush=True)
                return
            row[mode] = answer
            print(f'{mode}: completed {query}', flush=True)
            time.sleep(13)
        results.append(row)
        path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf8')

if __name__ == '__main__':
    if '--starter-baseline' in sys.argv:
        # Reproduce the original starter prompt, which ignored all_text.
        load_dotenv()
        client = GeminiClient()
        query = QUERIES[0]
        response = client.client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=f'You are a documentation assistant.\nAnswer this developer question: {query}',
        )
        Path('starter_baseline.json').write_text(json.dumps({
            'query': query, 'model': GEMINI_MODEL_NAME,
            'context': 'none; original starter prompt',
            'answer': response.text,
        }, indent=2), encoding='utf8')
        print('Saved original-starter baseline.')
    else:
        main()
