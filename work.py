import json
import sqlite3
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

url = 'https://github.com/orgs/google/repositories'
headers = {'User-Agent': 'Mozilla/5.0'}
DB_path = 'github.sqlite'
MAX_PAGES = 3

def fetch_page(page):
    res = requests.get(url, headers=headers, params={'page': page})
    res.raise_for_status()
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    tag = soup.select_one('script[data-target= "react-app.embeddedData"]')
    data = json.loads(tag.string)
    return data['payload']['orgReposPageRoute'] 

con = sqlite3.connect(DB_path)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

page = 1
last_page = None
while True:
    route = fetch_page(page)
    if last_page is None:
        last_page = route['pageCount']
        if MAX_PAGES:
            last_page = min(last_page, MAX_PAGES)
    
    for repo in route['repositories']:
        lang = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        cur.execute(
            'INSERT OR REPLACE INTO repos VALUES(?, ?, ?)',
            (repo['name'], lang, repo['starsCount'])
        )
    con.commit()
    print(f'page{page}/{last_page}done')
    
    if page >= last_page:
        break
    page += 1
    time.sleep(1)

con.close()

pd.set_option('display.unicode.east_asian_width', True)

con = sqlite3.connect(DB_path)
print(pd.read_sql('SELECT * FROM repos ORDER BY stars DESC LIMIT 20;', con))
con.close()
