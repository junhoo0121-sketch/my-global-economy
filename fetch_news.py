import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
today = datetime.now(KST).strftime('%Y-%m-%d')

feeds = {
    '미국': 'https://news.google.com/rss/search?q=US+economy+stock+market&hl=en-US&gl=US&ceid=US:en',
    '한국': 'https://news.google.com/rss/search?q=한국+경제+증시&hl=ko&gl=KR&ceid=KR:ko',
    '중국': 'https://news.google.com/rss/search?q=China+economy&hl=en-US&gl=US&ceid=US:en',
    '유럽': 'https://news.google.com/rss/search?q=Europe+economy+ECB&hl=en-US&gl=US&ceid=US:en',
}


def translate_title(title):
    """Try unofficial Google Translate endpoint; keep original on failure.

    This endpoint is not an official supported API and may stop working or rate-limit.
    """
    params = urllib.parse.urlencode({'client': 'gtx', 'sl': 'auto', 'tl': 'ko', 'dt': 't', 'q': title})
    url = 'https://translate.googleapis.com/translate_a/single?' + params
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.load(response)
        translated = ''.join(part[0] for part in payload[0] if part and part[0]).strip()
        if translated:
            return translated, True
    except Exception as exc:
        print(f'번역 실패, 원문 유지: {exc}')
    return title, False


articles = []
seen = set()
for region, url in feeds.items():
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read())
        count = 0
        for item in root.findall('./channel/item'):
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            published = item.findtext('pubDate', '')
            source = item.findtext('source', '')
            if not title or not link or title in seen:
                continue
            seen.add(title)
            if region == '한국':
                title_ko, translated = title, True
            else:
                title_ko, translated = translate_title(title)
            articles.append({
                'region': region,
                'title': title,
                'title_ko': title_ko,
                'translation_ok': translated,
                'link': link,
                'source': source,
                'published': published,
            })
            count += 1
            if count >= 5:
                break
    except Exception as error:
        print(f'{region} 수집 실패: {error}')

if not articles:
    raise RuntimeError('뉴스 수집 실패: 저장하지 않습니다.')

output = {'date': today, 'updated_at': datetime.now(KST).isoformat(), 'articles': articles}
folder = Path('data')
folder.mkdir(exist_ok=True)
content = json.dumps(output, ensure_ascii=False, indent=2)
(folder / 'latest.json').write_text(content, encoding='utf-8')
(folder / f'{today}.json').write_text(content, encoding='utf-8')
print(f'{today}: 뉴스 {len(articles)}개 저장 완료, 번역 성공 {sum(a["translation_ok"] for a in articles)}개')
