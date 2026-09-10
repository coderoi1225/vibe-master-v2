#!/usr/bin/env python3
"""바이브마스터 v2 빌드 — 원고/*/​*.md → 단일 HTML 한 장.
사용: python3 발행/build.py            (어디서 실행해도 됨)
출력: 발행/바이브마스터v2.html  → 같은 파일을 같은 아티팩트에 재발행한다. 링크가 바뀌면 안 된다.

v1이 죽은 두 원인을 피한다:
  1) 검색을 외부 빌드(Pagefind)에 맡기지 않는다 — 페이지 안 JS로.
  2) 절대경로를 쓰지 않는다 — 링크는 전부 페이지 안 앵커.
진도는 보는 사람 기기(localStorage)에만 남는다. 서버·로그인 없음."""
import sys, re, json, os, glob, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '바이브마스터v2.html')

# 폴더 이름 → (스테이지 키, 표시 이름, 색). 순서가 곧 목차 순서다.
STAGES = [
    ('00-환경',          '0',      '환경',            '#2dd4bf'),
    ('01-시장',          '1',      '시장',            '#60a5fa'),
    ('02-명세',          '2',      '명세',            '#7dd3fc'),
    ('03-컨텍스트하네스', '3',      '컨텍스트·하네스',  '#a78bfa'),
    ('04-디자인',        '4',      '디자인',          '#f472b6'),
    ('045-버전관리',     '4.5',    '버전 관리',       '#fb7185'),
    ('05-구현',          '5',      '구현',            '#fb923c'),
    ('06-서버결제',      '6',      '서버·인증·결제',   '#fbbf24'),
    ('07-배포PR',        '7',      '배포·PR',         '#34d399'),
    ('08-자율운영',      '8',      '자율 운영',        '#4ade80'),
    ('09-지식운영',      '9',      '지식 운영',        '#c4b5fd'),
    ('10-판매',          '10',     '판매',            '#fde68a'),
    ('업무자동화',       '자동화',  '업무 자동화',      '#f59e0b'),
    ('부록',             '부록',    '부록',            '#94a3b8'),
]

