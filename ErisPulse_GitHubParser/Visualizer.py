import html
import time
from typing import Any, Dict, List, Optional, Tuple

from .I18n import card_labels


def _fmt_count(n: int) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 10_000:
        return f"{n / 10_000:.1f}w"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_bytes(n: int) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


_ICONS: Dict[str, str] = {
    "star": '<path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>',
    "fork": '<path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"/>',
    "eye": '<path d="M8 2c1.981 0 3.671.992 4.933 2.075 1.27 1.091 2.187 2.345 2.637 3.023a1.62 1.62 0 0 1 0 1.804c-.45.678-1.367 1.932-2.637 3.023C11.67 13.008 9.981 14 8 14c-1.981 0-3.671-.992-4.933-2.075C1.797 10.83.88 9.576.43 8.898a1.62 1.62 0 0 1 0-1.804c.45-.677 1.367-1.931 2.637-3.022C4.33 2.992 6.019 2 8 2ZM1.679 7.932a.12.12 0 0 0 0 .136c.411.622 1.241 1.75 2.366 2.717C5.176 11.758 6.527 12.5 8 12.5c1.473 0 2.825-.742 3.955-1.715 1.124-.967 1.954-2.096 2.366-2.717a.12.12 0 0 0 0-.136c-.412-.621-1.242-1.75-2.366-2.717C10.824 4.242 9.473 3.5 8 3.5c-1.473 0-2.825.742-3.955 1.715-1.124.967-1.954 2.096-2.366 2.717ZM8 10a2 2 0 1 1-.001-3.999A2 2 0 0 1 8 10Z"/>',
    "issue": '<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"/>',
    "pr": '<path d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Z"/>',
    "commit": '<path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z"/>',
    "tag": '<path d="M1 7.775V2.75C1 1.784 1.784 1 2.75 1h5.025c.464 0 .91.184 1.238.513l6.25 6.25a1.75 1.75 0 0 1 0 2.474l-5.026 5.026a1.75 1.75 0 0 1-2.474 0l-6.25-6.25A1.752 1.752 0 0 1 1 7.775Zm1.5 0c0 .066.026.13.073.177l6.25 6.25a.25.25 0 0 0 .354 0l5.025-5.025a.25.25 0 0 0 0-.354l-6.25-6.25a.25.25 0 0 0-.177-.073H2.75a.25.25 0 0 0-.25.25ZM6 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/>',
    "clock": '<path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm7-3.25v2.992l2.028.812a.75.75 0 0 1-.557 1.392l-2.5-1A.751.751 0 0 1 7 8.25v-3.5a.75.75 0 0 1 1.5 0Z"/>',
}

_LANG_FALLBACK_PALETTE = [
    "#3572A5", "#f1e05a", "#3178c6", "#00ADD8", "#dea584", "#b07219",
    "#f34b7d", "#178600", "#701516", "#4F5D95", "#A97BFF", "#563d7c",
]

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Go": "#00ADD8", "Rust": "#dea584", "Java": "#b07219", "C++": "#f34b7d",
    "C": "#555555", "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "HTML": "#e34c26", "CSS": "#563d7c",
    "Shell": "#89e051", "Vue": "#41b883", "Dart": "#00B4AB", "Lua": "#000080",
    "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384d54", "Makefile": "#427819",
    "SCSS": "#c6538c", "Less": "#1d365d", "Objective-C": "#438eff",
}


def _lang_color(lang: str) -> str:
    return LANG_COLORS.get(lang) or _LANG_FALLBACK_PALETTE[
        abs(hash(lang)) % len(_LANG_FALLBACK_PALETTE)
    ]


def _icon(name: str, color: str = "currentColor", size: int = 14) -> str:
    path = _ICONS.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 16 16" fill="{color}" '
            f'style="vertical-align:-2px;margin-right:5px;display:inline-block">{path}</svg>')


