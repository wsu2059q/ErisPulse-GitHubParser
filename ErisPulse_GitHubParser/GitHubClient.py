import base64
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ErisPulse import sdk


_GRAPHQL_URL = "https://api.github.com/graphql"
_REST = "https://api.github.com"
_CONTRIB_SVG_URL = "https://github.com/users/{user}/contributions"

_RECT_RE = re.compile(r'<rect\b[^>]*data-date="([^"]+)"[^>]*?/?>')
_ATTR_RE = {
    "count": re.compile(r'data-count="(\d+)"'),
    "level": re.compile(r'data-level="(\d+)"'),
}


def _level_from_count(count: int) -> int:
    if count <= 0:
        return 0
    if count < 9:
        return 1
    if count < 17:
        return 2
    if count < 25:
        return 3
    return 4


def parse_contrib_svg(svg_text: str) -> Dict[str, Any]:
    days: List[Dict[str, Any]] = []
    for m in _RECT_RE.finditer(svg_text or ""):
        blob = m.group(0)
        date = m.group(1)
        cm = _ATTR_RE["count"].search(blob)
        lm = _ATTR_RE["level"].search(blob)
        count = int(cm.group(1)) if cm else 0
        level = int(lm.group(1)) if lm else _level_from_count(count)
        days.append({"date": date, "count": count, "level": level})
    if not days:
        raise ValueError("no contribution rects parsed")
    days.sort(key=lambda d: d["date"])
    weeks: List[List[Dict[str, Any]]] = []
    for i in range(0, len(days), 7):
        weeks.append(days[i:i + 7])
    total = sum(d["count"] for d in days)
    return {"total": total, "weeks": weeks, "days": days, "source": "scrape"}


class GitHubError(Exception):
    def __init__(self, message: str, status: int = 0, kind: str = ""):
        super().__init__(message)
        self.status = status
        self.kind = kind


