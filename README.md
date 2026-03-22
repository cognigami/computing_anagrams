*Before you begin*: Be sure to download a word frequency data set to build the
bigram model. This project uses the Brown data set (1961), but you can change
that easily.

```shell
python -c "import nltk; nltk.download('brown')"
```

# Overview
The scripts in this repo generate genre-tailored anagrams from a phrase that you
provide.

The word search script tries to match your string with up to 3 words from one
or more dictionaries. You can pass the output of the search script to a scorer,
which has configurable genre profiles. Each profile tries to score the
anagram words according to a seed vocabulary. The vocabulaty allows you to tune
the scorers response by using word-count score and optional pattern-matched
bonuses.

# Usage
1. Generate a word list by using `word-search.py`. Be sure to add your phrase to
   word-search. I'll make this a command-line option at some point.
2. Use `scorer.py` to generate your top N candidates. I've included three
   profiles, which you can edit and tune to your liking. The `medical`
   profile includes a multiplier to boost the score of certain features.

```shell
# Add your phrase to word-search.py
python word-search.py > output.csv
python scorer.py output.csv --profile institutional --top 50
```
