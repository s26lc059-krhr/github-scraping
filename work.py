import json
import sqlite3
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# スクレイピング対象のURL
url = 'https://github.com/orgs/google/repositories'

# 保存先のSQLiteファイル名
DB_path = 'github.sqlite'

# 取得するページの範囲
START_PAGE = 1    # 状況に応じて変更可(中断したページ番号に合わせる)
END_PAGE = None   # None の場合は最終ページ(pageCount)まで取得

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})


def fetch_page(page, max_retries=6):
    """指定ページを取得する。429や接続エラーの場合は待機して再試行する"""
    for attempt in range(max_retries):
        try:
            res = session.get(url, params={'page': page}, timeout=30)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            # 接続が切れた/タイムアウトした場合も待機して再試行
            wait = 30 * (attempt + 1)
            print(f'  接続エラー、{wait}秒待機して再試行します({attempt + 1}/{max_retries})')
            time.sleep(wait)
            continue

        if res.status_code == 429:
            wait = int(res.headers.get('Retry-After', 60 * (attempt + 1)))
            print(f'  429、{wait}秒待機して再試行します({attempt + 1}/{max_retries})')
            time.sleep(wait)
            continue

        res.raise_for_status()
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        tag = soup.select_one('script[data-target="react-app.embeddedData"]')
        data = json.loads(tag.string)
        return data['payload']['orgReposPageRoute']

    raise RuntimeError(f'{page}ページ目は{max_retries}回再試行しても失敗しました')


con = sqlite3.connect(DB_path)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

page = START_PAGE
while True:
    route = fetch_page(page)

    # 最終ページが未指定なら、取得したデータの pageCount を使う
    if END_PAGE is None:
        END_PAGE = route['pageCount']

    for repo in route['repositories']:
        lang = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        cur.execute('INSERT OR REPLACE INTO repos VALUES(?, ?, ?)',
                    (repo['name'], lang, repo['starsCount']))
    con.commit()
    print(f'page {page}/{END_PAGE} done')

    if page >= END_PAGE:
        break
    page += 1
    time.sleep(1)

con.close()

# --- 保存したデータをSELECT文で表示する ---
pd.set_option('display.unicode.east_asian_width', True)
con = sqlite3.connect(DB_path)
print(pd.read_sql('SELECT COUNT(*) AS total FROM repos;', con))
print(pd.read_sql('SELECT * FROM repos ORDER BY stars DESC LIMIT 20;', con))
con.close()