class Visualizer:
    BLUE = "#0969da"
    GREEN = "#1a7f37"
    PURPLE = "#8250df"
    ORANGE = "#bc4c00"
    RED = "#cf222e"
    YELLOW = "#bf8700"

    GH_GREEN_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    GH_GREEN_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    CARD_WIDTH = 920
    HEAT_WIDTH = 1000
    _PAGE_PAD = 40
    _CARD_PAD = 28
    _CARD_GAP = 14

    _CSS_TPL = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: "Noto Sans SC", "Source Han Sans SC", sans-serif;
        background: __PAGE__; color: __INK__; -webkit-font-smoothing: antialiased;
        padding: 40px;
    }
    .card { background: __CARD__; border-radius: 18px; padding: 28px 30px; margin-bottom: 14px; }
    .last { margin-bottom: 0; }
    .head { margin-bottom: 4px; }
    .title { font-size: 27px; font-weight: 700; color: __INK__; letter-spacing: -0.4px; }
    .subtitle { font-size: 14px; color: __SUB__; margin-top: 4px; line-height: 1.5; }
    .divider { height: 1px; background: __SEP__; margin: 20px 0; }
    .chips { display: flex; flex-wrap: wrap; gap: 10px; }
    .chip { display: inline-flex; align-items: center; padding: 8px 14px; border-radius: 9px; font-size: 13.5px; background: __SOFT__; color: __INK__; }
    .chip svg { margin-right: 6px; }
    .chip b { font-weight: 700; margin-right: 5px; }
    .chip.blue b { color: __BLUE__; } .chip.green b { color: __GREEN__; }
    .chip.purple b { color: __PURPLE__; } .chip.orange b { color: __ORANGE__; }
    .chip.red b { color: __RED__; }
    .section-label { font-size: 12px; font-weight: 600; color: __SUB__; letter-spacing: 0.8px; margin: 4px 0 12px; text-transform: uppercase; }
    .kv { display: flex; flex-direction: column; gap: 9px; }
    .kv-row { display: flex; align-items: baseline; font-size: 14px; }
    .kv-row .k { width: 88px; color: __SUB__; flex-shrink: 0; }
    .kv-row .v { color: __INK__; flex: 1; word-break: break-all; }
    .kv-row .v a { color: __BLUE__; text-decoration: none; }
    .tags { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { padding: 4px 11px; border-radius: 7px; font-size: 12.5px; color: __BLUE__; background: __SOFTTAG__; }
    .commit { display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid __SEP__; }
    .commit:last-child { border-bottom: none; }
    .commit .sha { font-family: "Source Code Pro", monospace; font-size: 13px; color: __BLUE__; background: __SOFTTAG__; padding: 3px 8px; border-radius: 5px; height: fit-content; white-space: nowrap; }
    .commit .body { flex: 1; }
    .commit .msg { font-size: 14px; color: __INK__; line-height: 1.5; word-break: break-word; }
    .commit .meta { font-size: 12px; color: __SUB__; margin-top: 4px; }
    .lang-dot { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
    .badge { display: inline-block; padding: 2px 9px; border-radius: 5px; font-size: 11.5px; font-weight: 600; margin-left: 8px; vertical-align: middle; }
    .badge.archived { background: __SOFTTAG__; color: __SUB__; }
    .badge.fork { background: __SOFT__; color: __PURPLE__; }
    .badge.draft { background: __SOFT__; color: __SUB__; }
    .state-pill { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
    .state-pill.open { background: rgba(26,127,55,0.12); color: __GREEN__; }
    .state-pill.closed { background: rgba(207,34,46,0.12); color: __RED__; }
    .state-pill.merged { background: rgba(130,80,223,0.14); color: __PURPLE__; }
    .foot { font-size: 12.5px; color: __SUB__; text-align: center; margin-top: 14px; }
    .foot code { color: __BLUE__; background: __SOFT__; padding: 2px 7px; border-radius: 5px; font-family: "Source Code Pro", monospace; }
    .empty { font-size: 15px; color: __SUB__; text-align: center; padding: 36px 20px; border-radius: 14px; background: __SOFT__; }
    .heat-wrap { display: flex; justify-content: center; }
    .stage { position: relative; }
    .heat-stats { display: flex; gap: 10px; flex-wrap: wrap; }
    .legend { display: flex; align-items: center; gap: 5px; font-size: 12px; color: __SUB__; }
    .legend i { display: inline-block; width: 11px; height: 11px; border-radius: 2px; }
    .avatar-row { display: flex; align-items: center; gap: 18px; }
    .avatar { width: 84px; height: 84px; border-radius: 50%; object-fit: cover; border: 3px solid __SEP__; flex-shrink: 0; }
    .avatar-fallback { width: 84px; height: 84px; border-radius: 50%; background: __SOFT__; color: __SUB__; display: flex; align-items: center; justify-content: center; font-size: 34px; font-weight: 700; flex-shrink: 0; }
    .who .login { font-size: 15px; color: __SUB__; margin-top: 2px; }
    .who .bio { font-size: 13.5px; color: __INK__; margin-top: 8px; line-height: 1.5; max-width: 620px; }
    .donut-row { display: flex; align-items: center; gap: 28px; flex-wrap: wrap; }
    .lang-list { flex: 1; min-width: 280px; display: flex; flex-direction: column; gap: 11px; }
    .lang-item { display: flex; align-items: center; gap: 10px; }
    .lang-item .nm { width: 120px; font-size: 13.5px; color: __INK__; }
    .lang-item .bar { flex: 1; height: 9px; border-radius: 5px; background: __SEP__; overflow: hidden; }
    .lang-item .bar > i { display: block; height: 100%; border-radius: 5px; }
    .lang-item .pct { width: 54px; text-align: right; font-size: 13px; font-weight: 600; color: __INK__; font-variant-numeric: tabular-nums; }
    .donut-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
    .donut-center .v { font-size: 26px; font-weight: 700; color: __INK__; }
    .donut-center .l { font-size: 12px; color: __SUB__; margin-top: 2px; }
    .comment { padding: 11px 0; border-bottom: 1px solid __SEP__; }
    .comment:last-child { border-bottom: none; }
    .comment .head { font-size: 13px; color: __INK__; margin-bottom: 3px; }
    .comment .head b { color: __BLUE__; font-weight: 600; }
    .comment .date { font-size: 11.5px; color: __SUB__; margin-left: 8px; font-weight: 400; }
    .comment .body { font-size: 13px; color: __INK__; line-height: 1.55; word-break: break-word; white-space: pre-wrap; }
    """

    def __init__(self, sdk, config):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubParser.Visualizer")
        self.config = config
        self._takumi_inst = None

    @property
    def takumi(self):
        if self._takumi_inst is None:
            inst = None
            try:
                inst = self.sdk.module.get("Takumi")
            except Exception:
                inst = None
            if inst is None:
                inst = getattr(self.sdk, "Takumi", None)
            self._takumi_inst = inst
        return self._takumi_inst

    @staticmethod
    def _esc(text) -> str:
        return html.escape("" if text is None else str(text))

    def _L(self, key: str, **kw) -> str:
        labels = card_labels(self.config.get("lang", "zh-CN"))
        s = labels.get(key, card_labels("zh-CN").get(key, key))
        if kw:
            try:
                s = s.format(**kw)
            except Exception:
                pass
        return s

    def _trunc(self, text: str, max_len: Optional[int] = None) -> str:
        text = "" if text is None else str(text).strip()
        if not text:
            return ""
        limit = max_len or int(self.config.get("comment_max_len", 120))
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)] + "…"

    def _theme(self) -> Dict[str, Any]:
        mode = self.config.get("theme", "auto")
        if mode == "auto":
            offset = self.config.get("utc_offset", 8)
            hour = int((time.time() / 3600 + offset) % 24)
            mode = "dark" if (hour >= 19 or hour < 7) else "light"
        if mode == "dark":
            return {"page": "#0d1117", "card": "#161b22", "ink": "#e6edf3", "sub": "#7d8590",
                    "sep": "#30363d", "soft": "#21262d", "softtag": "rgba(56,139,253,0.15)",
                    "dark": True}
        return {"page": "#f6f8fa", "card": "#ffffff", "ink": "#1f2328", "sub": "#656d76",
                "sep": "#d0d7de", "soft": "#f6f8fa", "softtag": "#ddf4ff",
                "dark": False}

    def _css(self) -> Tuple[str, Dict[str, Any]]:
        t = self._theme()
        css = (self._CSS_TPL
               .replace("__PAGE__", t["page"]).replace("__CARD__", t["card"])
               .replace("__INK__", t["ink"]).replace("__SUB__", t["sub"])
               .replace("__SEP__", t["sep"]).replace("__SOFT__", t["soft"])
               .replace("__SOFTTAG__", t["softtag"])
               .replace("__BLUE__", self.BLUE).replace("__GREEN__", self.GREEN)
               .replace("__PURPLE__", self.PURPLE).replace("__ORANGE__", self.ORANGE)
               .replace("__RED__", self.RED))
        return css, t

    def _render(self, body_html: str, height: int = None, width: int = None) -> Optional[bytes]:
        takumi = self.takumi
        if takumi is None or not hasattr(takumi, "render_html"):
            self.logger.error("Takumi 模块不可用，无法渲染图片。请先安装 ErisPulse-Takumi")
            return None
        css, _ = self._css()
        try:
            return takumi.render_html(
                body_html, stylesheets=[css],
                width=width or self.CARD_WIDTH, height=None, lang="zh-CN",
            )
        except Exception as e:
            self.logger.error(f"Takumi 渲染失败: {e}")
            return None

    def _head(self, title: str, subtitle: str) -> str:
        return (f"<div class='head'><div class='title'>{self._esc(title)}</div>"
                f"<div class='subtitle'>{self._esc(subtitle)}</div></div>")

    def _card(self, inner: str, last: bool = False) -> str:
        return f"<div class='card{' last' if last else ''}'>{inner}</div>"

    def _cards_height(self, inner_heights: List[int], footer: int = 0) -> int:
        n = len(inner_heights)
        return (self._PAGE_PAD * 2 + n * self._CARD_PAD * 2
                + sum(inner_heights) + max(0, n - 1) * self._CARD_GAP + footer + 24)

    def _state_pill(self, state: str, merged: bool = False) -> str:
        if merged:
            return f"<span class='state-pill merged'>{_icon('pr', 'currentColor', 13)}{self._L('state_merged')}</span>"
        if state == "open":
            return f"<span class='state-pill open'>{_icon('issue', 'currentColor', 13)}{self._L('state_open')}</span>"
        return f"<span class='state-pill closed'>{_icon('issue', 'currentColor', 13)}{self._L('state_closed')}</span>"

    def _build_user(self, data: Dict[str, Any], avatar_uri: Optional[str] = None) -> Tuple[str, int, int]:
        login = data.get("login", "")
        name = data.get("name") or login
        is_org = data.get("type", "User") != "User"

        if avatar_uri:
            avatar = f"<img class='avatar' src='{self._esc(avatar_uri)}' alt='avatar'/>"
        else:
            initial = self._esc((name or login)[:1].upper())
            avatar = f"<div class='avatar-fallback'>{initial}</div>"

        chips = (
            f"<div class='chips'>"
            f"<div class='chip'>{_icon('fork', self.BLUE)}<b>{_fmt_count(data.get('public_repos', 0))}</b>{self._L('repos')}</div>"
            f"<div class='chip purple'>{_icon('eye', self.PURPLE)}<b>{_fmt_count(data.get('followers', 0))}</b>{self._L('followers')}</div>"
            f"<div class='chip green'><b>{_fmt_count(data.get('following', 0))}</b>{self._L('following')}</div>"
            f"<div class='chip orange'><b>{_fmt_count(data.get('public_gists', 0))}</b>{self._L('gists')}</div>"
            f"</div>"
        )

        kv_rows: List[Tuple[str, str]] = []
        if data.get("company"):
            kv_rows.append((self._L('company'), self._esc(data["company"])))
        if data.get("location"):
            kv_rows.append((self._L('location'), self._esc(data["location"])))
        if data.get("blog"):
            blog = data["blog"]
            href = blog if blog.startswith("http") else f"https://{blog}"
            kv_rows.append((self._L('website'), f"<a href='{self._esc(href)}'>{self._esc(blog)}</a>"))
        kv_rows.append((self._L('joined'), self._esc(data.get("created_at", self._L('unknown')))))
        url = data.get("html_url", "")
        kv_rows.append((self._L('homepage'), f"<a href='{self._esc(url)}'>{self._esc(url)}</a>"))

        kv_html = "<div class='kv'>" + "".join(
            f"<div class='kv-row'><div class='k'>{k}</div><div class='v'>{v}</div></div>"
            for k, v in kv_rows
        ) + "</div>"

        bio_html = f"<div class='bio'>{self._esc(data['bio'])}</div>" if data.get("bio") else ""
        header = (
            f"<div class='avatar-row'>{avatar}"
            f"<div class='who'><div class='title' style='font-size:24px'>{self._esc(name)}</div>"
            f"<div class='login'>@{self._esc(login)}{(self._L('org_badge') if is_org else '')}</div>"
            f"{bio_html}</div></div>"
        )
        inner = (
            header + "<div class='divider'></div>" + chips
            + f"<div class='section-label' style='margin-top:18px'>{self._L('profile_section')}</div>" + kv_html
        )
        body = self._card(inner, last=True)
        h = 28 + 84 + 18 + 42 + 30 + len(kv_rows) * 24 + 14
        return body, self._cards_height([h], footer=8), self.CARD_WIDTH

    def render_user(self, data: Dict[str, Any], avatar_uri: Optional[str] = None) -> Optional[bytes]:
        body, h, w = self._build_user(data, avatar_uri)
        return self._render(body, h, w)

    def _build_repo(self, data: Dict[str, Any], show_topics: bool = True) -> Tuple[str, int, int]:
        _, t = self._css()
        full_name = data.get("full_name", "")
        desc = data.get("description", self._L('no_desc')) or self._L('no_desc')
        lang = data.get("language", self._L('lang_unspecified'))
        lang_color = _lang_color(lang) if lang != self._L('lang_unspecified') else "#8b949e"

        badges = ""
        if data.get("archived"):
            badges += f"<span class='badge archived'>{self._L('archived')}</span>"
        if data.get("fork"):
            badges += f"<span class='badge fork'>{self._L('fork')}</span>"

        chips = (
            f"<div class='chips'>"
            f"<div class='chip green'>{_icon('star', self.GREEN)}<b>{_fmt_count(data.get('stars', 0))}</b></div>"
            f"<div class='chip purple'>{_icon('fork', self.PURPLE)}<b>{_fmt_count(data.get('forks', 0))}</b></div>"
            f"<div class='chip'>{_icon('eye', t['sub'])}<b>{_fmt_count(data.get('watchers', 0))}</b></div>"
            f"<div class='chip orange'>{_icon('issue', self.ORANGE)}<b>{_fmt_count(data.get('open_issues', 0))}</b>{self._L('issues')}</div>"
            f"</div>"
        )
        kv_rows: List[Tuple[str, str]] = [
            (self._L('language'), f"<span class='lang-dot' style='background:{lang_color}'></span>{self._esc(lang)}"),
            (self._L('license'), self._esc(data.get("license", self._L('none')))),
            (self._L('default_branch'), self._esc(data.get("default_branch", "main"))),
            (self._L('created'), self._esc(data.get("created_at", self._L('unknown')))),
            (self._L('pushed'), self._esc(data.get("pushed_at", self._L('unknown')))),
        ]
        if data.get("homepage"):
            home = data["homepage"]
            href = home if home.startswith("http") else f"https://{home}"
            kv_rows.insert(2, (self._L('homepage'), f"<a href='{self._esc(href)}'>{self._esc(home)}</a>"))
        kv_html = "<div class='kv'>" + "".join(
            f"<div class='kv-row'><div class='k'>{k}</div><div class='v'>{v}</div></div>"
            for k, v in kv_rows
        ) + "</div>"

        topics_html = ""
        if show_topics and data.get("topics"):
            tags = "".join(f"<span class='tag'>{self._esc(t)}</span>" for t in data["topics"][:10])
            topics_html = f"<div class='section-label' style='margin-top:18px'>{self._L('topics_section')}</div><div class='tags'>{tags}</div>"

        inner = (
            f"<div class='head'><div class='title' style='font-size:23px'>{self._esc(full_name)}{badges}</div>"
            f"<div class='subtitle' style='margin-top:8px'>{self._esc(desc)}</div></div>"
            + "<div class='divider'></div>" + chips
            + f"<div class='section-label' style='margin-top:18px'>{self._L('detail_section')}</div>" + kv_html
            + topics_html
        )
        body = self._card(inner, last=True)
        h = 28 + 30 + 50 + 42 + 30 + len(kv_rows) * 24 + (44 + 34 if topics_html else 0) + 14
        return body, self._cards_height([h], footer=8), self.CARD_WIDTH

    def render_repo(self, data: Dict[str, Any], show_topics: bool = True) -> Optional[bytes]:
        body, h, w = self._build_repo(data, show_topics)
        return self._render(body, h, w)

    def _build_commits(self, owner_repo: str, commits: List[Dict[str, Any]]) -> Tuple[str, int, int]:
        if not commits:
            inner = self._head(owner_repo, self._L('recent_commits')) + "<div class='divider'></div><div class='empty'>" + self._L('no_commits') + "</div>"
            body = self._card(inner, last=True)
            return body, self._cards_height([28 + 30 + 100]), self.CARD_WIDTH

        items = "".join(
            f"<div class='commit'>"
            f"<div class='sha'>{self._esc(c.get('sha', ''))}</div>"
            f"<div class='body'><div class='msg'>{self._esc(c.get('message', ''))}</div>"
            f"<div class='meta'>{self._esc(c.get('author', ''))} · {self._esc(c.get('date', ''))}</div></div>"
            f"</div>"
            for c in commits
        )
        inner = (
            self._head(owner_repo, self._L('commits_n', n=len(commits)))
            + "<div class='divider'></div>" + items
        )
        body = self._card(inner, last=True)
        h = 28 + 30 + 22 + len(commits) * 56
        return body, self._cards_height([h], footer=8), self.CARD_WIDTH

    def render_commits(self, owner_repo: str, commits: List[Dict[str, Any]]) -> Optional[bytes]:
        body, h, w = self._build_commits(owner_repo, commits)
        return self._render(body, h, w)

    def _build_issue_pr(self, kind: str, owner_repo: str, data: Dict[str, Any]) -> Tuple[str, int, int]:
        number = data.get("number", "?")
        title = data.get("title", "")
        state = data.get("state", "open")
        merged = bool(data.get("merged_at"))
        label = self._L('pr_label') if kind == "pr" else self._L('issue_label')

        pill = self._state_pill(state, merged)
        chips_parts = [
            f"<div class='chip'>{_icon('eye', self.BLUE)}<b>{_fmt_count(data.get('comments', 0))}</b>{self._L('comments')}</div>",
        ]
        if kind == "pr":
            chips_parts.append(f"<div class='chip green'>+<b>{_fmt_count(data.get('additions', 0))}</b></div>")
            chips_parts.append(f"<div class='chip red'>-<b>{_fmt_count(data.get('deletions', 0))}</b></div>")
            chips_parts.append(f"<div class='chip purple'>{_icon('commit', self.PURPLE)}<b>{_fmt_count(data.get('commits', 0))}</b>{self._L('commits_label')}</div>")
            if data.get("changed_files"):
                chips_parts.append(f"<div class='chip orange'><b>{_fmt_count(data.get('changed_files', 0))}</b>{self._L('files')}</div>")
        chips = f"<div class='chips'>{''.join(chips_parts)}</div>"

        kv_rows: List[Tuple[str, str]] = [(self._L('author'), self._esc(data.get("user", self._L('unknown'))))]
        if data.get("assignees"):
            kv_rows.append((self._L('assignees'), self._esc("、".join(data["assignees"][:5]))))
        kv_rows.append((self._L('created'), self._esc(data.get("created_at", self._L('unknown')))))
        if merged:
            kv_rows.append((self._L('merged_at'), self._esc(data.get("merged_at"))))
        elif state == "closed":
            kv_rows.append((self._L('closed_at'), self._esc(data.get("closed_at", "—"))))
        kv_html = "<div class='kv'>" + "".join(
            f"<div class='kv-row'><div class='k'>{k}</div><div class='v'>{v}</div></div>"
            for k, v in kv_rows
        ) + "</div>"

        labels_html = ""
        if data.get("labels"):
            labels_html = (f"<div class='section-label' style='margin-top:16px'>{self._L('labels_section')}</div><div class='tags'>"
                           + "".join(f"<span class='tag'>{self._esc(lb)}</span>" for lb in data["labels"][:8])
                           + "</div>")

        comments_html = ""
        comments = data.get("comments_list") or []
        if comments:
            items = "".join(
                f"<div class='comment'><div class='head'><b>{self._esc(c.get('user', ''))}</b>"
                f"<span class='date'>{self._esc(c.get('created_at', ''))}</span></div>"
                f"<div class='body'>{self._esc(self._trunc(c.get('body', '')))}</div></div>"
                for c in comments
            )
            comments_html = (f"<div class='section-label' style='margin-top:16px'>{self._L('comments_section')}</div>"
                             + items)

        inner = (
            self._head(f"{owner_repo} #{number}", f"{label} · {title}")
            + f"<div style='margin-top:14px'>{pill}</div>"
            + "<div class='divider'></div>" + chips
            + f"<div class='section-label' style='margin-top:18px'>{self._L('detail_section')}</div>" + kv_html
            + labels_html
            + comments_html
        )
        body = self._card(inner, last=True)
        h = 28 + 30 + 30 + 44 + 42 + 30 + len(kv_rows) * 24 + (40 if labels_html else 0) + 14
        return body, self._cards_height([h], footer=8), self.CARD_WIDTH

    def render_issue(self, owner_repo: str, data: Dict[str, Any]) -> Optional[bytes]:
        body, h, w = self._build_issue_pr("issue", owner_repo, data)
        return self._render(body, h, w)

    def render_pr(self, owner_repo: str, data: Dict[str, Any]) -> Optional[bytes]:
        body, h, w = self._build_issue_pr("pr", owner_repo, data)
        return self._render(body, h, w)

    def _build_languages(self, owner_repo: str, langs_raw: Dict[str, int]) -> Tuple[str, int, int]:
        _, t = self._css()
        total = sum(langs_raw.values()) or 1
        ranked = sorted(langs_raw.items(), key=lambda kv: kv[1], reverse=True)
        top = ranked[:6]
        other_sum = sum(v for _, v in ranked[6:])
        slices = [(name, v) for name, v in top]
        if other_sum > 0:
            slices.append(("Other", other_sum))

        cx = cy = 90
        R = 70
        sw = 22
        import math
        circ = 2 * math.pi * R
        acc = 0.0
        circles = []
        for name, val in slices:
            pct = val / total
            dash = pct * circ
            color = _lang_color(name) if name != "Other" else "#8b949e"
            circles.append(
                f"<circle cx='{cx}' cy='{cy}' r='{R}' fill='none' "
                f"stroke='{color}' stroke-width='{sw}' "
                f"stroke-dasharray='{dash:.2f} {circ - dash:.2f}' "
                f"stroke-dashoffset='{-acc:.2f}' transform='rotate(-90 {cx} {cy})'/>"
            )
            acc += dash
        svg = (f"<svg width='180' height='180' viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'>"
               + "".join(circles) + "</svg>")
        center = (f"<div class='donut-center'><div class='v'>{len(langs_raw)}</div>"
                  f"<div class='l'>{self._L('lang_count')}</div></div>")
        stage = f"<div class='stage' style='width:180px;height:180px'>{svg}{center}</div>"

        list_items = []
        for name, val in slices:
            pct = val / total * 100
            color = _lang_color(name) if name != "Other" else "#8b949e"
            list_items.append(
                f"<div class='lang-item'><div class='nm'>"
                f"<span class='lang-dot' style='background:{color}'></span>{self._esc(name)}</div>"
                f"<div class='bar'><i style='width:{pct:.1f}%;background:{color}'></i></div>"
                f"<div class='pct'>{pct:.1f}%</div></div>"
            )
        lang_list = f"<div class='lang-list'>{''.join(list_items)}</div>"

        inner = (
            self._head(owner_repo, self._L('lang_summary', size=_fmt_bytes(total)))
            + "<div class='divider'></div>"
            + f"<div class='donut-row'>{stage}{lang_list}</div>"
        )
        body = self._card(inner, last=True)
        rows_h = max(180, len(slices) * 30 + 20)
        h = 28 + 30 + 22 + rows_h + 14
        return body, self._cards_height([h], footer=8), self.CARD_WIDTH

    def render_languages(self, owner_repo: str, langs_raw: Dict[str, int]) -> Optional[bytes]:
        if not langs_raw:
            inner = self._head(owner_repo, self._L('lang_breakdown')) + "<div class='divider'></div><div class='empty'>" + self._L('no_langs') + "</div>"
            body = self._card(inner, last=True)
            return self._render(body, self._cards_height([28 + 30 + 100]), self.CARD_WIDTH)
        body, h, w = self._build_languages(owner_repo, langs_raw)
        return self._render(body, h, w)

    def _build_heatmap(self, username: str, contrib: Dict[str, Any]) -> Tuple[str, int, int]:
        weeks: List[List[Dict[str, Any]]] = contrib.get("weeks", [])
        total = int(contrib.get("total", 0))
        if not weeks:
            inner = self._head(f"@{username}", self._L('heat_title_empty')) + "<div class='divider'></div><div class='empty'>" + self._L('no_heat') + "</div>"
            body = self._card(inner, last=True)
            return body, self._cards_height([28 + 30 + 100]), self.HEAT_WIDTH

        _, t = self._css()
        levels = self.GH_GREEN_DARK if t["dark"] else self.GH_GREEN_LIGHT
        empty_color = t["sep"]

        CELL, GAP = 12, 3
        PITCH = CELL + GAP
        LABEL_LEFT, LABEL_TOP = 34, 22
        n_weeks = len(weeks)
        grid_w = LABEL_LEFT + n_weeks * PITCH
        grid_h = LABEL_TOP + 7 * PITCH

        rects: List[str] = []
        weekday_labels = ["", "Mon", "", "Wed", "", "Fri", ""]
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month_labels: List[Tuple[float, str]] = []
        prev_month = -1

        for wi, week in enumerate(weeks):
            for di, day in enumerate(week[:7]):
                x = LABEL_LEFT + wi * PITCH
                y = LABEL_TOP + di * PITCH
                level = int(day.get("level", 0)) if day else 0
                color = levels[max(0, min(4, level))] if day else empty_color
                op = "1" if day else "0.25"
                rects.append(
                    f"<rect x='{x:.1f}' y='{y:.1f}' width='{CELL}' height='{CELL}' rx='2' ry='2' fill='{color}' opacity='{op}'/>"
                )
            first_day = week[0] if week else None
            if first_day and first_day.get("date"):
                try:
                    m = int(first_day["date"][5:7])
                    if m != prev_month:
                        month_labels.append((LABEL_LEFT + wi * PITCH, month_names[m - 1]))
                        prev_month = m
                except (ValueError, IndexError):
                    pass

        svg = (f"<svg width='{grid_w}' height='{grid_h}' viewBox='0 0 {grid_w} {grid_h}' xmlns='http://www.w3.org/2000/svg'>"
               + "".join(rects) + "</svg>")

        overlays = ""
        for row_idx, label in enumerate(weekday_labels):
            if not label:
                continue
            y = LABEL_TOP + row_idx * PITCH + CELL / 2
            overlays += f"<div style='position:absolute;left:0;top:{y:.1f}px;transform:translateY(-50%);font-size:11px;color:{t['sub']}'>{label}</div>"
        for x, name in month_labels:
            overlays += f"<div style='position:absolute;left:{x:.1f}px;top:0;font-size:11px;color:{t['sub']}'>{name}</div>"

        stage = f"<div class='stage' style='width:{grid_w}px;height:{grid_h}px'>{svg}{overlays}</div>"

        streak = self._streak(contrib.get("days", []))
        best_day = max((d.get("count", 0) for d in contrib.get("days", []) if d), default=0)
        stats = (
            f"<div class='heat-stats'>"
            f"<div class='chip green'><b>{_fmt_count(total)}</b>{self._L('year_contrib')}</div>"
            f"<div class='chip blue'><b>{streak['current']}</b>{self._L('cur_streak')}</div>"
            f"<div class='chip purple'><b>{streak['longest']}</b>{self._L('max_streak')}</div>"
            f"<div class='chip orange'><b>{best_day}</b>{self._L('best_day')}</div>"
            f"</div>"
        )
        legend_cells = "".join(f"<i style='background:{levels[lv]}'></i>" for lv in range(5))
        legend = (f"<div style='display:flex;justify-content:space-between;align-items:center;margin-top:14px'>"
                  f"<div class='legend'>{self._L('less')} {legend_cells} {self._L('more')}</div>"
                  f"<div class='legend'>{self._L('source')}: {self._esc(contrib.get('source', 'unknown'))}</div></div>")

        inner = (
            self._head(f"@{username}", self._L('heat_subtitle', n=total))
            + "<div class='divider'></div>" + stats
            + f"<div class='heat-wrap' style='margin-top:18px'>{stage}</div>"
            + legend
        )
        body = self._card(inner, last=True)
        h = 28 + 30 + 42 + 18 + grid_h + 28 + 14
        return body, self._cards_height([h], footer=8), self.HEAT_WIDTH

    def render_heatmap(self, username: str, contrib: Dict[str, Any]) -> Optional[bytes]:
        body, h, w = self._build_heatmap(username, contrib)
        return self._render(body, h, w)

    @staticmethod
    def _streak(days: List[Dict[str, Any]]) -> Dict[str, int]:
        valid = [d for d in days if d and d.get("date")]
        if not valid:
            return {"current": 0, "longest": 0}
        valid.sort(key=lambda d: d["date"])
        current = 0
        for d in reversed(valid):
            if d.get("count", 0) > 0:
                current += 1
            else:
                break
        longest = 0
        run = 0
        for d in valid:
            if d.get("count", 0) > 0:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        return {"current": current, "longest": longest}
