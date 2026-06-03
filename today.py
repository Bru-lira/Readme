import datetime
from dateutil import relativedelta
import requests
import os
from xml.etree import ElementTree as ET

# ─── Config ────────────────────────────────────────────────────────────────────
HEADERS = {'Authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ.get('USER_NAME', 'Bru-lira')

# ─── Data fetchers ─────────────────────────────────────────────────────────────

def gql(query, variables=None):
    r = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': variables or {}},
        headers=HEADERS
    )
    if r.status_code != 200:
        raise Exception(f'GraphQL error {r.status_code}: {r.text}')
    return r.json()

def get_user():
    q = '''
    query($login: String!) {
      user(login: $login) {
        name
        createdAt
        followers { totalCount }
        repositories(ownerAffiliations: [OWNER], isFork: false) {
          totalCount
        }
      }
    }'''
    data = gql(q, {'login': USER_NAME})['data']['user']
    return data

def get_stars():
    stars = 0
    cursor = None
    while True:
        q = '''
        query($login: String!, $cursor: String) {
          user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: [OWNER]) {
              edges { node { stargazers { totalCount } } }
              pageInfo { endCursor hasNextPage }
            }
          }
        }'''
        data = gql(q, {'login': USER_NAME, 'cursor': cursor})['data']['user']['repositories']
        for edge in data['edges']:
            stars += edge['node']['stargazers']['totalCount']
        if not data['pageInfo']['hasNextPage']:
            break
        cursor = data['pageInfo']['endCursor']
    return stars

