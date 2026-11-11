import sqlite3
import time
import requests
from bs4 import BeautifulSoup

url = 'https://github.com/orgs/google/repositories'
headers = {'User-Agent': 'Mozilla/5.0'}

github = 'github.sqlite'
con = sqlite3.connect(github)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

