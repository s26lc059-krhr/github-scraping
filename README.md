# github-scraping

GitHubの Google 公式組織(`google`)が管理するリポジトリの情報を
スクレイピングで取得し、SQLite に保存するプログラムです。
(データサイエンスプログラミング1 最終課題)

## 取得する情報

| 項目 | 説明 |
|---|---|
| name | リポジトリ名 |
| language | 主要な言語(設定がない場合は NULL) |
| stars | スターの数 |

## 対象ページ

https://github.com/orgs/google/repositories

## ファイル構成

```
github-scraping/
├── work.py          # 1ページ目から最終ページまで取得するメインプログラム
├── work2.py         # アクセス制限(429)で中断した分を補完取得するプログラム
├── README.md
└── .gitignore       # github.sqlite などを管理対象外にする
```

## 使用技術

- Python 3
- requests(HTTPリクエスト)
- BeautifulSoup4(HTMLの解析)
- sqlite3(データベース)
- pandas(結果の表示)

## 実行方法

### 1. ライブラリのインストール

```bash
pip install requests beautifulsoup4 pandas
```

### 2. スクレイピングの実行

```bash
python work.py
```

途中で `429 Too Many Requests` により中断した場合は、
中断したページ以降を `work2.py` で補完します。
`START_PAGE` と `END_PAGE` を必要に応じて書き換えてから実行してください。

```bash
python work2.py
```

### 3. 保存したデータの確認

```bash
sqlite3 github.sqlite
```

```sql
SELECT COUNT(*) FROM repos;
SELECT * FROM repos ORDER BY stars DESC LIMIT 10;
```

## 実装上のポイント

- **GitHub API は使用していません。** 一覧ページのHTMLに埋め込まれている
  JSONを解析して取得しています。
- リクエストの間に `time.sleep()` を入れ、サーバーへの負荷を抑えています。
- `name` を主キーにして `INSERT OR REPLACE` を使っているため、
  同じページを再取得しても重複データは作成されません。
- 主要な言語が未設定のリポジトリは `NULL` として保存します。
- スター数は、画面表示の `1.5k` のような略記ではなく、
  JSON内の正確な整数値(`starsCount`)を保存しています。

## 工夫した点

- 途中で `429 Too Many Requests` が発生したため、
  `work2.py` では `Retry-After` に従って待機・再試行する処理を追加しました。
- ページごとに `commit()` することで、中断してもそれまでのデータが失われないようにしました。
- 全99ページを取得する途中で、429 Too Many Requests によりアクセスが制限されました。 
そのため、リクエスト間隔を空け、Retry-After に従って待機・再試行する処理を追加し、
中断した分を work2.py で補完しました。

## 注意事項

- 取得中にリポジトリの並び順(最終更新順)が変化するため、
  件数が公式の表示(約2,945件)と数件ずれる場合があります。
- スクレイピングは対象サイトの利用規約・負荷に配慮して行ってください。
