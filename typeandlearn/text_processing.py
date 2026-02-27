"""
Text conversion between file formats
"""

import json

import nltk
import pandas as pd
from nltk.tokenize import sent_tokenize

nltk.download("punkt")
nltk.download("punkt_tab")
nltk.download("wordnet")
nltk.download("omw-1.4")
nltk.download("averaged_perceptron_tagger_eng")

def lemmatized_frequency_distribution(text):
    """
    Get the lemmatized frequency distribution of a text
    
    Inputs:
    --------
    text: String, text to be processed
    
    Outputs:
    --------
    freq_dist: DataFrame, lemmatized frequency distribution
    """
    tokens = word_tokenize(text.lower())
    lemmatizer = WordNetLemmatizer()
    tagged_tokens = pos_tag(tokens)

    # todo: use:
    # wordnet.NOUN = 'n'
    # wordnet.VERB = 'v'
    # wordnet.ADJ  = 'a'
    # wordnet.ADV  = 'r'
    def get_wordnet_pos(tag):
        if tag.startswith('J'):
            return 'a'
        elif tag.startswith('V'):
            return 'v'
        elif tag.startswith('N'):
            return 'n'
        elif tag.startswith('R'):
            return 'r'
        else:
            return 'n'

    lemmatized_str = []
    for word, tag in tagged_tokens:
        if word.lower() == 'are' or word.lower() in ['is', 'am']:
            lemmatized_str.append(word)
        else:
            lemmatized_str.append(
                lemmatizer.lemmatize(word, get_wordnet_pos(tag)))
    return pd.DataFrame(nltk.FreqDist(lemmatized_str), columns=['Word', 'Frequency'])

def clean_freq_dist(freq_dist):
    """
    Clean the frequency distribution
    
    Inputs:
    --------
    freq_dist: DataFrame, Frequency distribution
    
    Outputs:
    --------
    freq_dist: DataFrame, Cleaned frequency distribution
    """
    df = freq_dist

    # Drop rows with non letter values
    df = df[df['Word'].str.contains(r'[a-zA-Z]')]

    # Drop rows with to be verbs
    to_be_verbs = ['am', 'is', 'are', 'was', 'were', 'be', 'being', 'been']
    df = df[~df['Word'].isin(to_be_verbs)]

    # Drop rows with prepositions without using regex
    prepositions = ['a', 'an', 'the', 'to', 'of', 'and', 'or', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'into', 'out', 'over', 'up', 'down', 'off', 'about', 'after', 'against', 'along', 'among', 'around', 'as', 'at', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond', 'but', 'by', 'down', 'during', 'except', 'for', 'from', 'in', 'inside', 'into', 'like', 'minus', 'near', 'next', 'of', 'off', 'on', 'onto', 'opposite', 'out', 'outside', 'over', 'past', 'per', 'plus', 'round', 'save', 'since', 'than', 'through', 'throughout', 'till', 'times', 'to', 'toward', 'towards', 'under', 'until', 'up', 'upon', 'via', 'with', 'within', 'without', 'yet']
    df = df[~df['Word'].isin(prepositions)]

    # Drop rows with conjunctions
    conjunctions = ['and', 'or', 'but', 'nor', 'for', 'yet', 'so', 'if', 'while', 'as', 'because', 'since', 'unless', 'once', 'when', 'till', 'unless', 'although', 'whereas', 'whether', 'how', 'although', 'whereas', 'whether', 'how', 'once', 'after', 'before', 'over', 'under', 'above', 'below', 'among', 'amid', 'amongst', 'among', 'around', 'as', 'at', 'atop', 'by', 'down', 'during', 'except', 'for', 'from', 'in', 'into', 'like', 'minus', 'near', 'next', 'of', 'off', 'on', 'onto', 'opposite', 'out', 'outside', 'over', 'past', 'per', 'plus', 'round', 'save', 'since', 'than', 'through', 'throughout', 'till', 'times', 'to', 'toward', 'towards', 'under', 'until', 'up', 'upon', 'via', 'with', 'within', 'without', 'yet']
    df = df[~df['Word'].isin(conjunctions)]

    # Drop rows with articles
    articles = ['a', 'an', 'the']
    df = df[~df['Word'].isin(articles)]

    # Drop rows with pronouns
    pronouns = ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'my', 'him', 'her', 'us', 'mine', 'our', 'his', 'hers', 'its', 'ours', 'yours', 'theirs', 'myself', 'yourself', 'himself', 'herself', 'itself', 'yourselves', 'themselves', 'my', 'your', 'yours', 'ours', 'theirs', 'its', 'whose']
    df = df[~df['Word'].isin(pronouns)]

    # Sort by frequency
    df = df.sort_values(by=['Frequency'], ascending=False)

    return df

    

def text_to_json(book_name, sentence_type, json_path, sentences_input_path):
    """
    Convert text to JSON books format

    Inputs:
    --------
    book_name: String, Name of the book

    sentence_type: String, Type of sentences to add (generated or original)

    json_path: String, Path to the JSON file to be written to

    sentences_input_path: String, Path to the text file to be read from
    """
    # Read the text file
    with open(sentences_input_path, "r") as f:
        text = f.read()
    # Split into sentences
    paragraphs = text.split("\n\n")
    sentences = [
        s.strip() for para in paragraphs for s in sent_tokenize(para) if s.strip()
    ]

    with open(json_path, "r+") as f:
        data = json.load(f)

        book_found = False
        # If book in JSON, update the sentences
        for book in data["books"]:
            if book["text_name"] == book_name:
                book[sentence_type] = sentences
                book_found = True
                break

        # If book not in JSON, add it
        if not book_found:
            new_book = {"text_name": book_name}
            new_book[sentence_type] = sentences
            data["books"].append(new_book)
            print(data)
    with open(json_path, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
