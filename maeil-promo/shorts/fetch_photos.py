"""숏폼용 실사 사진 수집 (무료 라이선스: Unsplash License / Wikimedia Commons CC).

1) python3 fetch_photos.py search      → candidates/<slot>/NN.jpg 후보 + contact_<slot>.jpg
2) python3 fetch_photos.py pick 01_phone_night=3 02_scroll=0 ...
                                        → photos/<slot>.jpg (세로 1210x2150 크롭) + credits.json 갱신
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, 'candidates')
PHOTOS = os.path.join(HERE, 'photos')
CREDITS = os.path.join(HERE, 'credits.json')
UA = {'User-Agent': 'maeil-promo-shorts/1.0 (video draft; contact via repo)'}

SLOTS = {
    '01_phone_night': ('unsplash', 'face lit by phone screen at night'),
    '02_scroll': ('unsplash', 'hand scrolling smartphone'),
    '03_crowd_phones': ('unsplash', 'people using phones subway'),
    '04_film_camera': ('unsplash', 'film camera hands'),
    '05_vinyl': ('unsplash', 'vinyl record player'),
    '06_handwriting': ('unsplash', 'handwriting notebook pen'),
    '07_reading_cafe': ('unsplash', 'young person reading book cafe'),
    '08_newspaper_young': ('unsplash', 'young man reading newspaper'),
    '09_newsprint': ('unsplash', 'newspaper close up'),
    '10_daegu': ('unsplash', 'Daegu'),
    '11_morning_paper': ('unsplash', 'coffee newspaper morning'),
}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def unsplash(query, n=8):
    q = urllib.parse.urlencode({'query': query, 'per_page': 30, 'orientation': 'portrait'})
    data = json.loads(get(f'https://unsplash.com/napi/search/photos?{q}'))
    out = []
    for p in data.get('results', []):
        if p.get('premium') or p.get('plus'):  # Unsplash+ 는 무료 라이선스가 아님
            continue
        out.append({
            'thumb': p['urls']['small'],
            'full': p['urls']['raw'] + '&w=1400&fm=jpg&q=85',
            'author': p['user']['name'],
            'page': p['links']['html'],
            'license': 'Unsplash License',
        })
        if len(out) >= n:
            break
    return out


def commons(query, n=8):
    q = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
        'gsrsearch': query, 'gsrlimit': 30, 'prop': 'imageinfo',
        'iiprop': 'url|extmetadata', 'iiurlwidth': 1400})
    data = json.loads(get(f'https://commons.wikimedia.org/w/api.php?{q}'))
    out = []
    for p in (data.get('query', {}).get('pages', {}) or {}).values():
        ii = p['imageinfo'][0]
        md = ii.get('extmetadata', {})
        lic = md.get('LicenseShortName', {}).get('value', '')
        if not any(k in lic for k in ('CC BY', 'CC0', 'Public domain')):
            continue
        out.append({
            'thumb': ii['thumburl'], 'full': ii['thumburl'],
            'author': md.get('Artist', {}).get('value', ''),
            'page': ii['descriptionurl'], 'license': lic,
        })
        if len(out) >= n:
            break
    return out


def search():
    os.makedirs(CAND, exist_ok=True)
    for slot, (src, query) in SLOTS.items():
        items = (unsplash if src == 'unsplash' else commons)(query)
        d = os.path.join(CAND, slot)
        os.makedirs(d, exist_ok=True)
        json.dump(items, open(os.path.join(d, 'meta.json'), 'w'), ensure_ascii=False, indent=1)
        thumbs = []
        for i, it in enumerate(items):
            im = Image.open(io.BytesIO(get(it['thumb']))).convert('RGB')
            im.save(os.path.join(d, f'{i:02d}.jpg'))
            thumbs.append(im)
        W, H = 240, 400
        sheet = Image.new('RGB', (W * max(1, len(thumbs)), H + 30), 'white')
        for i, im in enumerate(thumbs):
            im = im.copy()
            im.thumbnail((W, H))
            sheet.paste(im, (i * W, 30))
            ImageDraw.Draw(sheet).text((i * W + 6, 6), str(i), fill='black')
        sheet.save(os.path.join(CAND, f'contact_{slot}.jpg'))
        print(slot, len(items))


def cover(im, w=1210, h=2150, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = round((im.width - w) * fx)
    y = round((im.height - h) * fy)
    return im.crop((x, y, x + w, y + h))


def pick(args):
    os.makedirs(PHOTOS, exist_ok=True)
    credits = json.load(open(CREDITS)) if os.path.exists(CREDITS) else {}
    for a in args:
        slot, spec = a.split('=')
        parts = spec.split(',')                    # 번호[,가로중심,세로중심]
        i = int(parts[0])
        fx = float(parts[1]) if len(parts) > 1 else 0.5
        fy = float(parts[2]) if len(parts) > 2 else 0.5
        it = json.load(open(os.path.join(CAND, slot, 'meta.json')))[i]
        im = Image.open(io.BytesIO(get(it['full']))).convert('RGB')
        cover(im, fx=fx, fy=fy).save(os.path.join(PHOTOS, f'{slot}.jpg'), quality=88)
        credits[slot] = {k: it[k] for k in ('author', 'page', 'license')}
        print(slot, '←', it['page'])
    json.dump(dict(sorted(credits.items())), open(CREDITS, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    if sys.argv[1] == 'search':
        search()
    else:
        pick(sys.argv[2:])
