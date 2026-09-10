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
    ('00-환경',          '0',      '환경',            '#1F7A5C'),
    ('01-시장',          '1',      '시장',            '#2C5FA8'),
    ('02-명세',          '2',      '명세',            '#2C5FA8'),
    ('03-컨텍스트하네스', '3',      '컨텍스트·하네스',  '#2C5FA8'),
    ('04-디자인',        '4',      '디자인',          '#B0533A'),
    ('045-버전관리',     '4.5',    '버전 관리',       '#B0533A'),
    ('05-구현',          '5',      '구현',            '#7A3E9D'),
    ('06-서버결제',      '6',      '서버·인증·결제',   '#7A3E9D'),
    ('07-배포PR',        '7',      '배포·PR',         '#7A3E9D'),
    ('08-자율운영',      '8',      '자율 운영',        '#3B6E8F'),
    ('09-지식운영',      '9',      '지식 운영',        '#3B6E8F'),
    ('10-판매',          '10',     '판매',            '#3B6E8F'),
    ('업무자동화',       '자동화',  '업무 자동화',      '#8A6D1F'),
    ('부록',             '부록',    '부록',            '#5A5A5A'),
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#FBFAF8;--fg:#1C1B19;--dim:#6B675F;--line:#E3DFD7;--card:#FFFFFF;--accent:#1F7A5C;--mark:#FFF3C4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161513;--fg:#EDEAE3;--dim:#9C978C;--line:#2E2C28;--card:#1E1D1A;--mark:#4A3F18}}
:root[data-theme="dark"]{--bg:#161513;--fg:#EDEAE3;--dim:#9C978C;--line:#2E2C28;--card:#1E1D1A;--mark:#4A3F18}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 'Noto Sans KR',-apple-system,BlinkMacSystemFont,sans-serif;-webkit-text-size-adjust:100%}
code,pre{font-family:'IBM Plex Mono',ui-monospace,monospace}
.wrap{display:grid;grid-template-columns:250px minmax(0,1fr);gap:0;max-width:1180px;margin:0 auto}
@media(max-width:820px){.wrap{grid-template-columns:1fr}}
/* 사이드 */
aside{border-right:1px solid var(--line);padding:20px 14px 60px;position:sticky;top:0;height:100vh;overflow-y:auto}
@media(max-width:820px){aside{position:static;height:auto;border-right:none;border-bottom:1px solid var(--line)}}
aside h1{font-size:16px;margin:0 0 2px;letter-spacing:-.02em}
aside .ver{font-size:12px;color:var(--dim);margin-bottom:14px}
#q{width:100%;padding:9px 11px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:14px 'Noto Sans KR',sans-serif}
#q:focus{outline:2px solid var(--accent);outline-offset:1px}
.navlist{margin-top:14px;display:flex;flex-direction:column;gap:1px}
.navitem{display:flex;gap:9px;align-items:baseline;padding:7px 9px;border-radius:7px;cursor:pointer;font-size:14px;border:none;background:none;color:var(--fg);text-align:left;width:100%;font-family:inherit}
.navitem:hover{background:var(--card)}
.navitem[aria-current="true"]{background:var(--card);font-weight:700;box-shadow:inset 3px 0 0 var(--sc,var(--accent))}
.navitem .k{font-size:11px;color:var(--dim);min-width:26px;font-family:'IBM Plex Mono',monospace}
.navitem .done{margin-left:auto;font-size:11px;color:var(--dim)}
/* 본문 */
main{padding:34px 30px 120px;min-width:0}
@media(max-width:820px){main{padding:24px 16px 90px}}
.chip{display:inline-block;font-size:11px;letter-spacing:.08em;padding:3px 9px;border-radius:999px;background:var(--sc);color:#fff;font-weight:700}
h2.st{font-size:27px;margin:12px 0 4px;letter-spacing:-.02em;line-height:1.3}
.sub{color:var(--dim);font-size:15px;margin-bottom:18px}
.goal{border-left:3px solid var(--sc);padding:10px 0 10px 15px;margin:18px 0;font-size:16px}
.goal b{display:block;font-size:11px;letter-spacing:.09em;color:var(--dim);margin-bottom:3px;font-weight:700}
.meta{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 22px}
.meta span{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:4px 9px;color:var(--dim);background:var(--card)}
.sec{border:1px solid var(--line);border-radius:11px;background:var(--card);padding:18px 20px;margin:14px 0}
@media(max-width:820px){.sec{padding:15px 14px}}
.sec>h3{margin:0 0 3px;font-size:19px;letter-spacing:-.01em;line-height:1.4}
.sec .through{margin:6px 0 14px;padding:9px 13px;background:var(--bg);border-radius:8px;font-size:15px;font-weight:500;border-left:3px solid var(--sc)}
.sec h4{margin:20px 0 6px;font-size:15px;letter-spacing:-.01em}
.sec h4:first-of-type{margin-top:12px}
.body p{margin:9px 0}.body ul,.body ol{margin:9px 0;padding-left:22px}.body li{margin:4px 0}
.body a{color:var(--accent)}
.body table{border-collapse:collapse;width:100%;font-size:14px;margin:11px 0;display:block;overflow-x:auto}
.body th,.body td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
.body th{background:var(--bg);font-weight:700;white-space:nowrap}
.body code{background:var(--bg);padding:1px 5px;border-radius:4px;font-size:.9em;word-break:break-all}
.body pre{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow-x:auto;position:relative}
.body pre code{background:none;padding:0;font-size:13px;word-break:normal}
.body blockquote{margin:11px 0;padding:2px 0 2px 14px;border-left:3px solid var(--line);color:var(--dim)}
.copy{position:absolute;top:7px;right:7px;font-size:11px;padding:3px 8px;border:1px solid var(--line);border-radius:5px;background:var(--card);color:var(--dim);cursor:pointer;font-family:inherit}
.copy:hover{color:var(--fg)}
/* 특수 칸 */
.k-say{background:#F2F7FF;border-color:#C9DCF5}.k-trap{background:#FFF6F3;border-color:#F2CFC3}
.k-deep{background:#F5F2FA;border-color:#DCD2EA}.k-zap{background:#F3FAF6;border-color:#C7E5D6}
.k-ok{background:#FFFBEE;border-color:#EDDFB0}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .k-say{background:#141B26;border-color:#26374F}
:root:not([data-theme="light"]) .k-trap{background:#241715;border-color:#4A2A22}
:root:not([data-theme="light"]) .k-deep{background:#1B1622;border-color:#352A44}
:root:not([data-theme="light"]) .k-zap{background:#12201A;border-color:#234436}
:root:not([data-theme="light"]) .k-ok{background:#211D10;border-color:#43391C}}
.kbox{border:1px solid var(--line);border-radius:9px;padding:13px 16px;margin:14px 0}
.kbox>b{display:block;font-size:13px;margin-bottom:5px;letter-spacing:-.01em}
/* 진도 */
.readbtn{margin-top:15px;font-size:13px;padding:7px 14px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--dim);cursor:pointer;font-family:inherit}
.readbtn[data-on="1"]{background:var(--sc);border-color:var(--sc);color:#fff;font-weight:700}
.progress{height:4px;background:var(--line);border-radius:99px;overflow:hidden;margin:16px 0 4px}
.progress i{display:block;height:100%;background:var(--sc);transition:width .25s}
.ptext{font-size:12px;color:var(--dim)}
mark{background:var(--mark);color:inherit;padding:0 2px;border-radius:3px}
.empty{color:var(--dim);border:1px dashed var(--line);border-radius:11px;padding:26px;text-align:center;font-size:14px}
.toctbl{width:100%;border-collapse:collapse;font-size:14px;margin:16px 0;display:block;overflow-x:auto}
.toctbl th,.toctbl td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.toctbl th{background:var(--card);font-weight:700;white-space:nowrap}
.toctbl td:first-child{white-space:nowrap;font-weight:700}
.hitstage{font-size:11px;color:var(--dim);letter-spacing:.06em}
.xref{color:var(--accent);text-decoration:underline;text-underline-offset:2px;cursor:pointer}
.egfile{color:var(--dim);font-family:'IBM Plex Mono',monospace;font-size:.92em}
</style>
<div class="wrap">
<aside>
  <h1>바이브마스터 <span style="color:var(--accent)">버전2</span></h1>
  <div class="ver">웹서비스 개발 · 빌드 __DATE__</div>
  <input id="q" type="search" placeholder="검색 — 훅, 결제, 되돌리기…" autocomplete="off">
  <div class="navlist" id="nav"></div>
</aside>
<main id="main"></main>
</div>
<script type="application/json" id="data">__DATA__</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('data').textContent);
  var KEY = 'vm2-read-v1';
  var read = {};
  try { read = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) { read = {}; }
  function save(){ try { localStorage.setItem(KEY, JSON.stringify(read)); } catch(e) {} }
  if (window.marked && marked.setOptions) marked.setOptions({gfm:true, breaks:false});
  function md(s){ return window.marked ? marked.parse(s||'') : '<pre>' + esc(s||'') + '</pre>'; }
  function esc(s){ return (s||'').replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  // 칸 제목 → 상자 종류
  function kind(t){
    if (t.indexOf('말 풀이') >= 0) return 'k-say';
    if (t.indexOf('함정') >= 0) return 'k-trap';
    if (t.indexOf('더 깊이') >= 0) return 'k-deep';
    if (t.indexOf('이렇게 하세요') >= 0) return 'k-zap';
    if (t.indexOf('됐는지') >= 0 || t.indexOf('자가 체크') >= 0) return 'k-ok';
    return '';
  }

  // 한글 스테이지 이름은 주소창에서 인코딩돼 돌아온다. 반드시 되돌려 읽는다.
  function hashKey(){
    try { return decodeURIComponent(location.hash.slice(1)); }
    catch (e) { return location.hash.slice(1); }
  }
  var cur = hashKey() || 'home';
  var nav = document.getElementById('nav'), main = document.getElementById('main');

  function counts(st){
    var n = st.sections.length, r = 0;
    st.sections.forEach(function(s){ if (read[s.id]) r++; });
    return [r, n];
  }

  function drawNav(){
    nav.innerHTML = '';
    var home = document.createElement('button');
    home.className = 'navitem'; home.type = 'button';
    home.innerHTML = '<span class="k">☰</span><span>전체 목차</span>';
    home.setAttribute('aria-current', cur === 'home' ? 'true' : 'false');
    home.onclick = function(){ go('home'); };
    nav.appendChild(home);
    D.stages.forEach(function(st){
      var b = document.createElement('button');
      b.className = 'navitem'; b.type = 'button';
      b.style.setProperty('--sc', st.color);
      var c = counts(st);
      b.innerHTML = '<span class="k">' + esc(st.key) + '</span><span>' + esc(st.name) + '</span>' +
                    '<span class="done">' + (c[1] ? c[0] + '/' + c[1] : '—') + '</span>';
      b.setAttribute('aria-current', cur === st.key ? 'true' : 'false');
      b.onclick = function(){ go(st.key); };
      nav.appendChild(b);
    });
  }

  function homeView(){
    var rows = D.stages.map(function(st){
      var c = counts(st);
      return '<tr><td style="color:' + st.color + '">' + esc(st.key) + ' ' + esc(st.name) + '</td>' +
             '<td>' + esc(st.goal || '—') + '</td>' +
             '<td>' + esc(st.makes || '—') + '</td>' +
             '<td class="hitstage">' + (c[1] ? c[0] + ' / ' + c[1] + ' 절' : '준비 중') + '</td></tr>';
    }).join('');
    var done = 0, all = 0;
    D.stages.forEach(function(st){ var c = counts(st); done += c[0]; all += c[1]; });
    main.innerHTML =
      '<span class="chip" style="--sc:#1F7A5C">전체 목차</span>' +
      '<h2 class="st">한 사람이 웹서비스 하나를 만들어 내놓기까지</h2>' +
      '<div class="sub">앞 장에서 나온 것이 뒤 장의 재료가 됩니다. 순서대로 가는 것이 가장 빠릅니다.</div>' +
      '<div class="progress" style="--sc:#1F7A5C"><i style="width:' + (all ? Math.round(done / all * 100) : 0) + '%"></i></div>' +
      '<div class="ptext">' + done + ' / ' + all + ' 절 읽음</div>' +
      '<table class="toctbl"><thead><tr><th>장</th><th>학습 목적</th><th>만드는 것</th><th>진도</th></tr></thead><tbody>' +
      rows + '</tbody></table>' +
      '<div class="kbox k-ok"><b>✅ 자가 체크가 붙어 있습니다</b>각 장 끝에 예·아니오로 답하는 체크가 있습니다. ' +
      '하나라도 «아니오»면 다음 장으로 가지 말고 그 절로 돌아갑니다.</div>';
  }

  function stageView(st){
    var h = '<span class="chip" style="--sc:' + st.color + '">Stage ' + esc(st.key) + '</span>' +
            '<h2 class="st">' + esc(st.name) + (st.sub ? ' — ' + esc(st.sub) : '') + '</h2>';
    if (st.goal) h += '<div class="goal" style="--sc:' + st.color + '"><b>학습 목적</b>' + esc(st.goal) + '</div>';
    var m = [];
    if (st.makes) m.push('만드는 것 · ' + st.makes);
    if (st.time) m.push('걸리는 시간 · ' + st.time);
    (st.need || []).forEach(function(n){ if (n) m.push('준비물 · ' + n); });
    if (m.length) h += '<div class="meta">' + m.map(function(x){ return '<span>' + esc(x) + '</span>'; }).join('') + '</div>';
    if (st.head) h += '<div class="body">' + md(st.head) + '</div>';

    if (!st.sections.length) {
      h += '<div class="empty">이 장은 아직 쓰는 중입니다.</div>';
    }
    st.sections.forEach(function(s){
      h += '<article class="sec" id="' + s.id + '" style="--sc:' + st.color + '">' +
           '<h3>' + (s.no ? esc(s.no) + '. ' : '') + esc(s.title) + '</h3>';
      if (s.through) h += '<div class="through" style="--sc:' + st.color + '">' + esc(s.through) + '</div>';
      var sm = [];
      if (s.time) sm.push('소요 · ' + s.time);
      (s.need || []).forEach(function(n){ if (n) sm.push('준비물 · ' + n); });
      if (sm.length) h += '<div class="meta">' + sm.map(function(x){ return '<span>' + esc(x) + '</span>'; }).join('') + '</div>';
      if (s.head) h += '<div class="body">' + md(s.head) + '</div>';
      s.secs.forEach(function(k){
        var cls = kind(k.title);
        h += cls ? '<div class="kbox ' + cls + '"><b>' + esc(k.title) + '</b><div class="body">' + md(k.md) + '</div></div>'
                 : '<h4>' + esc(k.title) + '</h4><div class="body">' + md(k.md) + '</div>';
      });
      h += '<button class="readbtn" type="button" data-id="' + s.id + '" data-on="' + (read[s.id] ? '1' : '0') + '">' +
           (read[s.id] ? '✓ 읽음' : '읽음으로 표시') + '</button></article>';
    });

    // 스테이지 자가 체크·다음으로 (_스테이지.md 의 ## 칸)
    (st.metasecs || []).forEach(function(k){
      var cls = kind(k.title);
      h += '<div class="kbox ' + (cls || '') + '"><b>' + esc(k.title) + '</b><div class="body">' + md(k.md) + '</div></div>';
    });
    main.innerHTML = h;

    main.querySelectorAll('.readbtn').forEach(function(b){
      b.onclick = function(){
        var id = b.dataset.id;
        if (read[id]) { delete read[id]; } else { read[id] = 1; }
        save();
        b.dataset.on = read[id] ? '1' : '0';
        b.textContent = read[id] ? '✓ 읽음' : '읽음으로 표시';
        drawNav();
      };
    });
    main.querySelectorAll('.xref').forEach(function(a){
      a.onclick = function(e){
        e.preventDefault();
        go(a.getAttribute('href').replace('#', ''));
        var el = document.getElementById(a.dataset.jump);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      };
    });
    main.querySelectorAll('pre').forEach(function(p){
      var code = p.innerText;   // 버튼을 붙이기 전에 기억한다. 안 그러면 '복사'가 딸려 간다
      var btn = document.createElement('button');
      btn.className = 'copy'; btn.type = 'button'; btn.textContent = '복사';
      btn.onclick = function(){
        navigator.clipboard.writeText(code).then(function(){
          btn.textContent = '복사됨'; setTimeout(function(){ btn.textContent = '복사'; }, 1400);
        }, function(){ btn.textContent = '실패'; });
      };
      p.appendChild(btn);
    });
  }

  function go(k){
    cur = k;
    if (hashKey() !== k) location.hash = k;
    drawNav();
    if (k === 'home') { homeView(); }
    else {
      var st = D.stages.filter(function(s){ return s.key === k; })[0];
      st ? stageView(st) : homeView();
    }
    window.scrollTo(0, 0);
    document.getElementById('q').value = '';
  }

  // ── 검색: 페이지 안에서. 외부 빌드에 맡기지 않는다 (v1이 그래서 죽었다) ──
  var idx = [];
  D.stages.forEach(function(st){
    st.sections.forEach(function(s){
      var text = [s.title, s.through, s.head].concat(s.secs.map(function(k){ return k.title + ' ' + k.md; })).join(' ');
      idx.push({ stage: st, sec: s, low: text.toLowerCase() });
    });
  });
  function search(q){
    var lq = q.toLowerCase().trim();
    if (!lq) { go(cur); return; }
    var hits = idx.filter(function(r){ return r.low.indexOf(lq) >= 0; }).slice(0, 40);
    var h = '<span class="chip" style="--sc:#6B675F">검색</span><h2 class="st">「' + esc(q) + '」 ' + hits.length + '건</h2>';
    if (!hits.length) h += '<div class="empty">찾은 것이 없습니다. 다른 말로 찾아보세요.</div>';
    hits.forEach(function(r){
      var p = r.low.indexOf(lq), raw = [r.sec.title, r.sec.through, r.sec.head]
        .concat(r.sec.secs.map(function(k){ return k.title + ' ' + k.md; })).join(' ');
      var snip = esc(raw.substr(Math.max(0, p - 60), 190)).replace(new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'ig'), function(m){ return '<mark>' + m + '</mark>'; });
      h += '<article class="sec" style="--sc:' + r.stage.color + '">' +
           '<div class="hitstage">Stage ' + esc(r.stage.key) + ' · ' + esc(r.stage.name) + '</div>' +
           '<h3>' + esc(r.sec.title) + '</h3><div class="body"><p>…' + snip + '…</p></div>' +
           '<button class="readbtn" type="button" data-go="' + r.stage.key + '" data-at="' + r.sec.id + '">이 절로 가기</button></article>';
    });
    main.innerHTML = h;
    main.querySelectorAll('[data-go]').forEach(function(b){
      b.onclick = function(){
        go(b.dataset.go);
        var el = document.getElementById(b.dataset.at);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      };
    });
  }
  var t;
  document.getElementById('q').addEventListener('input', function(e){
    clearTimeout(t); var v = e.target.value;
    t = setTimeout(function(){ search(v); }, 160);
  });
  window.addEventListener('hashchange', function(){
    var k = hashKey() || 'home';
    if (k !== cur) go(k);
  });
  go(cur);
})();
</script>'''

html = (TPL.replace('__DATE__', datetime.date.today().isoformat())
           .replace('__DATA__', json.dumps({'stages': stages}, ensure_ascii=False).replace('</', '<\\/')))
open(OUT, 'w', encoding='utf-8').write(html)
print(f'✅ {OUT}  ({len(html)//1024}KB) · Stage {len(stages)}개 · 절 {total}개')
