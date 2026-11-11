import requests

url = 'https://github.com/orgs/google/repositories'

res = requests.get(url)
res.encoding = 'cp932'

# print(res.text)

with open("google.html", 'w') as f:
  f.write(res.text)
