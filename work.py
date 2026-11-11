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

# 取得する最大ページ数(None の場合は最終ページまで取得)
MAX_PAGES = None

# Sessionを使うと、ヘッダーやCookieを引き継いで複数回リクエストできる
session = requests.Session()
session.headers.update({
    # ブラウザからのアクセスに見せるための User-Agent
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})


def fetch_page(page):
    """指定したページを取得し、埋め込まれているJSONデータを返す"""
    res = session.get(url, params={'page': page}, timeout=30)
    res.raise_for_status()      # 200以外(429など)ならエラーにする
    res.encoding = 'utf-8'      # 文字化け防止

    # HTMLを解析し、リポジトリ情報が入っているJSONの<script>タグを探す
    soup = BeautifulSoup(res.text, 'html.parser')
    tag = soup.select_one('script[data-target="react-app.embeddedData"]')
    data = json.loads(tag.string)
    return data['payload']['orgReposPageRoute']


# --- DBへ接続し、テーブルを作成する ---
con = sqlite3.connect(DB_path)
cur = con.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS repos(
        name TEXT PRIMARY KEY,
        language TEXT,
        stars INTEGER
    );
''')

# --- 1ページ目から順にスクレイピングする ---
page = 1
last_page = None
while True:
    route = fetch_page(page)

    # 初回のみ、最終ページ番号(pageCount)を取得する
    if last_page is None:
        last_page = route['pageCount']
        if MAX_PAGES:
            last_page = min(last_page, MAX_PAGES)

    # 1ページ分のリポジトリをDBに保存する
    for repo in route['repositories']:
        # 主要な言語が設定されていないリポジトリは None にする
        lang = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        # INSERT OR REPLACE:同じnameがあれば上書きする
        cur.execute(
            'INSERT OR REPLACE INTO repos VALUES(?, ?, ?)',
            (repo['name'], lang, repo['starsCount'])
        )
    con.commit()    # ページごとに保存
    print(f'page{page}/{last_page}done')

    if page >= last_page:
        break
    page += 1
    time.sleep(1)

con.close()

# --- 保存したデータをSELECT文で表示する ---
# 日本語(全角文字)でも列がずれないようにする設定
pd.set_option('display.unicode.east_asian_width', True)

con = sqlite3.connect(DB_path)
print(pd.read_sql('SELECT * FROM repos ORDER BY stars DESC LIMIT 20;', con))
con.close()
