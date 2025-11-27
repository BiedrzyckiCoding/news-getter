this is supposed to be a simple app that fetches historical data from google using google custom search api

the purpse of this repo is to then use this program to retrirve historial data about companies / crypto to try and find a correlation between the news and their price movements

as far as im aware, the api fetches links to the web articles, then i can build a simple webscraper to scrape the html contents and retrire text from it - make embeddings using a simple library, maybe it will privide better data.

ok so there are multiple python libraries that i can use to summarize text:
1. Pandas: For basic data manipulation and summary statistics.
2. csv: For simple line-by-line reading and manual summaries.
3. TextBlob: For basic text summarization.
4. NLTK: For more advanced NLP and text summarization.
5. Gensim: For topic modeling and advanced text summarization.
6. Dask: For handling large CSV files that do not fit in memory.