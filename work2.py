import sqlite3
con = sqlite3.connect('github.sqlite')
print(con.execute('SELECT COUNT(*) FROM repos').fetchone()[0])
con.close()

import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

url = 'https://github.com/orgs/google/repositories'
DB_path = 'github.sqlite'
START_PAGE = 90
END_PAGE = 99

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})

def fetch_page(page, max_retries=6):
    for attempt in range(max_retries):
        res = session.get(url, params={'page': page}, timeout=30)
        if res.status_code == 429:
            wait = int(res.headers.get('Retry-After', 60 * (attempt + 1)))
            print(f'  429，等待 {wait} 秒後重試（{attempt + 1}/{max_retries}）')
            time.sleep(wait)
            continue
        res.raise_for_status()
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        tag = soup.select_one('script[data-target="react-app.embeddedData"]')
        data = json.loads(tag.string)
        return data['payload']['orgReposPageRoute']
    raise RuntimeError(f'第 {page} 頁重試 {max_retries} 次仍失敗')

con = sqlite3.connect(DB_path)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

for page in range(START_PAGE, END_PAGE + 1):
    route = fetch_page(page)
    for repo in route['repositories']:
        lang = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        cur.execute('INSERT OR REPLACE INTO repos VALUES(?, ?, ?)',
                    (repo['name'], lang, repo['starsCount']))
    con.commit()
    print(f'page {page}/{END_PAGE} done')
    if page < END_PAGE:
        time.sleep(2)

con.close()

pd.set_option('display.unicode.east_asian_width', True)
con = sqlite3.connect(DB_path)
print(pd.read_sql('SELECT COUNT(*) AS total FROM repos;', con))
con.close()
