import re
import time
import base64
from typing import Optional, Dict, List, Tuple

import aiohttp

from ErisPulse import sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import message

_GITHUB_LINK_REGEX = re.compile(
    r'https?://(?:www\.)?github\.com/([^/\s]+)/([^/\s]+)/?(?:issues/(\d+)|pull/(\d+)|tree/([^/\s]+)|blob/([^/\s]+/[^/\s]+)|$)?'
)

_GITHUB_URL_REGEX = re.compile(r'https?://github\.com/[^\s]+')

_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
_MD_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


def _format_count(n: int) -> str:
    if n >= 10_000:
        return f"{n / 10_000:.1f}w"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _resolve_relative_urls(text: str, owner: str, repo: str, branch: str) -> str:
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    blob_base = f"https://github.com/{owner}/{repo}/blob/{branch}"

    def _make_abs(url: str, is_image: bool = False) -> str:
        if not url or url.startswith(("http://", "https://", "mailto:", "#", "data:")):
            return url
        base = raw_base if is_image else blob_base
        path = url.lstrip("./")
        return f"{base}/{path}"

    def _replace_image(m):
        alt, url = m.group(1), m.group(2)
        return f"![{alt}]({_make_abs(url, is_image=True)})"

    def _replace_link(m):
        text_inner, url = m.group(1), m.group(2)
        return f"[{text_inner}]({_make_abs(url)})"

    text = _MD_IMAGE_RE.sub(_replace_image, text)
    text = _MD_LINK_RE.sub(_replace_link, text)
    return text


