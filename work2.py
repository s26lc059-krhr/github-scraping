import sqlite3
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- 現在のDBの件数を確認する ---
con = sqlite3.connect('github.sqlite')
print(con.execute('SELECT COUNT(*) FROM repos').fetchone()[0])
con.close()

# スクレイピング対象のURL
url = 'https://github.com/orgs/google/repositories'

DB_path = 'github.sqlite'

# 補完して取得するページの範囲
START_PAGE = 90 # 状況に応じて変更可(work.py が中断したページ番号に合わせる)
END_PAGE = 99

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})


def fetch_page(page, max_retries=6):
    """指定ページを取得する。429(アクセス制限)の場合は待機して再試行する"""
    for attempt in range(max_retries):
        res = session.get(url, params={'page': page}, timeout=30)

        # 429 Too Many Requests:アクセス過多で一時的に制限されている
        if res.status_code == 429:
            # サーバーが指定する待機秒数(Retry-After)があればそれに従う
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

    # 何度試しても取得できなかった場合
    raise RuntimeError(f'{page}ページ目は{max_retries}回再試行しても失敗しました')


# --- DBへ接続し、テーブルがなければ作成する ---
con = sqlite3.connect(DB_path)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

# --- 指定した範囲のページを順に取得して保存する ---
for page in range(START_PAGE, END_PAGE + 1):
    route = fetch_page(page)
    for repo in route['repositories']:
        lang = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        cur.execute('INSERT OR REPLACE INTO repos VALUES(?, ?, ?)',
                    (repo['name'], lang, repo['starsCount']))
    con.commit()
    print(f'page {page}/{END_PAGE} done')

    # 最後のページ以外は、次のリクエストまで待機する(time.sleep の指示を守る)
    if page < END_PAGE:
        time.sleep(2)

con.close()

# --- 最終的な件数を表示する ---
pd.set_option('display.unicode.east_asian_width', True)
con = sqlite3.connect(DB_path)
print(pd.read_sql('SELECT COUNT(*) AS total FROM repos;', con))
con.close()
