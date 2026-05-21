
import json
import re

try:
    with open("page.html", "r") as f:
        html = f.read()
    
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if match:
        data = json.loads(match.group(1))
        episode = data.get('props', {}).get('pageProps', {}).get('episode', {})
        print("Episode keys:", list(episode.keys()))
        print("Enclosure:", episode.get('enclosure'))
        print("Media:", episode.get('media'))
        print("Pid:", episode.get('pid'))
        print("Description len:", len(episode.get('description', '')))
    else:
        print("No NEXT_DATA found")
except Exception as e:
    print(e)