def _inline_md_to_html(text: str) -> str:
    if not text:
        return ""
    text = _MD_IMAGE_RE.sub(
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" style="max-width:100%;border-radius:4px;">',
        text
    )
    text = re.sub(r'`([^`]+)`', r'<code style="background:rgba(0,0,0,0.06);padding:1px 4px;border-radius:3px;font-size:12px;">\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = _MD_LINK_RE.sub(r'<a href="\2" style="color:#0969da;text-decoration:none;">\1</a>', text)
    return text


def _md_to_html(text: str) -> str:
    if not text:
        return ""
    lines = text.split('\n')
    html_parts = []
    in_list = False
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if re.match(r'^</?(details|summary|table|thead|tbody|tr|th|td|thead|br|hr|img|a\s|div|p|blockquote|pre|code|strong|em|b|i|ul|ol|li|h[1-6])', stripped, re.IGNORECASE):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(line)
            continue

        if stripped.startswith('```'):
            if in_code_block:
                html_parts.append('</code></pre>')
                in_code_block = False
            else:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                lang = stripped[3:].strip()
                html_parts.append(f'<pre><code{f" class={lang}" if lang else ""}>')
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(_inline_md_to_html(line))
            continue

        if re.match(r'^---+\s*$', stripped):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append('<hr style="border:none;border-top:1px solid #e0e0e0;margin:8px 0;">')
            continue

        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            level = len(header_match.group(1))
            sizes = {1: '18px', 2: '16px', 3: '14px', 4: '13px', 5: '13px', 6: '12px'}
            size = sizes.get(level, '13px')
            content = _inline_md_to_html(header_match.group(2))
            html_parts.append(f'<div style="font-size:{size};font-weight:bold;margin:8px 0 4px;">{content}</div>')
            continue

        if stripped.startswith('>'):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            quote_content = re.sub(r'^>\s*', '', stripped)
            html_parts.append(f'<div style="border-left:3px solid #238636;padding:4px 8px;margin:4px 0;color:#555;font-size:13px;">{_inline_md_to_html(quote_content)}</div>')
            continue

        list_match = re.match(r'^(\s*)-\s+(.*)$', line)
        if list_match:
            indent = len(list_match.group(1))
            content = _inline_md_to_html(list_match.group(2))
            if not in_list:
                html_parts.append('<ul style="margin:4px 0;padding-left:20px;">')
                in_list = True
            margin = f"margin-left:{indent * 8}px;" if indent > 0 else ""
            html_parts.append(f'<li style="{margin}font-size:13px;margin-bottom:2px;">{content}</li>')
            continue

        if in_list:
            html_parts.append('</ul>')
            in_list = False

        if not stripped:
            html_parts.append('<div style="height:6px;"></div>')
            continue

        html_parts.append(f'<div style="font-size:13px;line-height:1.6;">{_inline_md_to_html(stripped)}</div>')

    if in_list:
        html_parts.append('</ul>')
    if in_code_block:
        html_parts.append('</code></pre>')

    return '\n'.join(html_parts)


class GitHubTemplates:
    PRIMARY_COLOR = "#238636"
    PRIMARY_BG = "rgba(35, 134, 54, 0.06)"
    SECONDARY_COLOR = "#656d76"
    ACCENT_COLOR = "#0969da"

    _HINT_HTML = '<div style="font-size:12px;color:{color};margin-top:8px;">想{action}吗？说 <code style="background:rgba(0,0,0,0.06);padding:1px 4px;border-radius:3px;">看一下</code> 发送</div>'

    @classmethod
    def _get_hint(cls, data: dict) -> dict:
        if data["type"] == "repository" and data.get("readme_content"):
            return {
                "action": "查看这个项目的 README",
                "has_detail": True,
            }
        elif data["type"] == "issue" and data.get("issue_body"):
            return {
                "action": "查看这条 Issue 的详细内容和评论",
                "has_detail": True,
            }
        elif data["type"] == "pull_request" and data.get("pr_body"):
            return {
                "action": "查看这条 PR 的详细内容和评论",
                "has_detail": True,
            }
        return {"action": "", "has_detail": False}

    @classmethod
    def _hint_html(cls, data: dict) -> str:
        hint = cls._get_hint(data)
        if not hint["has_detail"]:
            return ""
        return cls._HINT_HTML.format(action=hint["action"], color=cls.SECONDARY_COLOR)

    @classmethod
    def _hint_md(cls, data: dict) -> Optional[str]:
        hint = cls._get_hint(data)
        if not hint["has_detail"]:
            return None
        return f'\n\n想{hint["action"]}吗？说 `看一下` 发送'

    @classmethod
    def _hint_text(cls, data: dict) -> Optional[str]:
        hint = cls._get_hint(data)
        if not hint["has_detail"]:
            return None
        return f'\n\n想{hint["action"]}吗？说 看一下 发送'

    @classmethod
    def build_card(cls, data: dict, config: dict) -> Dict[str, str]:
        html_card = cls._build_html(data, config)
        markdown_card = cls._build_markdown(data, config)
        text_card = cls._build_text(data, config)
        return {"html": html_card, "markdown": markdown_card, "text": text_card}

    @classmethod
    def _build_html(cls, data: dict, config: dict) -> str:
        if data["type"] == "repository":
            return cls._build_repo_html(data, config)
        elif data["type"] == "issue":
            return cls._build_issue_html(data, config)
        elif data["type"] == "pull_request":
            return cls._build_pr_html(data, config)
        return ""

    @classmethod
    def _build_repo_html(cls, data: dict, config: dict) -> str:
        stat_items = (
            f'<span style="margin-right: 12px;">Stars: {_format_count(data["stars"])}</span>'
            f'<span style="margin-right: 12px;">Forks: {_format_count(data["forks"])}</span>'
            f'<span>Watchers: {_format_count(data["watchers"])}</span>'
        )

        info_items = []
        if data.get("language") and data["language"] != "未知":
            info_items.append(f'<span style="margin-right: 12px;">{data["language"]}</span>')
        if data.get("license") and data["license"] != "无":
            info_items.append(f'<span>{data["license"]}</span>')
        info_line = "".join(info_items)

        topics_line = ""
        if config.get("show_topics", True) and data.get("topics"):
            topics_html = " ".join(
                f'<code style="font-size: 11px; background: rgba(35,134,54,0.08); padding: 1px 5px; border-radius: 3px;">{t}</code>'
                for t in data["topics"][:8]
            )
            topics_line = f'<div style="font-size: 12px; margin-top: 6px;">{topics_html}</div>'

        homepage_line = ""
        if data.get("homepage"):
            homepage_line = (
                f'<div style="font-size: 12px; margin-top: 4px;">'
                f'<a href="{data["homepage"]}" style="color: {cls.ACCENT_COLOR};">{data["homepage"]}</a>'
                f'</div>'
            )

        return (
            f'<div style="padding: 12px; border-radius: 8px;">'
            f'<div style="font-size: 15px; font-weight: bold; margin-bottom: 8px;">'
            f'<a href="{data["url"]}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">{data["full_name"]}</a></div>'
            f'<div style="font-size: 13px; color: {cls.SECONDARY_COLOR}; margin-bottom: 10px;">{data.get("description") or "暂无描述"}</div>'
            f'<div style="padding: 8px; background: {cls.PRIMARY_BG}; border-radius: 6px; margin-bottom: 8px;">'
            f'<div style="font-size: 13px; margin-bottom: 4px;">{stat_items}</div>'
            f'<div style="font-size: 13px;">{info_line}</div>'
            f'{topics_line}'
            f'</div>'
            f'{homepage_line}'
            f'<div style="font-size: 11px; color: {cls.SECONDARY_COLOR};">创建于: {data["created_at"]} | 更新于: {data["updated_at"]}</div>'
            f'{cls._hint_html(data)}'
            f'</div>'
        )

    @classmethod
    def _build_issue_html(cls, data: dict, config: dict) -> str:
        state_color = "#1a7f37" if data["state"] == "开启" else "#cf222e"
        return (
            f'<div style="padding: 12px; border-radius: 8px;">'
            f'<div style="font-size: 15px; font-weight: bold; margin-bottom: 8px;">'
            f'<a href="{data["url"]}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">Issue #{data["issue_number"]}</a></div>'
            f'<div style="font-size: 13px; margin-bottom: 10px;">{data["title"]}</div>'
            f'<div style="padding: 8px; background: {cls.PRIMARY_BG}; border-radius: 6px;">'
            f'<span style="color: {state_color}; font-weight: bold;">{data["state"]}</span>'
            f'<span style="margin-left: 12px; font-size: 13px;">作者: {data["user"]}</span>'
            f'<span style="margin-left: 12px; font-size: 13px;">评论: {data["comments"]}</span>'
            f'</div>'
            f'<div style="font-size: 11px; color: {cls.SECONDARY_COLOR}; margin-top: 6px;">创建于: {data["created_at"]}</div>'
            f'{cls._hint_html(data)}'
            f'</div>'
        )

    @classmethod
    def _build_pr_html(cls, data: dict, config: dict) -> str:
        state_color = "#1a7f37" if data["state"] == "开启" else "#cf222e"
        return (
            f'<div style="padding: 12px; border-radius: 8px;">'
            f'<div style="font-size: 15px; font-weight: bold; margin-bottom: 8px;">'
            f'<a href="{data["url"]}" style="color: {cls.PRIMARY_COLOR}; text-decoration: none;">PR #{data["pr_number"]}</a></div>'
            f'<div style="font-size: 13px; margin-bottom: 10px;">{data["title"]}</div>'
            f'<div style="padding: 8px; background: {cls.PRIMARY_BG}; border-radius: 6px;">'
            f'<span style="color: {state_color}; font-weight: bold;">{data["state"]}</span>'
            f'<span style="margin-left: 12px; font-size: 13px;">作者: {data["user"]}</span>'
            f'<span style="margin-left: 12px; font-size: 13px;">评论: {data["comments"]}</span>'
            f'<span style="margin-left: 12px; font-size: 13px;">提交: {data["commits"]}</span>'
            f'</div>'
            f'<div style="font-size: 12px; margin-top: 6px; color: {cls.PRIMARY_COLOR};">'
            f'+{data["additions"]} / -{data["deletions"]}</div>'
            f'<div style="font-size: 11px; color: {cls.SECONDARY_COLOR}; margin-top: 4px;">创建于: {data["created_at"]}</div>'
            f'{cls._hint_html(data)}'
            f'</div>'
        )

    @classmethod
    def _build_markdown(cls, data: dict, config: dict) -> str:
        if data["type"] == "repository":
            return cls._build_repo_markdown(data, config)
        elif data["type"] == "issue":
            return cls._build_issue_markdown(data, config)
        elif data["type"] == "pull_request":
            return cls._build_pr_markdown(data, config)
        return ""

    @classmethod
    def _build_repo_markdown(cls, data: dict, config: dict) -> str:
        lines = [
            f'**[{data["full_name"]}]({data["url"]})**',
            f'{data.get("description") or "暂无描述"}',
            '',
            f'Stars: {_format_count(data["stars"])} | '
            f'Forks: {_format_count(data["forks"])} | '
            f'Watchers: {_format_count(data["watchers"])}',
        ]

        info_parts = []
        if data.get("language") and data["language"] != "未知":
            info_parts.append(data["language"])
        if data.get("license") and data["license"] != "无":
            info_parts.append(data["license"])
        if info_parts:
            lines.append(' | '.join(info_parts))

        if config.get("show_topics", True) and data.get("topics"):
            lines.append(f'标签: {" | ".join(f"`{t}`" for t in data["topics"][:8])}')

        if data.get("homepage"):
            lines.append(f'[{data["homepage"]}]({data["homepage"]})')

        lines.append(f'创建于: {data["created_at"]} | 更新于: {data["updated_at"]}')

        hint = cls._hint_md(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_issue_markdown(cls, data: dict, config: dict) -> str:
        lines = [
            f'**[Issue #{data["issue_number"]}]({data["url"]})** - {data["title"]}',
            '',
            f'状态: {data["state"]} | 作者: {data["user"]}',
            f'评论: {data["comments"]} | 创建于: {data["created_at"]}',
        ]

        hint = cls._hint_md(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_pr_markdown(cls, data: dict, config: dict) -> str:
        lines = [
            f'**[PR #{data["pr_number"]}]({data["url"]})** - {data["title"]}',
            '',
            f'状态: {data["state"]} | 作者: {data["user"]}',
            f'评论: {data["comments"]} | 提交: {data["commits"]}',
            f'+{data["additions"]} / -{data["deletions"]} 行 | 创建于: {data["created_at"]}',
        ]

        hint = cls._hint_md(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_text(cls, data: dict, config: dict) -> str:
        if data["type"] == "repository":
            return cls._build_repo_text(data, config)
        elif data["type"] == "issue":
            return cls._build_issue_text(data, config)
        elif data["type"] == "pull_request":
            return cls._build_pr_text(data, config)
        return data.get("url", "")

    @classmethod
    def _build_repo_text(cls, data: dict, config: dict) -> str:
        lines = [
            data["full_name"],
            data.get("description") or "暂无描述",
            '----------',
            f'Stars: {_format_count(data["stars"])}  '
            f'Forks: {_format_count(data["forks"])}  '
            f'Watchers: {_format_count(data["watchers"])}',
        ]

        info_parts = []
        if data.get("language") and data["language"] != "未知":
            info_parts.append(f'语言: {data["language"]}')
        if data.get("license") and data["license"] != "无":
            info_parts.append(f'许可证: {data["license"]}')
        if info_parts:
            lines.append(' | '.join(info_parts))

        if config.get("show_topics", True) and data.get("topics"):
            lines.append(f'标签: {" | ".join(data["topics"][:8])}')

        if data.get("homepage"):
            lines.append(f'首页: {data["homepage"]}')

        lines.append(f'创建于: {data["created_at"]} | 更新于: {data["updated_at"]}')
        lines.append(f'{data["url"]}')

        hint = cls._hint_text(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_issue_text(cls, data: dict, config: dict) -> str:
        lines = [
            f'Issue #{data["issue_number"]} - {data["title"]}',
            '----------',
            f'状态: {data["state"]} | 作者: {data["user"]}',
            f'评论: {data["comments"]} | 创建于: {data["created_at"]}',
            data["url"],
        ]

        hint = cls._hint_text(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_pr_text(cls, data: dict, config: dict) -> str:
        lines = [
            f'PR #{data["pr_number"]} - {data["title"]}',
            '----------',
            f'状态: {data["state"]} | 作者: {data["user"]}',
            f'评论: {data["comments"]} | 提交: {data["commits"]}',
            f'+{data["additions"]} / -{data["deletions"]}',
            f'创建于: {data["created_at"]}',
            data["url"],
        ]

        hint = cls._hint_text(data)
        if hint:
            lines.append(hint)

        return '\n'.join(lines)

    @classmethod
    def _build_comment_text(cls, c: dict) -> str:
        return f'{c["user"]}: {c["body"]}'

    @classmethod
    def _build_comment_md(cls, c: dict) -> str:
        return f'**{c["user"]}**: {c["body"]}'

    @classmethod
    def _build_comment_html(cls, c: dict) -> str:
        return (
            f'<div style="margin-bottom:8px;padding:6px;background:rgba(35,134,54,0.03);border-radius:4px;">'
            f'<span style="font-weight:bold;color:{cls.PRIMARY_COLOR};">{c["user"]}</span>'
            f'<div style="font-size:13px;margin-top:2px;color:#333;">{_md_to_html(c["body"])}</div>'
            f'</div>'
        )

    @classmethod
    def build_detail(cls, data: dict) -> Dict[str, str]:
        if data["type"] == "repository":
            return cls._build_readme_detail(data)
        elif data["type"] == "issue":
            return cls._build_issue_detail(data)
        elif data["type"] == "pull_request":
            return cls._build_pr_detail(data)
        return {}

    @classmethod
    def _build_readme_detail(cls, data: dict) -> Dict[str, str]:
        return {
            "html": (
                f'<div style="padding:12px;border-radius:8px;">'
                f'<div style="font-size:15px;font-weight:bold;margin-bottom:8px;color:{cls.PRIMARY_COLOR};">README</div>'
                f'<div style="font-size:13px;line-height:1.6;">{data.get("readme_html", "")}</div>'
                f'</div>'
            ),
            "markdown": "**README**\n\n" + '\n'.join(f'> {line}' for line in data.get("readme_content", "").split('\n')),
            "text": f"── README ──\n\n{data.get('readme_content', '')}",
        }

    @classmethod
    def _build_issue_detail(cls, data: dict) -> Dict[str, str]:
        body = data.get("issue_body", "")
        comments: List[dict] = data.get("issue_comments", [])

        body_html = _md_to_html(body)
        comments_html = ''.join(cls._build_comment_html(c) for c in comments)
        comments_md = '\n'.join(cls._build_comment_md(c) for c in comments)
        comments_text = '\n'.join(cls._build_comment_text(c) for c in comments)

        return {
            "html": (
                f'<div style="padding:12px;border-radius:8px;">'
                f'<div style="font-size:15px;font-weight:bold;margin-bottom:8px;color:{cls.PRIMARY_COLOR};">'
                f'Issue #{data["issue_number"]}: {data["title"]}</div>'
                f'<div style="font-size:13px;color:#333;margin-bottom:12px;line-height:1.6;">{body_html}</div>'
                f'{comments_html}'
                f'</div>'
            ),
            "markdown": (
                f'**Issue #{data["issue_number"]}: {data["title"]}**\n\n'
                f'{body}\n\n'
                f'{"── 评论 ──" if comments else ""}\n{comments_md}'
            ),
            "text": (
                f'Issue #{data["issue_number"]}: {data["title"]}\n'
                f'{"─" * 20}\n\n'
                f'{body}\n\n'
                f'{"── 评论 ──" if comments else ""}\n{comments_text}'
            ),
        }

    @classmethod
    def _build_pr_detail(cls, data: dict) -> Dict[str, str]:
        body = data.get("pr_body", "")
        comments: List[dict] = data.get("pr_comments", [])

        body_html = _md_to_html(body)
        comments_html = ''.join(cls._build_comment_html(c) for c in comments)
        comments_md = '\n'.join(cls._build_comment_md(c) for c in comments)
        comments_text = '\n'.join(cls._build_comment_text(c) for c in comments)

        return {
            "html": (
                f'<div style="padding:12px;border-radius:8px;">'
                f'<div style="font-size:15px;font-weight:bold;margin-bottom:8px;color:{cls.PRIMARY_COLOR};">'
                f'PR #{data["pr_number"]}: {data["title"]}</div>'
                f'<div style="font-size:13px;color:#333;margin-bottom:12px;line-height:1.6;">{body_html}</div>'
                f'{comments_html}'
                f'</div>'
            ),
            "markdown": (
                f'**PR #{data["pr_number"]}: {data["title"]}**\n\n'
                f'{body}\n\n'
                f'{"── 评论 ──" if comments else ""}\n{comments_md}'
            ),
            "text": (
                f'PR #{data["pr_number"]}: {data["title"]}\n'
                f'{"─" * 20}\n\n'
                f'{body}\n\n'
                f'{"── 评论 ──" if comments else ""}\n{comments_text}'
            ),
        }


class GitHubParser:
    def __init__(self, logger, config: dict):
        self.logger = logger
        self.config = config
        self._cache: Dict[str, Tuple[dict, float]] = {}
        self._cache_ttl = config.get("cache_ttl", 600)

        gh_config = sdk.config.getConfig("GitHubParser") or {}
        self.gh_token = gh_config.get("token", "")
        if not self.gh_token:
            sdk.config.setConfig("GitHubParser", {"token": ""})
            self.logger.warning("未找到GitHub API令牌，你可以在你的配置文件填入token，或者你也可以不填")
            self.gh_token = ""

        self.headers = {"Authorization": f"token {self.gh_token}"} if self.gh_token else {}

    def _get_cache(self, key: str) -> Optional[dict]:
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        self._cache[key] = (data, time.time())
        now = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if now - ts > self._cache_ttl]
        for k in expired:
            del self._cache[k]

    async def _fetch_github_data(self, url: str) -> Optional[Dict]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if not isinstance(data, dict):
                            self.logger.error(f"GitHub API返回无效数据类型: {type(data)}")
                            return None
                        return data
                    elif response.status == 404:
                        self.logger.warning(f"GitHub资源不存在: {url}")
                    else:
                        self.logger.error(f"GitHub API请求失败: {response.status}")
        except Exception as e:
            self.logger.error(f"获取GitHub数据时出错: {str(e)}")
        return None

    async def _fetch_github_list(self, url: str) -> List[Dict]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            return data
                    return []
        except Exception:
            return []

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return "未知"
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y年%m月%d日")

    async def _fetch_readme(self, owner: str, repo: str, branch: str) -> Optional[Dict]:
        readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        data = await self._fetch_github_data(readme_url)
        if not data or "content" not in data:
            return None

        try:
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            resolved = _resolve_relative_urls(content, owner, repo, branch)

            return {
                "raw": resolved,
                "html": _md_to_html(resolved),
            }
        except Exception as e:
            self.logger.debug(f"解析README内容失败: {e}")
            return None

    async def _fetch_issue_comments(self, owner: str, repo: str, issue_num: str) -> List[dict]:
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/comments"
        raw = await self._fetch_github_list(url)
        return [
            {
                "user": c.get("user", {}).get("login", "未知用户"),
                "body": c.get("body", ""),
            }
            for c in raw
        ]

    async def _fetch_pr_comments(self, owner: str, repo: str, pr_num: str) -> List[dict]:
        review_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}/comments"
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_num}/comments"
        review_raw = await self._fetch_github_list(review_url)
        issue_raw = await self._fetch_github_list(issue_url)

        seen = set()
        comments = []
        for c in review_raw + issue_raw:
            login = c.get("user", {}).get("login", "未知用户")
            body = c.get("body", "")
            key = (login, body)
            if key not in seen:
                seen.add(key)
                comments.append({"user": login, "body": body})
        return comments

    async def parse_github_url(self, url: str) -> Optional[Dict]:
        cached = self._get_cache(url)
        if cached:
            return cached

        try:
            match = _GITHUB_LINK_REGEX.match(url)
            if not match:
                return None

            owner, repo, issue_num, pr_num, branch, blob_path = match.groups()

            result = {
                "type": "repository",
                "url": url,
                "owner": owner,
                "repo": repo,
                "full_name": f"{owner}/{repo}",
                "api_url": f"https://api.github.com/repos/{owner}/{repo}",
                "is_issue": issue_num is not None,
                "is_pr": pr_num is not None,
                "is_branch": branch is not None,
                "is_blob": blob_path is not None,
            }

            repo_data = await self._fetch_github_data(result["api_url"])
            if repo_data is None:
                self.logger.warning(f"获取仓库信息失败: {result['api_url']}")
                return None

            default_branch = repo_data.get("default_branch", "main")

            result.update({
                "description": repo_data.get("description") if repo_data.get("description") is not None else "",
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "language": repo_data.get("language", "未知"),
                "license": repo_data.get("license", {}).get("name", "无") if repo_data.get("license") is not None else "无",
                "created_at": self._format_date(repo_data.get("created_at", "")),
                "updated_at": self._format_date(repo_data.get("updated_at", "")),
                "homepage": repo_data.get("homepage", ""),
                "topics": repo_data.get("topics", []),
                "default_branch": default_branch,
            })

            if issue_num:
                issue_url = f"{result['api_url']}/issues/{issue_num}"
                issue_data = await self._fetch_github_data(issue_url)
                if issue_data is None:
                    self.logger.warning(f"获取issue信息失败: {issue_url}")
                    return None

                result.update({
                    "type": "issue",
                    "issue_number": issue_num,
                    "title": issue_data.get("title", ""),
                    "state": "开启" if issue_data.get("state") == "open" else "关闭",
                    "user": issue_data.get("user", {}).get("login", "未知用户") if issue_data.get("user") is not None else "未知用户",
                    "comments": issue_data.get("comments", 0),
                    "issue_body": issue_data.get("body", ""),
                    "created_at": self._format_date(issue_data.get("created_at", "")),
                    "updated_at": self._format_date(issue_data.get("updated_at", "")),
                    "closed_at": self._format_date(issue_data.get("closed_at", "")),
                })

                result["issue_comments"] = await self._fetch_issue_comments(owner, repo, issue_num)

            elif pr_num:
                pr_url = f"{result['api_url']}/pulls/{pr_num}"
                pr_data = await self._fetch_github_data(pr_url)
                if pr_data is None:
                    self.logger.warning(f"获取PR信息失败: {pr_url}")
                    return None

                result.update({
                    "type": "pull_request",
                    "pr_number": pr_num,
                    "title": pr_data.get("title", ""),
                    "state": "开启" if pr_data.get("state") == "open" else "关闭",
                    "user": pr_data.get("user", {}).get("login", "未知用户") if pr_data.get("user") is not None else "未知用户",
                    "comments": pr_data.get("comments", 0),
                    "commits": pr_data.get("commits", 0),
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "changed_files": pr_data.get("changed_files", 0),
                    "pr_body": pr_data.get("body", ""),
                    "created_at": self._format_date(pr_data.get("created_at", "")),
                    "updated_at": self._format_date(pr_data.get("updated_at", "")),
                    "closed_at": self._format_date(pr_data.get("closed_at", "")),
                    "merged_at": self._format_date(pr_data.get("merged_at", "")),
                })

                result["pr_comments"] = await self._fetch_pr_comments(owner, repo, pr_num)

            if result["type"] == "repository" and self.config.get("show_readme", True):
                readme = await self._fetch_readme(owner, repo, default_branch)
                if readme:
                    result["readme_content"] = readme["raw"]
                    result["readme_html"] = readme["html"]

            self._set_cache(url, result)
            return result
        except Exception as e:
            self.logger.error(f"解析GitHub URL时出错: {str(e)}")
            return None


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubParser")
        self.config = self._load_config()
        self.parser = GitHubParser(self.logger, self.config)

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(
            lazy_load=False,
            priority=0,
        )

    def _load_config(self) -> dict:
        config = sdk.config.getConfig("GitHubParser")
        if not config or not isinstance(config, dict):
            default_config = {
                "show_readme": True,
                "cache_ttl": 600,
                "show_topics": True,
                "max_urls_per_message": 3,
            }
            sdk.config.setConfig("GitHubParser", default_config, immediate=True)
            self.logger.info("已创建默认配置")
            return default_config
        return config

    async def on_load(self, event):
        self._register_auto_parse()
        self.logger.info("GitHub解析模块已加载")

    async def on_unload(self, event):
        self.logger.info("GitHub解析模块已卸载")

    def _register_auto_parse(self):
        @message.on_message(priority=50)
        async def auto_parse_handler(event):
            if event.is_command():
                return

            text = event.get_text()
            if not text:
                return

            urls = _GITHUB_URL_REGEX.findall(text)
            if not urls:
                return

            max_count = self.config.get("max_urls_per_message", 3)
            for url in urls[:max_count]:
                await self._send_github_info(event, url)

    def _select_best_format(self, platform: str, templates: Dict[str, str]) -> tuple:
        try:
            supported_methods = sdk.adapter.list_sends(platform)
            if "Html" in supported_methods:
                return ("Html", templates["html"])
            elif "Markdown" in supported_methods:
                return ("Markdown", templates["markdown"])
            else:
                return ("Text", templates["text"])
        except Exception:
            return ("Text", templates["text"])

    async def _send_with_fallback(self, event, templates: Dict[str, str], fmt_name: str):
        if fmt_name == "Html":
            try:
                await event.reply(templates["html"], method="Html")
                return
            except Exception:
                pass
        if fmt_name in ("Html", "Markdown"):
            try:
                await event.reply(templates["markdown"], method="Markdown")
                return
            except Exception:
                pass
        await event.reply(templates["text"])

    async def _send_github_info(self, event, url: str):
        data = await self.parser.parse_github_url(url)
        if not data:
            return

        templates_set = GitHubTemplates.build_card(data, self.config)
        platform = event.get_platform()
        fmt_name, content = self._select_best_format(platform, templates_set)

        try:
            await event.reply(content, method=fmt_name)
        except Exception:
            try:
                await event.reply(templates_set["text"])
                fmt_name = "Text"
            except Exception:
                return

        hint = GitHubTemplates._get_hint(data)
        if not hint["has_detail"]:
            return

        async def on_detail_reply(reply_event):
            text = reply_event.get_text().strip()
            if "看一下" not in text:
                return

            detail = GitHubTemplates.build_detail(data)
            if not detail:
                return
            await self._send_with_fallback(reply_event, detail, fmt_name)

        await event.wait_reply(
            timeout=60,
            callback=on_detail_reply,
        )
