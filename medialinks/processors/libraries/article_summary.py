from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words


LANGUAGE = "english"


def summarize(url: str, num_sentences = 10, iteration:int = 0) -> str:
    """(attempt to) Summarize an online article"""
    try:
        parser = HtmlParser.from_url(url, Tokenizer(LANGUAGE))
        stemmer = Stemmer(LANGUAGE)

        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(LANGUAGE)
        output = ""
        for sentence in summarizer(parser.document, num_sentences):
            output += f"{sentence}\n\n"
        return output
    except LookupError:
        if iteration > 0:
            raise Exception("nltk not working")
        import nltk
        nltk.download('punkt')
        return summarize(url, num_sentences, iteration+1)