class GitHubClient:
    def __init__(self, token: str = "", cache_ttl: int = 600):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubParser.GitHub")
        self.client = sdk.client
        self.token = (token or "").strip()
        self.cache_ttl = max(30, int(cache_ttl))
        self._cache: Dict[str, Tuple[Any, float]] = {}

        if self.token:
            self.logger.info("GitHub token 已配置，匿名速率限制解除（5000/h）")
        else:
            self.logger.warning("未配置 GitHub token，匿名访问速率受限（60/h），建议在配置中填写 token")

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    def _get_cache(self, key: str) -> Optional[Any]:
        ent = self._cache.get(key)
        if ent is None:
            return None
        data, ts = ent
        if time.time() - ts < self.cache_ttl:
            return data
        self._cache.pop(key, None)
        return None

    def _set_cache(self, key: str, data: Any) -> Any:
        self._cache[key] = (data, time.time())
        if len(self._cache) > 256:
            now = time.time()
            for k in [k for k, (_, ts) in self._cache.items() if now - ts > self.cache_ttl]:
                self._cache.pop(k, None)
        return data

    async def _get_json(self, url: str) -> Tuple[int, Any]:
        try:
            resp = await self.client.get(url, headers=self._headers(), timeout=20)
        except Exception as e:
            raise GitHubError(f"网络请求失败: {e}", kind="network") from None
        status = getattr(resp, "status", 0)
        try:
            data = await resp.json()
        except Exception:
            data = None
        return status, data

    async def _post_json(self, url: str, payload: Dict[str, Any]) -> Tuple[int, Any]:
        try:
            resp = await self.client.post(
                url, headers=self._headers({"Content-Type": "application/json"}),
                json=payload, timeout=20,
            )
        except Exception as e:
            raise GitHubError(f"网络请求失败: {e}", kind="network") from None
        status = getattr(resp, "status", 0)
        try:
            data = await resp.json()
        except Exception:
            data = None
        return status, data

    def _check_common(self, status: int, data: Any, resource: str):
        if status == 200:
            return
        if status == 404:
            raise GitHubError(f"未找到 {resource}", status=404, kind="not_found")
        if status == 403:
            remaining = self._extract_remaining(data)
            if remaining == 0:
                raise GitHubError("GitHub API 速率限制已达上限，请稍后再试或配置 token", status=403, kind="rate_limit")
            raise GitHubError(f"访问被拒绝（{resource}）", status=403, kind="forbidden")
        msg = ""
        if isinstance(data, dict):
            msg = data.get("message") or ""
        raise GitHubError(f"GitHub API 返回 {status}: {msg or resource}", status=status, kind="error")

    @staticmethod
    def _extract_remaining(data: Any) -> Optional[int]:
        if isinstance(data, dict):
            rate = data.get("rate") or {}
            if isinstance(rate, dict) and "remaining" in rate:
                return int(rate["remaining"])
        return None

    async def get_user(self, username: str) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        if not username:
            raise GitHubError("用户名不能为空", kind="invalid")
        key = f"user:{username}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        status, data = await self._get_json(f"{_REST}/users/{username}")
        self._check_common(status, data, f"用户 {username}")
        if not isinstance(data, dict):
            raise GitHubError("用户数据格式异常", kind="error")
        result = {
            "login": data.get("login", username),
            "name": data.get("name") or data.get("login", username),
            "avatar_url": data.get("avatar_url", ""),
            "bio": data.get("bio") or "",
            "company": data.get("company") or "",
            "location": data.get("location") or "",
            "blog": data.get("blog") or "",
            "followers": data.get("followers", 0),
            "following": data.get("following", 0),
            "public_repos": data.get("public_repos", 0),
            "public_gists": data.get("public_gists", 0),
            "created_at": self._fmt_date(data.get("created_at", "")),
            "html_url": data.get("html_url", f"https://github.com/{username}"),
            "type": data.get("type", "User"),
        }
        return self._set_cache(key, result)

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        owner = (owner or "").strip().lstrip("@")
        repo = (repo or "").strip().rstrip("/")
        if not owner or not repo:
            raise GitHubError("仓库地址格式应为 owner/repo", kind="invalid")
        key = f"repo:{owner}/{repo}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        status, data = await self._get_json(f"{_REST}/repos/{owner}/{repo}")
        self._check_common(status, data, f"仓库 {owner}/{repo}")
        if not isinstance(data, dict):
            raise GitHubError("仓库数据格式异常", kind="error")
        lic = data.get("license") or {}
        result = {
            "full_name": data.get("full_name", f"{owner}/{repo}"),
            "name": data.get("name", repo),
            "owner": data.get("owner", {}).get("login", owner) if isinstance(data.get("owner"), dict) else owner,
            "description": data.get("description") or "暂无描述",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "watchers": data.get("subscribers_count") or data.get("watchers_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language") or "未指定",
            "license": lic.get("name") or "无",
            "homepage": data.get("homepage") or "",
            "topics": data.get("topics") or [],
            "default_branch": data.get("default_branch", "main"),
            "created_at": self._fmt_date(data.get("created_at", "")),
            "updated_at": self._fmt_date(data.get("updated_at", "")),
            "pushed_at": self._fmt_date(data.get("pushed_at", "")),
            "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
            "archived": bool(data.get("archived")),
            "fork": bool(data.get("fork")),
        }
        return self._set_cache(key, result)

    async def get_commits(self, owner: str, repo: str, limit: int = 5) -> List[Dict[str, Any]]:
        owner = (owner or "").strip().lstrip("@")
        repo = (repo or "").strip().rstrip("/")
        limit = max(1, min(10, int(limit)))
        key = f"commits:{owner}/{repo}:{limit}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        status, data = await self._get_json(
            f"{_REST}/repos/{owner}/{repo}/commits?per_page={limit}"
        )
        self._check_common(status, data, f"{owner}/{repo} 的提交")
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            commit = item.get("commit") or {}
            author = commit.get("author") or {}
            out.append({
                "sha": (item.get("sha") or "")[:7],
                "message": self._first_line(commit.get("message") or ""),
                "author": author.get("name") or (item.get("author") or {}).get("login") or "未知",
                "date": self._fmt_date(author.get("date") or ""),
                "html_url": item.get("html_url", ""),
            })
        return self._set_cache(key, out)

    async def get_issue(self, owner: str, repo: str, number: int) -> Dict[str, Any]:
        return await self._get_issue_pr("issue", owner, repo, number)

    async def get_pr(self, owner: str, repo: str, number: int) -> Dict[str, Any]:
        return await self._get_issue_pr("pr", owner, repo, number)

    async def _get_issue_pr(self, kind: str, owner: str, repo: str, number) -> Dict[str, Any]:
        owner = (owner or "").strip().lstrip("@")
        repo = (repo or "").strip().rstrip("/")
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise GitHubError("编号必须为数字", kind="invalid")
        if not owner or not repo:
            raise GitHubError("地址格式应为 owner/repo", kind="invalid")
        key = f"{kind}:{owner}/{repo}/{number}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        endpoint = "pulls" if kind == "pr" else "issues"
        status, data = await self._get_json(f"{_REST}/repos/{owner}/{repo}/{endpoint}/{number}")
        self._check_common(status, data, f"{owner}/{repo} #{number}")
        if not isinstance(data, dict):
            raise GitHubError("数据格式异常", kind="error")
        result = {
            "number": data.get("number", number),
            "title": data.get("title") or "(无标题)",
            "state": data.get("state", "open"),
            "user": (data.get("user") or {}).get("login", "未知") if isinstance(data.get("user"), dict) else "未知",
            "comments": data.get("comments", 0),
            "created_at": self._fmt_date(data.get("created_at", "")),
            "closed_at": self._fmt_date(data.get("closed_at", "")) if data.get("closed_at") else "—",
            "html_url": data.get("html_url", ""),
            "assignees": [a.get("login", "") for a in (data.get("assignees") or []) if isinstance(a, dict)],
            "labels": [l.get("name", "") for l in (data.get("labels") or []) if isinstance(l, dict)],
            "merged_at": self._fmt_date(data.get("merged_at", "")) if data.get("merged_at") else "",
        }
        if kind == "pr":
            result.update({
                "commits": data.get("commits", 0),
                "additions": data.get("additions", 0),
                "deletions": data.get("deletions", 0),
                "changed_files": data.get("changed_files", 0),
                "draft": bool(data.get("draft")),
            })
        return self._set_cache(key, result)

    async def get_issue_comments(self, owner: str, repo: str, number, limit: int = 3) -> List[Dict[str, Any]]:
        owner = (owner or "").strip().lstrip("@")
        repo = (repo or "").strip().rstrip("/")
        try:
            number = int(number)
            limit = max(1, min(10, int(limit)))
        except (TypeError, ValueError):
            raise GitHubError("编号必须为数字", kind="invalid")
        key = f"comments:{owner}/{repo}/{number}:{limit}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        status, data = await self._get_json(
            f"{_REST}/repos/{owner}/{repo}/issues/{number}/comments?per_page={limit}"
        )
        self._check_common(status, data, f"{owner}/{repo} #{number} 评论")
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        for c in data[:limit]:
            if not isinstance(c, dict):
                continue
            body = (c.get("body") or "").strip()
            if not body:
                continue
            out.append({
                "user": (c.get("user") or {}).get("login", "未知") if isinstance(c.get("user"), dict) else "未知",
                "body": body,
                "created_at": self._fmt_date(c.get("created_at") or ""),
            })
        return self._set_cache(key, out)

    async def get_languages(self, owner: str, repo: str) -> Dict[str, int]:
        owner = (owner or "").strip().lstrip("@")
        repo = (repo or "").strip().rstrip("/")
        if not owner or not repo:
            raise GitHubError("地址格式应为 owner/repo", kind="invalid")
        key = f"langs:{owner}/{repo}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        status, data = await self._get_json(f"{_REST}/repos/{owner}/{repo}/languages")
        self._check_common(status, data, f"{owner}/{repo} 语言")
        if not isinstance(data, dict) or not data:
            raise GitHubError("无语言数据", kind="not_found")
        cleaned = {str(k): int(v) for k, v in data.items() if isinstance(v, (int, float))}
        if not cleaned:
            raise GitHubError("无语言数据", kind="not_found")
        return self._set_cache(key, cleaned)

    async def get_contributions(self, username: str) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        if not username:
            raise GitHubError("用户名不能为空", kind="invalid")
        key = f"contrib:{username}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        if self.token:
            try:
                result = await self._contrib_graphql(username)
            except GitHubError as e:
                if e.kind in ("not_found", "invalid"):
                    raise
                self.logger.warning(f"GraphQL 获取贡献失败，回退到网页抓取: {e}")
                result = await self._contrib_scrape(username)
        else:
            result = await self._contrib_scrape(username)
        return self._set_cache(key, result)

    async def _contrib_graphql(self, username: str) -> Dict[str, Any]:
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays { contributionCount date color }
                }
              }
            }
          }
        }
        """
        status, data = await self._post_json(
            _GRAPHQL_URL, {"query": query, "variables": {"login": username}}
        )
        if status == 401:
            raise GitHubError("token 无效或已过期", status=401, kind="auth")
        if status != 200 or not isinstance(data, dict):
            self._check_common(status, data, f"用户 {username} 的贡献")
        errors = data.get("errors") if isinstance(data, dict) else None
        if errors:
            msg = errors[0].get("message", "GraphQL 错误") if errors else "GraphQL 错误"
            raise GitHubError(f"GraphQL: {msg}", kind="error")
        cal = (((data.get("data") or {}).get("user") or {})
               .get("contributionsCollection") or {}).get("contributionCalendar") or {}
        total = int(cal.get("totalContributions", 0))
        weeks_raw = cal.get("weeks") or []
        weeks: List[List[Dict[str, Any]]] = []
        all_days: List[Dict[str, Any]] = []
        for w in weeks_raw:
            col = []
            for d in (w.get("contributionDays") or []):
                count = int(d.get("contributionCount", 0))
                day = {
                    "date": d.get("date", ""),
                    "count": count,
                    "level": _level_from_count(count),
                }
                col.append(day)
                all_days.append(day)
            weeks.append(col)
        return {"total": total, "weeks": weeks, "days": all_days, "source": "graphql"}

    async def _contrib_scrape(self, username: str) -> Dict[str, Any]:
        try:
            resp = await self.client.get(
                _CONTRIB_SVG_URL.format(user=username),
                headers={"Accept": "image/svg+xml"}, timeout=20,
            )
        except Exception as e:
            raise GitHubError(f"获取贡献页失败: {e}", kind="network") from None
        status = getattr(resp, "status", 0)
        if status == 404:
            raise GitHubError(f"未找到用户 {username}", status=404, kind="not_found")
        if status != 200:
            raise GitHubError(f"贡献页返回 {status}", status=status, kind="error")
        try:
            svg = await resp.text()
        except Exception:
            try:
                raw = await resp.read()
                svg = raw.decode("utf-8", "replace")
            except Exception as e:
                raise GitHubError(f"读取贡献页失败: {e}", kind="error") from None
        try:
            return parse_contrib_svg(svg)
        except ValueError:
            raise GitHubError(
                f"未能从贡献页解析到数据（用户 {username} 可能无贡献记录，或 GitHub 页面结构已变更；建议配置 token 走 GraphQL）",
                kind="error",
            ) from None

    async def fetch_avatar_data_uri(self, avatar_url: str) -> Optional[str]:
        if not avatar_url:
            return None
        key = f"avatar:{avatar_url}"
        cached = self._get_cache(key)
        if cached is not None:
            return cached
        try:
            resp = await self.client.get(avatar_url, headers={"Accept": "image/*"}, timeout=15)
        except Exception as e:
            self.logger.warning(f"获取头像失败: {e}")
            return None
        if getattr(resp, "status", 0) != 200:
            return None
        try:
            raw = await resp.read()
        except Exception as e:
            self.logger.warning(f"读取头像字节失败: {e}")
            return None
        if not raw:
            return None
        b64 = base64.b64encode(raw).decode("ascii")
        return self._set_cache(key, f"data:image/png;base64,{b64}")

    async def rate_limit(self) -> Dict[str, Any]:
        status, data = await self._get_json(f"{_REST}/rate_limit")
        if status != 200 or not isinstance(data, dict):
            return {"available": False}
        core = (data.get("resources") or {}).get("core") or {}
        return {
            "available": True,
            "limit": core.get("limit", 0),
            "remaining": core.get("remaining", 0),
            "used": core.get("used", 0),
            "reset": core.get("reset", 0),
            "reset_at": datetime.fromtimestamp(core.get("reset", 0), tz=timezone.utc).isoformat(),
            "has_token": bool(self.token),
        }

    @staticmethod
    def _first_line(text: str) -> str:
        text = (text or "").strip()
        return text.split("\n", 1)[0].strip() if text else "(无提交信息)"

    @staticmethod
    def _fmt_date(date_str: str) -> str:
        if not date_str:
            return "未知"
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return date_str