def get_commits():
    """Sum contributions over all years since account creation, in 1-year windows."""
    q_user = '''query($login: String!) { user(login: $login) { createdAt } }'''
    created = gql(q_user, {'login': USER_NAME})['data']['user']['createdAt']
    start_year = int(created[:4])
    current_year = datetime.datetime.utcnow().year

    total = 0
    q = '''
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
        }
      }
    }'''
    for year in range(start_year, current_year + 1):
        frm = f'{year}-01-01T00:00:00Z'
        to  = f'{year}-12-31T23:59:59Z'
        data = gql(q, {'login': USER_NAME, 'from': frm, 'to': to})
        total += data['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
    return total

def get_account_age(created_at):
    created = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
    diff = relativedelta.relativedelta(datetime.datetime.utcnow(), created)
    parts = []
    if diff.years:  parts.append(f'{diff.years} ano{"s" if diff.years != 1 else ""}')
    if diff.months: parts.append(f'{diff.months} {"meses" if diff.months != 1 else "mês"}')
    if diff.days:   parts.append(f'{diff.days} dia{"s" if diff.days != 1 else ""}')
    return ', '.join(parts) if parts else '0 dias'

# ─── SVG generator ─────────────────────────────────────────────────────────────

ASCII_ART = r"""
  ██████╗ ██████╗ ██╗   ██╗
  ██╔══██╗██╔══██╗██║   ██║
  ██████╔╝██████╔╝██║   ██║
  ██╔══██╗██╔══██╗██║   ██║
  ██████╔╝██║  ██║╚██████╔╝
  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝

  ██╗     ██╗██████╗  █████╗
  ██║     ██║██╔══██╗██╔══██╗
  ██║     ██║██████╔╝███████║
  ██║     ██║██╔══██╗██╔══██║
  ███████╗██║██║  ██║██║  ██║
  ╚══════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
""".strip()

def dot_pad(label, value, total_width=52):
    """'label .......... value' with fixed total width."""
    dots_needed = total_width - len(label) - len(str(value)) - 2
    dots = '.' * max(dots_needed, 1)
    return f'{label} {dots} {value}'

def make_svg(user, stars, commits, theme='dark'):
    # ── colours ────────────────────────────────────────────────────────────────
    if theme == 'dark':
        bg       = '#0d1117'
        border   = '#30363d'
        title    = '#58a6ff'
        key      = '#79c0ff'
        value    = '#e6edf3'
        dot      = '#484f58'
        section  = '#3fb950'
        highlight= '#ffa657'
        ascii_c  = '#1f6feb'
    else:
        bg       = '#ffffff'
        border   = '#d0d7de'
        title    = '#0550ae'
        key      = '#0969da'
        value    = '#1f2328'
        dot      = '#8c959f'
        section  = '#1a7f37'
        highlight= '#953800'
        ascii_c  = '#0550ae'

    name      = user.get('name') or USER_NAME
    followers = user['followers']['totalCount']
    repos     = user['repositories']['totalCount']
    age       = get_account_age(user['createdAt'])

    # ── right-column lines ─────────────────────────────────────────────────────
    FIELD_W = 48
    def dp(label, val): return dot_pad(label, val, FIELD_W)

    info_lines = [
        # (text, colour, is_section)
        (f'bruno@lira', title, False, True),          # hostname title
        ('─' * FIELD_W, border, False, False),
        (dp('OS',       'Linux / Windows'), key, False, False),
        (dp('IDE',      'VS Code'), key, False, False),
        (dp('Shell',    'JavaScript ❤️'), key, False, False),
        ('', None, False, False),
        ('- Languages' + '─' * (FIELD_W - 10), section, False, False),
        (dp('Programming', 'JavaScript, HTML, CSS'), key, False, False),
        (dp('Aprendendo', 'React, Node.js, TypeScript'), key, False, False),
        (dp('Humana', 'Português, Inglês'), key, False, False),
        ('', None, False, False),
        ('- Hobbies' + '─' * (FIELD_W - 9), section, False, False),
        (dp('Software', 'Desenvolvimento Front-End'), key, False, False),
        (dp('Objetivo', 'Tornar a web acessível 🚀'), key, False, False),
        ('', None, False, False),
        ('- Contact' + '─' * (FIELD_W - 9), section, False, False),
        (dp('GitHub', f'github.com/{USER_NAME}'), key, False, False),
        (dp('LinkedIn', 'linkedin.com/in/seu-perfil'), key, False, False),
        (dp('Email', 'seu-email@gmail.com'), key, False, False),
        ('', None, False, False),
        ('- GitHub Stats' + '─' * (FIELD_W - 14), section, False, False),
        (f'Repos: {repos}  |  Stars: {stars}  |  Followers: {followers}', value, False, False),
        (f'Commits (total): {commits}', value, False, False),
    ]

    # ── dimensions ─────────────────────────────────────────────────────────────
    FONT     = 'Courier New, Courier, monospace'
    FONT_SZ  = 13
    LINE_H   = 19
    PAD      = 20
    ASCII_W  = 230   # width reserved for left ASCII block
    RIGHT_X  = ASCII_W + PAD + 10

    ascii_rows = ASCII_ART.split('\n')
    ascii_h = len(ascii_rows) * LINE_H

    right_h = len(info_lines) * LINE_H

    W = 860
    H = max(ascii_h, right_h) + PAD * 2 + 10

    # ── SVG build ──────────────────────────────────────────────────────────────
    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')

    # defs – fade-in animation + cursor blink
    lines.append('''<defs>
  <style>
    .fade { animation: fadeIn 0.6s ease forwards; opacity: 0; }
    @keyframes fadeIn { to { opacity: 1; } }
    .blink { animation: blink 1s step-end infinite; }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  </style>
</defs>''')

    # background + border
    lines.append(f'<rect width="{W}" height="{H}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>')

    # ── left: ASCII art (staggered per-row fade) ──────────────────────────────
    for i, row in enumerate(ascii_rows):
        delay = i * 0.04
        esc = row.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        y = PAD + (i + 1) * LINE_H
        lines.append(
            f'<text class="fade" style="animation-delay:{delay:.2f}s" '
            f'x="{PAD}" y="{y}" font-family="{FONT}" font-size="{FONT_SZ}" '
            f'fill="{ascii_c}" xml:space="preserve">{esc}</text>'
        )

    # ── right: info lines ─────────────────────────────────────────────────────
    base_delay = len(ascii_rows) * 0.04

    for i, (text, colour, _, is_title) in enumerate(info_lines):
        if colour is None:
            continue
        delay = base_delay + i * 0.03
        esc = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        y = PAD + (i + 1) * LINE_H
        weight = 'bold' if is_title else 'normal'
        fsize  = FONT_SZ + 1 if is_title else FONT_SZ
        lines.append(
            f'<text class="fade" style="animation-delay:{delay:.2f}s" '
            f'x="{RIGHT_X}" y="{y}" font-family="{FONT}" font-size="{fsize}" '
            f'font-weight="{weight}" fill="{colour}" xml:space="preserve">{esc}</text>'
        )

    # blinking cursor at end
    last_y = PAD + (len(info_lines) + 1) * LINE_H
    lines.append(
        f'<text class="blink" x="{RIGHT_X}" y="{last_y}" '
        f'font-family="{FONT}" font-size="{FONT_SZ}" fill="{value}">█</text>'
    )

    lines.append('</svg>')

    return '\n'.join(lines)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    print('Fetching GitHub data...')
    user    = get_user()
    stars   = get_stars()
    commits = get_commits()

    print(f'  Name:      {user.get("name")}')
    print(f'  Followers: {user["followers"]["totalCount"]}')
    print(f'  Repos:     {user["repositories"]["totalCount"]}')
    print(f'  Stars:     {stars}')
    print(f'  Commits:   {commits}')

    for theme in ('dark', 'light'):
        svg = make_svg(user, stars, commits, theme=theme)
        fname = f'{theme}_mode.svg'
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f'  Wrote {fname}')

    print('Done!')

if __name__ == '__main__':
    main()
