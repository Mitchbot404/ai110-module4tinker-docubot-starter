"""Offline behavior checks: python -m unittest -v."""
import tempfile
import unittest
from docubot import DocuBot


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.bot = DocuBot()

    def test_supported_answers_include_evidence(self):
        for question, evidence in [
            ('Where is the auth token generated?', 'generate_access_token'),
            ('Which endpoint returns all users?', 'Only accessible to admins'),
            ('How do I connect to the database?', 'DATABASE_URL'),
            ('Which fields are stored in the users table?', 'password_hash'),
        ]:
            with self.subTest(question=question):
                self.assertIn(evidence, self.bot.answer_retrieval_only(question))

    def test_users_section_ranks_first(self):
        snippets = self.bot.retrieve('Which fields are stored in the users table?')
        self.assertTrue(snippets[0][1].startswith('### users'))

    def test_snippets_are_smaller_than_source(self):
        docs = dict(self.bot.documents)
        for filename, snippet in self.bot.retrieve('Where is the auth token generated?'):
            self.assertIn(snippet, docs[filename])
            self.assertLess(len(snippet), len(docs[filename]))

    def test_empty_unrelated_and_stopwords_refuse(self):
        for question in ('', 'the and is', 'How do I configure payment processing?', 'Who won the baseball championship?'):
            self.assertEqual(self.bot.retrieve(question), [])

    def test_limits_and_missing_docs(self):
        self.assertEqual(self.bot.retrieve('token', top_k=0), [])
        self.assertEqual(len(self.bot.retrieve('token', top_k=1)), 1)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(DocuBot(folder).retrieve('token'), [])

    def test_refusal_does_not_call_gemini(self):
        class NoCalls:
            def answer_from_snippets(self, *args):
                raise AssertionError('Refusal must happen before calling Gemini')
        self.bot.llm_client = NoCalls()
        self.assertEqual(self.bot.answer_rag('How do I configure payment processing?'),
                         'I do not know based on these docs.')


if __name__ == '__main__':
    unittest.main()