def parse_fm(text):
    """--- 사이 frontmatter를 dict로. [a, b] 는 리스트로."""
    m = re.match(r'^---\n(.*?)\n---\n?(.*)$', text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        k, v = k.strip(), v.strip()
        if v.startswith('[') and v.endswith(']'):
            fm[k] = [x.strip() for x in v[1:-1].split(',') if x.strip()]
        else:
            fm[k] = v.strip('\'"')
    return fm, m.group(2)

def split_sections(body):
    """## 칸 단위로 쪼갠다. 첫 ## 앞의 글은 머리말로.
    코드블록(``` 또는 ~~~) 안의 ## 는 제목이 아니라 내용이다 — 자르지 않는다."""
    lines, fence = body.split('\n'), None
    head, secs, cur = [], [], None
    for ln in lines:
        m = re.match(r'^\s*(`{3,}|~{3,})', ln)
        if m:
            tok = m.group(1)[0] * 3
            fence = None if fence == tok else (fence or tok)
        if fence is None and ln.startswith('## '):
            cur = {'title': ln[3:].strip(), 'lines': []}
            secs.append(cur)
            continue
        (cur['lines'] if cur else head).append(ln)
    return ('\n'.join(head).strip(),
            [{'title': s['title'], 'md': '\n'.join(s['lines']).strip()} for s in secs])

stages, missing = [], []
for folder, key, name, color in STAGES:
    d = os.path.join(ROOT, '원고', folder)
    if not os.path.isdir(d):
        missing.append(folder)
        continue
    meta_path = os.path.join(d, '_스테이지.md')
    meta, meta_head, meta_secs = {}, '', []
    if os.path.exists(meta_path):
        meta, mbody = parse_fm(open(meta_path, encoding='utf-8').read())
        meta_head, meta_secs = split_sections(mbody)
    # 파일명이 아니라 frontmatter의 순서로 정렬한다.
    # 파일명 순이면 '10-'이 '2-' 앞으로 간다.
    files = []
    for fp in glob.glob(os.path.join(d, '*.md')):
        if os.path.basename(fp).startswith('_'):
            continue
        fm, body = parse_fm(open(fp, encoding='utf-8').read())
        try:
            order = float(str(fm.get('순서', '999')).replace(' ', ''))
        except ValueError:
            order = 999.0
        files.append((order, os.path.basename(fp), fm, body))
    sections = []
    for _, fname, fm, body in sorted(files, key=lambda x: (x[0], x[1])):
        head, secs = split_sections(body)
        sections.append({
            'file': fname,
            'id': f"s{key.replace('.', '_')}-{len(sections) + 1}",
            'no': fm.get('순서', ''), 'title': fm.get('제목', os.path.splitext(fname)[0]),
            'goals': fm.get('목표', []) if isinstance(fm.get('목표', []), list) else [fm.get('목표')],
            'steps': fm.get('진행', []) if isinstance(fm.get('진행', []), list) else [fm.get('진행')],
            'through': fm.get('관통', ''), 'time': fm.get('소요', ''),
            'need': fm.get('준비물', []) if isinstance(fm.get('준비물', []), list) else [fm.get('준비물')],
            'head': head, 'secs': secs,
        })
    stages.append({
        'folder': folder,
        'key': key, 'name': name, 'color': color,
        'sub': meta.get('부제', ''), 'goal': meta.get('학습목적', ''),
        'makes': meta.get('만드는것', ''), 'time': meta.get('소요', ''),
        'need': meta.get('준비물', []) if isinstance(meta.get('준비물', []), list) else [meta.get('준비물')],
        'head': meta_head, 'metasecs': meta_secs, 'sections': sections,
    })

# ── [[위키링크]] → 페이지 안 링크 ────────────────────────────────
# 옵시디언에서는 [[이름]]이 링크지만 발행 HTML에서는 대괄호가 그대로 보인다.
# 실재하는 절이면 그 절로 뛰는 링크로, 예시로 든 이름이면 조용한 글씨로 바꾼다.
INDEX, UNRESOLVED = {}, {}
for st in stages:
    # 장 자체를 가리키는 링크 — [[07-배포PR/_스테이지|Stage 7]] 같은 것
    for k in (st['folder'], f"{st['folder']}/_스테이지", f"Stage {st['key']}", st['name']):
        INDEX.setdefault(k, (st['key'], '', st['name']))
    for sec in st['sections']:
        for k in (sec['file'], os.path.splitext(sec['file'])[0],
                  f"{st['folder']}/{os.path.splitext(sec['file'])[0]}", sec['title']):
            INDEX[k] = (st['key'], sec['id'], sec['title'])

def wikilink(text):
    def rep(m):
        raw = m.group(1)
        target, _, label = raw.partition('|')
        # 옵시디언에서 [[경로\|라벨]] 처럼 파이프를 이스케이프한 경우가 있다
        target = target.split('#')[0].strip().rstrip('/').rstrip('\\').strip()
        label = (label.strip().lstrip('\\') or os.path.basename(target)) or target
        key = os.path.splitext(os.path.basename(target))[0]
        hit = INDEX.get(target) or INDEX.get(key)
        if hit:
            jump = f' data-jump="{hit[1]}"' if hit[1] else ''
            return f'<a class="xref" href="#{hit[0]}"{jump}>{label}</a>'
        UNRESOLVED[target] = UNRESOLVED.get(target, 0) + 1
        return f'<span class="egfile">{label}</span>'   # 예시 파일 이름 — 링크 아님
    return re.sub(r'\[\[([^\]]+)\]\]', rep, text)

for st in stages:
    st['head'] = wikilink(st['head'])
    for k in st['metasecs']:
        k['md'] = wikilink(k['md'])
    for sec in st['sections']:
        sec['head'] = wikilink(sec['head'])
        for k in sec['secs']:
            k['md'] = wikilink(k['md'])

if missing:
    print('⚠️ 폴더 없음:', ', '.join(missing))
if UNRESOLVED:
    top = sorted(UNRESOLVED.items(), key=lambda x: -x[1])[:8]
    print('· 링크 못 건 이름 %d종 (예시 파일이면 정상):' % len(UNRESOLVED),
          ', '.join(f'{k}×{v}' for k, v in top))
total = sum(len(s['sections']) for s in stages)

# 아티팩트로 발행할 때 doctype·html·head·body는 발행 쪽이 씌운다. 여기서는 내용만 낸다.
TPL = r'''<title>바이브마스터 버전2</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Gowun+Batang:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
/* v1 바이브마스터의 다크·카드·스테이지 색 체계를 잇는다 */
:root{
  --bg:#0a0d13; --s1:#10141c; --s2:#161b25; --s3:#1c2230;
  --line:#222a3a; --line2:#2c3648;
  --fg:#e6e9ef; --fg2:#b9c0cc; --mute:#7f8797; --faint:#59607a;
  --sans:'Noto Sans KR',-apple-system,BlinkMacSystemFont,sans-serif;
  --serif:'Gowun Batang',Georgia,serif;
  --mono:'JetBrains Mono',ui-monospace,monospace;
  --c:#60a5fa;             /* 현재 장의 색 — 화면마다 바뀐다 */
  --w:36rem;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto} *{transition:none!important;animation:none!important}}
body{margin:0;background:var(--bg);color:var(--fg);font:15.5px/1.8 var(--sans);-webkit-text-size-adjust:100%;min-height:100vh}
a{color:var(--c)}
button{font-family:inherit}
:focus-visible{outline:2px solid var(--c);outline-offset:2px;border-radius:4px}
code,pre,kbd{font-family:var(--mono)}

/* ── 위 막대: 진도가 곧 지도 ─────────────── */
.top{position:sticky;top:0;z-index:20;background:rgba(10,13,19,.88);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top-in{max-width:1080px;margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:18px;height:52px}
.brand{background:none;border:0;color:var(--fg);font-weight:900;font-size:14px;letter-spacing:-.02em;cursor:pointer;padding:0;white-space:nowrap}
.brand em{font-style:normal;color:var(--c)}
.segs{display:flex;gap:3px;flex:1;min-width:0}
.seg{flex:1;height:5px;border-radius:99px;background:var(--s3);position:relative;overflow:hidden;cursor:pointer;border:0;padding:0}
.seg i{position:absolute;inset:0;width:var(--p,0%);background:var(--sc);opacity:.95}
.seg[aria-current="true"]{outline:1px solid var(--sc);outline-offset:2px}
.seg:hover{background:var(--line2)}
.sbtn{background:var(--s2);border:1px solid var(--line);color:var(--mute);border-radius:7px;padding:5px 10px;font-size:12px;cursor:pointer;display:flex;gap:8px;align-items:center;white-space:nowrap}
.sbtn:hover{color:var(--fg);border-color:var(--line2)}
.sbtn kbd{font-size:10px;background:var(--s3);padding:1px 5px;border-radius:4px;color:var(--faint)}

/* ── 페이지 ─────────────────────────────── */
.page{max-width:1080px;margin:0 auto;padding:44px 24px 120px}
@media(max-width:720px){.page{padding:26px 16px 90px}.top-in{padding:0 14px;gap:10px}.sbtn span{display:none}}

/* 홈 — 여정 지도 */
.hero{margin-bottom:44px;max-width:44rem}
.hero h1{font-size:clamp(28px,4.4vw,42px);font-weight:900;letter-spacing:-.035em;line-height:1.22;margin:0 0 14px;text-wrap:balance}
.hero p{font-size:16px;color:var(--fg2);margin:0;line-height:1.75;text-wrap:pretty}
.hero .prog{margin-top:22px;font-size:13px;color:var(--mute)}
.hero .prog b{color:var(--fg);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.scard{display:flex;flex-direction:column;gap:10px;background:var(--s1);border:1px solid var(--line);border-radius:14px;padding:20px 20px 18px;
  text-align:left;color:inherit;cursor:pointer;transition:border-color .15s,transform .15s;position:relative;overflow:hidden}
.scard::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--sc)}
.scard:hover{border-color:var(--line2);transform:translateY(-2px)}
.scard .num{display:flex;align-items:center;gap:8px;font:600 11.5px var(--mono);color:var(--mute)}
.scard .num i{width:8px;height:8px;border-radius:50%;background:var(--sc);display:inline-block}
.scard h3{margin:2px 0 0;font-size:18px;font-weight:700;letter-spacing:-.02em;line-height:1.35}
.scard .goal{font-family:var(--serif);font-size:14.5px;line-height:1.7;color:var(--fg2);margin:0}
.scard .foot{display:flex;justify-content:space-between;align-items:center;margin-top:auto;padding-top:8px;font-size:12px;color:var(--mute)}
.scard .bar{height:3px;background:var(--s3);border-radius:99px;overflow:hidden;flex:1;margin-right:12px}
.scard .bar i{display:block;height:100%;background:var(--sc);width:var(--p,0%)}
.scard.done h3{color:var(--mute)}
.band{grid-column:1/-1;display:flex;align-items:center;gap:10px;margin:30px 0 2px;color:var(--fg2);font-size:14px;font-weight:700;letter-spacing:-.01em}
.band i{width:22px;height:2px;background:var(--bc,var(--line));border-radius:99px;flex:none}
.band small{font-weight:500;color:var(--faint);font-size:12px}
.band::after{content:"";flex:1;height:1px;background:var(--line);align-self:center}

/* 장 */
.shero{position:relative;padding:28px 30px 30px;margin:0 0 28px;border-radius:16px;max-width:none;
  background:linear-gradient(135deg,color-mix(in srgb,var(--c) 16%,var(--s1)),var(--s1) 70%);border:1px solid color-mix(in srgb,var(--c) 30%,var(--line))}
.shero::after{content:attr(data-n);position:absolute;right:26px;top:10px;font:900 84px/1 var(--mono);color:color-mix(in srgb,var(--c) 22%,transparent);letter-spacing:-.06em;pointer-events:none}
@media(max-width:720px){.shero{padding:22px 18px}.shero::after{font-size:56px}}
.crumbs{display:flex;gap:8px;align-items:center;font-size:12.5px;color:var(--mute);margin-bottom:16px;flex-wrap:wrap}
.crumbs button{background:none;border:0;color:var(--mute);cursor:pointer;padding:0;font-size:inherit}
.crumbs button:hover{color:var(--fg)}
.crumbs b{color:var(--c);font-weight:700}
.shero h1{font-size:clamp(26px,3.6vw,34px);font-weight:900;letter-spacing:-.03em;line-height:1.25;margin:0 0 16px;text-wrap:balance}
.shero h1 small{display:block;font-size:13px;font-weight:600;color:var(--c);letter-spacing:.02em;margin-bottom:8px;font-family:var(--mono)}
.goalline{font-family:var(--serif);font-size:19px;line-height:1.7;color:var(--fg);margin:0 0 18px;text-wrap:pretty}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-size:12px;color:var(--fg2);background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:4px 11px}
.chip b{color:var(--mute);font-weight:500;margin-right:5px}
.intro{max-width:var(--w);color:var(--fg2);font-size:15px}
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin:22px 0 34px}
.ccard{display:flex;flex-direction:column;gap:8px;background:var(--s1);border:1px solid var(--line);border-radius:12px;padding:16px 18px;
  text-align:left;color:inherit;cursor:pointer;transition:border-color .15s}
.ccard:hover{border-color:var(--c)}
.ccard .no{font:600 11px var(--mono);color:var(--mute);display:flex;justify-content:space-between;align-items:center}
.ccard .no em{font-style:normal;display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:22px;padding:0 7px;border-radius:6px;background:var(--c);color:#0a0d13;font-weight:700;margin-right:8px}
.ccard .no .rd{color:var(--c)}
.ccard h4{margin:0;font-size:16px;font-weight:700;letter-spacing:-.015em;line-height:1.4}
.ccard p{margin:0;font-size:13.5px;line-height:1.65;color:var(--fg2)}
.ccard.done h4{color:var(--mute)}
.ccard.done p{color:var(--faint)}

/* 절 — 읽는 단위 */
.two{display:grid;grid-template-columns:minmax(0,1fr) 220px;gap:44px;align-items:start}
@media(max-width:860px){.two{grid-template-columns:1fr}.rail{display:none}}
.art{max-width:var(--w)}
.art h1{font-size:clamp(24px,3.2vw,30px);font-weight:900;letter-spacing:-.03em;line-height:1.3;margin:0 0 14px;text-wrap:balance}
.through{font-family:var(--serif);font-size:18.5px;line-height:1.75;color:var(--fg);margin:0 0 20px;padding:18px 20px;
  background:var(--s1);border:1px solid var(--line);border-radius:12px;text-wrap:pretty}
.rail{position:sticky;top:70px;font-size:12.5px}
.rail .rt{font-size:11px;color:var(--faint);font-weight:700;margin:0 0 8px}
.rail a{display:block;color:var(--mute);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--line);line-height:1.5}
.rail a:hover,.rail a.on{color:var(--fg);border-left-color:var(--c)}
.rail .sep{height:14px}
.rail .btn{width:100%;margin-top:6px}

.body{font-size:15.5px}
.body p{margin:1em 0}
.body>:first-child{margin-top:0}
.body h2{font-size:19px;font-weight:700;letter-spacing:-.02em;margin:2.2em 0 .6em;scroll-margin-top:72px}
.body h3,.body h4{font-size:16px;font-weight:700;margin:1.8em 0 .5em;letter-spacing:-.015em}
.body ul,.body ol{margin:1em 0;padding-left:1.3em}
.body li{margin:.35em 0}
.body li::marker{color:var(--faint)}
.body strong{font-weight:600;color:#fff}
.body a{color:var(--c);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--c) 40%,transparent)}
.body a:hover{border-bottom-color:var(--c)}
.body blockquote{margin:1.3em 0;padding:12px 16px;background:var(--s1);border-radius:10px;color:var(--fg2)}
.body blockquote p{margin:.4em 0}
.body hr{border:0;border-top:1px solid var(--line);margin:2.2em 0}
.body code{background:var(--s2);border:1px solid var(--line);padding:.08em .38em;border-radius:5px;font-size:.85em;word-break:break-all}
.body pre{background:var(--s1);border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow-x:auto;position:relative;margin:1.2em 0;line-height:1.6}
.body pre code{background:none;border:0;padding:0;font-size:12.5px;word-break:normal}
.body table{border-collapse:collapse;width:100%;font-size:13.5px;margin:1.3em 0;display:block;overflow-x:auto;line-height:1.6}
.body th,.body td{border:0;border-bottom:1px solid var(--line);padding:9px 12px 9px 0;text-align:left;vertical-align:top}
.body th{color:var(--mute);font-weight:500;font-size:12px;white-space:nowrap}
.body tr:last-child td{border-bottom:0}
.copy{position:absolute;top:8px;right:8px;font-size:10.5px;padding:3px 8px;border:1px solid var(--line);border-radius:5px;
  background:var(--s2);color:var(--mute);cursor:pointer;opacity:0;transition:opacity .15s}
pre:hover .copy,.copy:focus{opacity:1}

/* 다섯 칸 — v1의 callout 어법: 옅게 물든 상자와 작은 라벨 */
.call{margin:26px 0;padding:16px 18px;border-radius:12px;border:1px solid color-mix(in srgb,var(--kc) 28%,transparent);
  background:color-mix(in srgb,var(--kc) 7%,transparent);scroll-margin-top:72px}
.call>b{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--kc);margin-bottom:10px;font-weight:700}
/* ⚡ 따라 하기 — 실행 칸이라 가장 눈에 띄게. 머리에 색 띠 */
.call.k-zap{padding:0;overflow:hidden;border-width:1.5px;background:var(--s1)}
.call.k-zap>b{background:color-mix(in srgb,var(--kc) 16%,transparent);margin:0;padding:11px 18px;
  border-bottom:1px solid color-mix(in srgb,var(--kc) 24%,transparent);font-size:13px}
.call.k-zap>.body{padding:14px 18px 16px}
/* ✅ 확인 — 체크리스트 카드 */
.call.k-ok{background:var(--s1);border-width:1.5px}
.call.k-ok .body ul{list-style:none;padding-left:0}
.call.k-ok .body li{position:relative;padding-left:30px;margin:.6em 0}
.call.k-ok .body li::before{content:"";position:absolute;left:0;top:.32em;width:16px;height:16px;
  border:1.5px solid color-mix(in srgb,var(--kc) 60%,transparent);border-radius:4px}
/* ⚠️ 함정 — 왼쪽 굵은 띠 */
.call.k-trap{border-left-width:4px;border-radius:4px 12px 12px 4px;background:color-mix(in srgb,var(--kc) 9%,transparent)}
/* 📘 말 풀이 — 사전처럼 조용하게 */
.call.k-say{background:transparent;border-style:dashed}
.call.k-say .body p{margin:.55em 0}
.call.k-say .body strong{color:var(--kc);font-weight:700}
/* 🔎 더 깊이 — 가장 조용하게 */
.call.k-deep{background:transparent;border-style:dotted;border-color:var(--line)}
.call.k-deep>b{color:var(--mute)}
.call.k-deep .body{color:var(--dim);font-size:14.5px}
.call>b svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}
.call .body p:first-child{margin-top:0}.call .body p:last-child{margin-bottom:0}
.k-say{--kc:#7dd3fc}.k-trap{--kc:#fb923c}.k-zap{--kc:#34d399}.k-ok{--kc:#fbbf24}.k-deep{--kc:#c4b5fd}

/* 학습 틀 — 목표·순서·단계 */
.goals{margin:0 0 18px;padding:16px 18px 16px 20px;border-radius:12px;background:color-mix(in srgb,var(--c) 9%,transparent);border:1px solid color-mix(in srgb,var(--c) 30%,transparent)}
.goals b{display:block;font-size:12px;color:var(--c);margin-bottom:8px}
.goals ul{margin:0;padding-left:1.2em}
.goals li{margin:.3em 0;font-size:15px}
.steps{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 34px;align-items:center}
.steps a{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--fg2);text-decoration:none;background:var(--s1);border:1px solid var(--line);border-radius:999px;padding:5px 12px 5px 6px}
.steps a i{width:18px;height:18px;border-radius:50%;background:var(--c);color:#0a0d13;font:700 11px var(--mono);display:inline-flex;align-items:center;justify-content:center;font-style:normal}
.steps a:hover{border-color:var(--c)}
.steps .arr{color:var(--faint);font-size:11px}
.step{display:grid;grid-template-columns:40px minmax(0,1fr);gap:16px;margin:0;padding:26px 0 4px;position:relative;scroll-margin-top:72px}
.step::before{content:"";position:absolute;left:19px;top:0;bottom:0;width:2px;background:var(--line)}
.step:first-of-type::before{top:34px}
.step:last-of-type::before{bottom:auto;height:34px}
.step .n{width:40px;height:40px;border-radius:50%;background:var(--bg);border:2px solid var(--c);color:var(--c);
  font:700 15px var(--mono);display:flex;align-items:center;justify-content:center;position:relative;z-index:1}
.step h2{margin:6px 0 10px!important;font-size:19px;color:var(--fg)}
.step .body{padding-bottom:6px}
/* 칸마다 다른 형태 */
.call.k-zap .body ol{counter-reset:z;list-style:none;padding-left:0}
.call.k-zap .body ol>li{counter-increment:z;position:relative;padding-left:2em;margin:.7em 0}
.call.k-zap .body ol>li::before{content:counter(z);position:absolute;left:0;top:.18em;width:1.5em;height:1.5em;border-radius:7px;background:var(--kc);color:#0a0d13;font:700 11px var(--mono);display:flex;align-items:center;justify-content:center}

.foot{margin-top:52px;padding-top:22px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.btn{font-size:13px;padding:9px 15px;border:1px solid var(--line);border-radius:8px;background:var(--s2);color:var(--fg2);cursor:pointer;line-height:1.3}
.btn:hover{border-color:var(--line2);color:var(--fg)}
.btn.on{background:var(--c);border-color:var(--c);color:#0a0d13;font-weight:700}
.btn.ghost{background:none}
.btn.next{margin-left:auto;border-color:var(--c);color:var(--c)}
.btn.next:hover{background:var(--c);color:#0a0d13}
.empty{color:var(--mute);border:1px dashed var(--line);border-radius:12px;padding:30px;text-align:center;font-size:13.5px}
mark{background:rgba(251,191,36,.28);color:inherit;padding:0 2px;border-radius:2px}

/* 검색 덮개 */
.ov{position:fixed;inset:0;background:rgba(6,8,12,.72);backdrop-filter:blur(6px);z-index:50;display:none;padding:9vh 16px 0;align-items:flex-start;justify-content:center}
.ov[data-open="1"]{display:flex}
.box{width:min(640px,100%);background:var(--s1);border:1px solid var(--line2);border-radius:14px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6)}
#q{width:100%;padding:16px 18px;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--fg);font:16px var(--sans);outline:none}
.hits{max-height:60vh;overflow-y:auto}
.hit{display:block;width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--line);padding:12px 18px;color:inherit;cursor:pointer}
.hit:hover,.hit.on{background:var(--s2)}
.hit .w{font:600 10.5px var(--mono);color:var(--mute)}
.hit .t{font-size:14.5px;font-weight:700;margin:2px 0 3px}
.hit .s{font-size:12.5px;color:var(--mute);line-height:1.6}
.hint{padding:9px 18px;font-size:11.5px;color:var(--faint);display:flex;gap:14px}
.hint kbd{background:var(--s3);padding:1px 5px;border-radius:4px;font-size:10px}
</style>

<div class="top"><div class="top-in">
  <button class="brand" id="brand" type="button">바이브마스터 <em>v2</em></button>
  <div class="segs" id="segs" aria-label="장별 진도"></div>
  <button class="sbtn" id="sopen" type="button"><span>검색</span><kbd>/</kbd></button>
</div></div>
<main class="page" id="main"></main>
<div class="ov" id="ov"><div class="box">
  <input id="q" type="search" placeholder="무엇을 찾으세요? — 되돌리기, 결제, 훅…" autocomplete="off">
  <div class="hits" id="hits"></div>
  <div class="hint"><span><kbd>↑</kbd><kbd>↓</kbd> 이동</span><span><kbd>Enter</kbd> 열기</span><span><kbd>Esc</kbd> 닫기</span></div>
</div></div>

<script type="application/json" id="data">__DATA__</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('data').textContent);
  var KEY = 'vm2-read-v1', read = {};
  try { read = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) { read = {}; }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(read)); } catch(e) {} }
  if (window.marked && marked.setOptions) marked.setOptions({gfm:true, breaks:false});
  function md(s){ return window.marked ? marked.parse(s||'') : '<pre>' + esc(s||'') + '</pre>'; }
  function esc(s){ return (s||'').replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  var $ = function(id){ return document.getElementById(id); };
  var main = $('main'), segs = $('segs'), ov = $('ov'), q = $('q'), hits = $('hits');

  // 칸 종류와 아이콘 (이모지 대신 선 아이콘)
  var ICON = {
    'k-say':  '<svg viewBox="0 0 24 24"><path d="M4 5h16v11H8l-4 4z"/></svg>',
    'k-trap': '<svg viewBox="0 0 24 24"><path d="M12 3 2 21h20z"/><path d="M12 10v5M12 18v.5"/></svg>',
    'k-zap':  '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
    'k-ok':   '<svg viewBox="0 0 24 24"><path d="M4 12l5 5L20 6"/></svg>',
    'k-deep': '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>'
  };
  function kind(t){
    if (t.indexOf('말 풀이') >= 0) return 'k-say';
    if (t.indexOf('함정') >= 0) return 'k-trap';
    if (t.indexOf('더 깊이') >= 0) return 'k-deep';
    if (t.indexOf('이렇게 하세요') >= 0 || t.indexOf('따라 하기') >= 0) return 'k-zap';
    if (t.indexOf('됐는지') >= 0 || t.indexOf('자가 체크') >= 0 || /^[✅\s]*확인$/.test(t)) return 'k-ok';
    return '';
  }
  function label(t){ return t.replace(/^[📘⚠️⚡✅🔎\s]+/, '').trim(); }
  function slug(i){ return 'k' + i; }

  // 주소: #장 / #장/절 — 한글은 인코딩돼 돌아오니 되돌린다
  function route(){
    var raw; try { raw = decodeURIComponent(location.hash.slice(1)); } catch(e){ raw = location.hash.slice(1); }
    var p = raw.split('/'); return { stage: p[0] || 'home', sec: p[1] || '' };
  }
  var cur = route();
  function stageOf(k){ return D.stages.filter(function(s){ return s.key === k; })[0]; }
  function isNum(k){ return /^\d/.test(k); }
  function tag(st){ return isNum(st.key) ? 'Stage ' + st.key : st.name; }
  function full(st){ return isNum(st.key) ? 'Stage ' + st.key + ' ' + st.name : st.name; }
  function counts(st){ var r = 0; st.sections.forEach(function(s){ if (read[s.id]) r++; }); return [r, st.sections.length]; }
  function setColor(c){ document.documentElement.style.setProperty('--c', c || '#60a5fa'); }

  function drawSegs(){
    segs.innerHTML = '';
    D.stages.forEach(function(st){
      var c = counts(st), b = document.createElement('button');
      b.className = 'seg'; b.type = 'button'; b.title = full(st) + (c[1] ? ' — ' + c[0] + '/' + c[1] : '');
      b.style.setProperty('--sc', st.color); b.style.setProperty('--p', (c[1] ? Math.round(c[0] / c[1] * 100) : 0) + '%');
      b.innerHTML = '<i></i>';
      b.setAttribute('aria-current', cur.stage === st.key ? 'true' : 'false');
      b.onclick = function(){ go(st.key); };
      segs.appendChild(b);
    });
  }

  // ── 홈: 여정 지도 ──
  var BANDS = { '0': '자리를 만든다', '1': '만들기 전에', '4': '보이는 것', '5': '돌아가게', '7': '내가 없어도', '10': '내놓는다', '자동화': '따로 — 회사 일' };
  function homeView(){
    setColor('#60a5fa');
    var done = 0, all = 0;
    D.stages.forEach(function(st){ var c = counts(st); done += c[0]; all += c[1]; });
    var h = '<section class="hero"><h1>한 사람이 웹서비스 하나를<br>만들어 내놓기까지</h1>' +
      '<p>직장인·비개발자를 위한 14장. 앞 장에서 만든 것이 뒤 장의 재료가 됩니다. 순서대로 가는 것이 가장 빠르지만, 막히면 어디로든 건너뛰어도 됩니다 — 모든 절이 서로 이어져 있습니다.</p>' +
      '<div class="prog"><b>' + done + '</b> / ' + all + ' 절 읽음</div></section><div class="grid">';
    D.stages.forEach(function(st){
      if (BANDS[st.key]) h += '<div class="band" style="--bc:' + st.color + '"><i></i>' + esc(BANDS[st.key]) + '</div>';
      var c = counts(st), p = c[1] ? Math.round(c[0] / c[1] * 100) : 0;
      h += '<button class="scard' + (c[1] && c[0] === c[1] ? ' done' : '') + '" type="button" data-k="' + esc(st.key) + '" style="--sc:' + st.color + ';--p:' + p + '%">' +
           '<div class="num"><i></i>' + esc(tag(st)) + '</div><h3>' + esc(st.name) + '</h3>' +
           '<p class="goal">' + esc(st.goal || '') + '</p>' +
           '<div class="foot"><div class="bar"><i></i></div><span>' + (c[1] ? c[0] + ' / ' + c[1] + ' 절' : '준비 중') + '</span></div></button>';
    });
    main.innerHTML = h + '</div>';
    main.querySelectorAll('[data-k]').forEach(function(b){ b.onclick = function(){ go(b.dataset.k); }; });
  }

  // ── 장: 절 카드 ──
  function stageView(st){
    setColor(st.color);
    var c = counts(st), i = D.stages.indexOf(st), nx = D.stages[i + 1];
    var h = '<div class="shero" data-n="' + esc(isNum(st.key) ? st.key : '') + '"><div class="crumbs"><button type="button" data-home="1">여정 지도</button><span>/</span><b>' + esc(full(st)) + '</b></div>' +
      '<h1>' + (isNum(st.key) ? '<small>Stage ' + esc(st.key) + '</small>' : '') + esc(st.name) + (st.sub ? ' — ' + esc(st.sub) : '') + '</h1>';
    if (st.goal) h += '<p class="goalline">' + esc(st.goal) + '</p>';
    var ch = [];
    if (st.makes) ch.push('<span class="chip"><b>만드는 것</b>' + esc(st.makes) + '</span>');
    if (st.time) ch.push('<span class="chip"><b>시간</b>' + esc(st.time) + '</span>');
    (st.need || []).forEach(function(n){ if (n) ch.push('<span class="chip"><b>준비물</b>' + esc(n) + '</span>'); });
    if (c[1]) ch.push('<span class="chip"><b>진도</b>' + c[0] + ' / ' + c[1] + '</span>');
    if (ch.length) h += '<div class="chips">' + ch.join('') + '</div>';
    h += '</div>';
    if (st.head) h += '<div class="intro body">' + md(st.head) + '</div>';
    if (st.sections.length) {
      h += '<div class="sgrid">';
      st.sections.forEach(function(s){
        h += '<button class="ccard' + (read[s.id] ? ' done' : '') + '" type="button" data-sec="' + s.id + '">' +
             '<div class="no"><span>' + (s.no ? '<em>' + esc(String(s.no)) + '</em>' : '') + (s.time ? esc(s.time) : '') + '</span>' +
             (read[s.id] ? '<span class="rd">읽음</span>' : '') + '</div>' +
             '<h4>' + esc(s.title) + '</h4>' + (s.through ? '<p>' + esc(s.through) + '</p>' : '') + '</button>';
      });
      h += '</div>';
    } else h += '<div class="empty">이 장은 아직 쓰는 중입니다.</div>';
    (st.metasecs || []).forEach(function(k){ h += callout(k); });
    h += '<div class="foot"><button class="btn ghost" type="button" data-home="1">여정 지도로</button>' +
         (nx ? '<button class="btn next" type="button" data-k="' + esc(nx.key) + '">다음 장 · ' + esc(nx.name) + '</button>' : '') + '</div>';
    main.innerHTML = h;
    main.querySelectorAll('[data-sec]').forEach(function(b){ b.onclick = function(){ go(st.key, b.dataset.sec); }; });
    main.querySelectorAll('[data-k]').forEach(function(b){ b.onclick = function(){ go(b.dataset.k); }; });
    main.querySelectorAll('[data-home]').forEach(function(b){ b.onclick = function(){ go('home'); }; });
    wire();
  }
  function callout(k, id){
    var cls = kind(k.title) || 'k-say';
    return '<div class="call ' + cls + '"' + (id ? ' id="' + id + '"' : '') + '><b>' + ICON[cls] + esc(label(k.title)) + '</b><div class="body">' + md(k.md) + '</div></div>';
  }

  // ── 절: 본문 + 오른쪽 안내 ──
  function secView(st, sec){
    setColor(st.color);
    var idx = st.sections.indexOf(sec), pv = st.sections[idx - 1], nx = st.sections[idx + 1];
    var h = '<div class="crumbs"><button type="button" data-home="1">여정 지도</button><span>/</span>' +
            '<button type="button" data-k="' + esc(st.key) + '">' + esc(full(st)) + '</button><span>/</span><b>' + (sec.no ? esc(String(sec.no)) + '절' : '') + '</b></div>' +
            '<div class="two"><article class="art"><h1>' + esc(sec.title) + '</h1>';
    if (sec.through) h += '<div class="through">' + esc(sec.through) + '</div>';
    var rail = [];
    if (sec.goals && sec.goals.length) h += '<div class="goals"><b>이 절을 마치면</b><ul>' + sec.goals.map(function(g){ return '<li>' + esc(g) + '</li>'; }).join('') + '</ul></div>';
    var stepSecs = sec.secs.filter(function(k){ return !kind(k.title); });
    if (stepSecs.length > 1) {
      h += '<div class="steps">' + stepSecs.map(function(k, i){
        return (i ? '<span class="arr">›</span>' : '') + '<a href="#s' + i + '" data-j="s' + i + '"><i>' + (i + 1) + '</i>' + esc(k.title.replace(/^[①②③④⑤⑥⑦⑧⑨⑩\s]+/, '')) + '</a>';
      }).join('') + '</div>';
    }
    if (sec.head) h += '<div class="body">' + md(sec.head) + '</div>';
    var si = 0;
    // 세부 내용(번호 단계)을 먼저, 그다음 따라 하기 → 확인 → 참고 순으로 고정
    var order = ['', 'k-zap', 'k-ok', 'k-say', 'k-trap', 'k-deep'];
    order.forEach(function(want){
      sec.secs.forEach(function(k){
        var cls = kind(k.title); if (cls !== want) return;
        if (!cls) {
          var id = 's' + si, t = k.title.replace(/^[①②③④⑤⑥⑦⑧⑨⑩\s]+/, '');
          rail.push({ id: id, t: (si + 1) + '. ' + t });
          h += '<section class="step" id="' + id + '"><div class="n">' + (si + 1) + '</div><div class="body"><h2>' + esc(t) + '</h2>' + md(k.md) + '</div></section>';
          si++;
        } else {
          var id2 = cls; rail.push({ id: id2, t: label(k.title) });
          h += callout(k, id2);
        }
      });
    });
    h += '<div class="foot">' +
         (pv ? '<button class="btn ghost" type="button" data-sec="' + pv.id + '">← ' + esc(pv.title) + '</button>' : '<button class="btn ghost" type="button" data-k="' + esc(st.key) + '">← 장으로</button>') +
         (nx ? '<button class="btn next" type="button" data-sec="' + nx.id + '">다음 · ' + esc(nx.title) + '</button>'
             : '<button class="btn next" type="button" data-k="' + esc(st.key) + '">장으로 돌아가기</button>') +
         '</div></article>' +
         '<aside class="rail"><p class="rt">이 절 안에서</p>' +
         rail.map(function(r){ return '<a href="#' + r.id + '" data-j="' + r.id + '">' + esc(r.t) + '</a>'; }).join('') +
         '<div class="sep"></div>' +
         '<button class="btn' + (read[sec.id] ? ' on' : '') + '" type="button" data-mark="' + sec.id + '">' + (read[sec.id] ? '✓ 읽음' : '읽음으로 표시') + '</button>' +
         '<p class="rt" style="margin-top:14px">' + (idx + 1) + ' / ' + st.sections.length + ' · <kbd>←</kbd><kbd>→</kbd> 로 이동</p></aside></div>';
    main.innerHTML = h;
    main.querySelectorAll('[data-sec]').forEach(function(b){ b.onclick = function(){ go(st.key, b.dataset.sec); }; });
    main.querySelectorAll('[data-k]').forEach(function(b){ b.onclick = function(){ go(b.dataset.k); }; });
    main.querySelectorAll('[data-home]').forEach(function(b){ b.onclick = function(){ go('home'); }; });
    main.querySelectorAll('[data-j]').forEach(function(a){
      a.onclick = function(e){ e.preventDefault(); var el = $(a.dataset.j); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
    });
    main.querySelectorAll('[data-mark]').forEach(function(b){
      b.onclick = function(){
        var id = b.dataset.mark; if (read[id]) delete read[id]; else read[id] = 1; save();
        b.classList.toggle('on', !!read[id]); b.textContent = read[id] ? '✓ 읽음' : '읽음으로 표시'; drawSegs();
      };
    });
    wire();
    // 읽는 위치를 오른쪽 안내에 비춘다
    var links = main.querySelectorAll('.rail a[data-j]');
    if ('IntersectionObserver' in window && links.length) {
      var io = new IntersectionObserver(function(es){
        es.forEach(function(e){ if (e.isIntersecting) { links.forEach(function(l){ l.classList.toggle('on', l.dataset.j === e.target.id); }); } });
      }, { rootMargin: '-60px 0px -70% 0px' });
      rail.forEach(function(r){ var el = $(r.id); if (el) io.observe(el); });
    }
    keys = { prev: pv ? function(){ go(st.key, pv.id); } : null, next: nx ? function(){ go(st.key, nx.id); } : null };
  }
  var keys = {};

  function wire(){
    main.querySelectorAll('.xref').forEach(function(a){
      a.onclick = function(e){ e.preventDefault(); go(a.getAttribute('href').replace('#', ''), a.dataset.jump || ''); };
    });
    main.querySelectorAll('pre').forEach(function(p){
      var code = p.innerText, btn = document.createElement('button');
      btn.className = 'copy'; btn.type = 'button'; btn.textContent = '복사';
      btn.onclick = function(){
        navigator.clipboard.writeText(code).then(function(){ btn.textContent = '복사됨'; setTimeout(function(){ btn.textContent = '복사'; }, 1400); },
                                                 function(){ btn.textContent = '실패'; });
      };
      p.appendChild(btn);
    });
  }

  function go(k, secId){
    cur = { stage: k, sec: secId || '' }; keys = {};
    var want = k + (secId ? '/' + secId : ''), now;
    try { now = decodeURIComponent(location.hash.slice(1)); } catch(e){ now = location.hash.slice(1); }
    // 샌드박스 안에서는 주소 변경이 막힐 수 있다. 막혀도 화면은 바뀌어야 한다.
    if (now !== want) { try { history.replaceState(null, '', '#' + want); } catch(e){ try { location.hash = want; } catch(e2){} } }
    closeSearch(); drawSegs();
    if (k === 'home') homeView();
    else {
      var st = stageOf(k);
      if (!st) homeView();
      else if (secId) { var sec = st.sections.filter(function(s){ return s.id === secId; })[0]; sec ? secView(st, sec) : stageView(st); }
      else stageView(st);
    }
    window.scrollTo(0, 0);
  }

  // ── 검색 덮개 ──
  var idx = [], sel = 0, shown = [];
  D.stages.forEach(function(st){ st.sections.forEach(function(s){
    var text = [s.title, s.through, s.head].concat(s.secs.map(function(k){ return k.title + ' ' + k.md; })).join(' ');
    idx.push({ stage: st, sec: s, raw: text, low: text.toLowerCase() });
  }); });
  function openSearch(){ ov.dataset.open = '1'; q.value = ''; hits.innerHTML = ''; setTimeout(function(){ q.focus(); }, 0); }
  function closeSearch(){ ov.dataset.open = '0'; }
  function render(){
    var lq = q.value.toLowerCase().trim(); hits.innerHTML = ''; shown = []; sel = 0;
    if (!lq) return;
    shown = idx.filter(function(r){ return r.low.indexOf(lq) >= 0; }).slice(0, 12);
    if (!shown.length) { hits.innerHTML = '<div class="hit"><div class="s">찾은 것이 없습니다. 다른 말로 찾아보세요.</div></div>'; return; }
    shown.forEach(function(r, i){
      var p = r.low.indexOf(lq), snip = esc(r.raw.substr(Math.max(0, p - 45), 130))
        .replace(new RegExp(esc(q.value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'), function(m){ return '<mark>' + m + '</mark>'; });
      var b = document.createElement('button'); b.className = 'hit' + (i === 0 ? ' on' : ''); b.type = 'button';
      b.innerHTML = '<div class="w">' + esc(full(r.stage)) + '</div><div class="t">' + esc(r.sec.title) + '</div><div class="s">…' + snip + '…</div>';
      b.onclick = function(){ go(r.stage.key, r.sec.id); };
      hits.appendChild(b);
    });
  }
  var t; q.addEventListener('input', function(){ clearTimeout(t); t = setTimeout(render, 120); });
  q.addEventListener('keydown', function(e){
    var items = hits.querySelectorAll('.hit');
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); if (!shown.length) return;
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + shown.length) % shown.length;
      items.forEach(function(it, i){ it.classList.toggle('on', i === sel); });
      items[sel].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter' && shown[sel]) { go(shown[sel].stage.key, shown[sel].sec.id); }
    else if (e.key === 'Escape') closeSearch();
  });
  ov.addEventListener('click', function(e){ if (e.target === ov) closeSearch(); });
  $('sopen').onclick = openSearch;
  $('brand').onclick = function(){ go('home'); };
  document.addEventListener('keydown', function(e){
    if (e.target === q) return;
    if (e.key === '/' && !e.metaKey && !e.ctrlKey) { e.preventDefault(); openSearch(); }
    else if (e.key === 'Escape') closeSearch();
    else if (e.key === 'ArrowRight' && keys.next && !e.altKey) keys.next();
    else if (e.key === 'ArrowLeft' && keys.prev && !e.altKey) keys.prev();
  });
  window.addEventListener('hashchange', function(){ var r = route(); if (r.stage !== cur.stage || r.sec !== cur.sec) go(r.stage, r.sec); });
  go(cur.stage, cur.sec);
})();
</script>'''
html = (TPL.replace('__DATE__', datetime.date.today().isoformat())
           .replace('__DATA__', json.dumps({'stages': stages}, ensure_ascii=False).replace('</', '<\\/')))
open(OUT, 'w', encoding='utf-8').write(html)
print(f'✅ {OUT}  ({len(html)//1024}KB) · Stage {len(stages)}개 · 절 {total}개')
