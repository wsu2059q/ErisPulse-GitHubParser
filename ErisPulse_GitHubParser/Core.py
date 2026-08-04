import re
from typing import Any, Dict, Optional, Tuple

from ErisPulse import i18n, sdk
from ErisPulse.Core.Bases import BaseModule
from ErisPulse.Core.Event import command, message

from .GitHubClient import GitHubClient, GitHubError
from .I18n import register as _register_i18n
from .TextTemplates import render_text
from .Visualizer import Visualizer

_GH_URL_FIND = re.compile(r'https?://(?:www\.)?github\.com/[A-Za-z0-9_.\-/]+')

_GH_RESERVED = {
    "settings", "orgs", "notifications", "search", "explore", "trending",
    "topics", "collections", "events", "about", "pricing", "security",
    "contact", "login", "join", "features", "enterprise", "sponsors",
    "marketplace", "pulls", "issues", "stars", "new", "import", "gist",
    "sessions", "team", "organizations", "opensource", "resources",
    "customer-stories", "site-resources", "secure-open-source", "blog",
}


def _parse_gh_url(url: str) -> Optional[Tuple[str, str, str, Any]]:
    url = url.split("#", 1)[0].split("?", 1)[0].rstrip(").,;]")
    m = re.match(r'https?://(?:www\.)?github\.com/(.+)', url)
    if not m:
        return None
    path = m.group(1).strip("/")
    if not path:
        return None
    parts = path.split("/")
    owner = parts[0]
    if owner.lower() in _GH_RESERVED:
        return None
    if len(parts) == 1:
        return ("user", owner, "", "")
    repo = parts[1]
    if not repo or repo.lower() in _GH_RESERVED:
        return None
    if len(parts) == 2:
        return ("repo", owner, repo, "")
    sub = parts[2].lower()
    if sub == "issues" and len(parts) >= 4 and parts[3].isdigit():
        return ("issue", owner, repo, int(parts[3]))
    if sub in ("pull", "pulls") and len(parts) >= 4 and parts[3].isdigit():
        return ("pr", owner, repo, int(parts[3]))
    if sub in ("commit", "commits"):
        return ("commits", owner, repo, "")
    return ("repo", owner, repo, "")


def _split_owner_repo(target: str) -> Tuple[str, str]:
    target = (target or "").strip().lstrip("@").rstrip("/")
    if "/" in target:
        owner, repo = target.split("/", 1)
        return owner.strip(), repo.strip()
    return target, ""


_DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "token": "",
    "theme": "auto",
    "utc_offset": 8,
    "auto_parse": True,
    "auto_parse_max": 3,
    "image_enabled": True,
    "show_topics": True,
    "avatar_enabled": True,
    "issue_comments": True,
    "issue_comments_max": 3,
    "comment_max_len": 120,
    "cache_ttl": 600,
    "lang": "auto",
}


class Main(BaseModule):
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger.get_child("GitHubParser")
        self.config = self._load_config()
        self._client: Optional[GitHubClient] = None
        self._viz: Optional[Visualizer] = None

    @staticmethod
    def get_load_strategy():
        from ErisPulse.loaders import ModuleLoadStrategy
        return ModuleLoadStrategy(lazy_load=False, priority=0)

    def _t(self, key: str, default: str = "", **kw) -> str:
        return i18n.t(key, default=default, **kw)

    def _load_config(self) -> Dict[str, Any]:
        config = sdk.config.getConfig("GitHubParser")
        if not config or not isinstance(config, dict):
            sdk.config.setConfig("GitHubParser", dict(_DEFAULT_CONFIG), immediate=True)
            self.logger.info("已写入 GitHubParser 默认配置")
            return dict(_DEFAULT_CONFIG)
        changed = False
        for k, v in _DEFAULT_CONFIG.items():
            if k not in config:
                config[k] = v
                changed = True
        if changed:
            sdk.config.setConfig("GitHubParser", config, immediate=True)
        return config

    def _resolve_lang(self) -> str:
        cfg_lang = (self.config.get("lang") or "auto").strip()
        if cfg_lang == "auto":
            try:
                cur = i18n.get_language() or ""
            except Exception:
                cur = ""
            if isinstance(cur, str) and cur:
                return cur if not cur.startswith("en") else "en"
            return "zh-CN"
        return cfg_lang

    async def on_load(self, event) -> bool:
        _register_i18n(i18n)
        self._client = GitHubClient(
            token=self.config.get("token", ""),
            cache_ttl=self.config.get("cache_ttl", 600),
        )
        self.config["lang"] = self._resolve_lang()
        self._viz = Visualizer(self.sdk, self.config)
        self._register_passive()
        self._register_commands()
        self._register_routes()
        self.logger.info(self._t(
            "ghparser.loaded", "GitHubParser loaded",
            auto=str(self.config.get("auto_parse")),
            image=str(self.config.get("image_enabled")),
            token=self._t("ghparser.token_yes") if self.config.get("token") else self._t("ghparser.token_no"),
        ))
        return True

    async def on_unload(self, event) -> bool:
        self._unregister_routes()
        self.logger.info(self._t("ghparser.unloaded", "GitHubParser unloaded"))
        return True

    def _register_passive(self):
        if not self.config.get("auto_parse", True):
            self.logger.info(self._t("ghparser.passive_skip", "passive off"))
            return

        @message.on_message(priority=50)
        async def on_message(event):
            if event.is_command():
                return
            text = event.get_text() or ""
            if "github.com" not in text:
                return
            urls = _GH_URL_FIND.findall(text)
            if not urls:
                return
            seen = set()
            uniq = []
            for u in urls:
                if u not in seen:
                    seen.add(u)
                    uniq.append(u)
            max_n = max(1, min(5, int(self.config.get("auto_parse_max", 3))))
            for url in uniq[:max_n]:
                parsed = _parse_gh_url(url)
                if not parsed:
                    continue
                try:
                    await self._dispatch(event, parsed, passive=True)
                except GitHubError as e:
                    self.logger.debug(f"被动解析失败 {url}: {e}")
                except Exception as e:
                    self.logger.warning(f"被动解析异常 {url}: {e}")

    def _register_commands(self):
        @command("gh", help="GitHubParser：状态 / 开关 / 额度 / 手动卡片")
        async def gh_cmd(event):
            args = event.get_command_args() or []
            sub = args[0].lower() if args else ""
            if sub in ("on", "enable"):
                await self._set_toggle(event, "auto_parse", True,
                                       self._t("ghparser.auto_on"))
            elif sub in ("off", "disable"):
                await self._set_toggle(event, "auto_parse", False,
                                       self._t("ghparser.auto_off"))
            elif sub == "toggle":
                cur = self.config.get("auto_parse", True)
                state = self._t("ghparser.toggle_on") if not cur else self._t("ghparser.toggle_off")
                await self._set_toggle(event, "auto_parse", not cur,
                                       self._t("ghparser.auto_toggled", state=state))
            elif sub == "image":
                if len(args) < 2:
                    st = self._t("ghparser.toggle_on") if self.config.get("image_enabled") else self._t("ghparser.toggle_off")
                    await event.reply(self._t("ghparser.image_status", state=st))
                    return
                val = args[1].lower() in ("on", "1", "true", "yes")
                await self._set_toggle(
                    event, "image_enabled", val,
                    self._t("ghparser.image_on") if val else self._t("ghparser.image_off"))
            elif sub == "rate":
                await self._cmd_rate(event)
            elif sub == "heat":
                rest = args[1:]
                if not rest:
                    await event.reply(self._t("ghparser.usage_heat"))
                    return
                await self._dispatch(event, ("heat", " ".join(rest), "", ""), passive=False)
            elif sub in ("langs", "languages"):
                owner, repo = _split_owner_repo(" ".join(args[1:]))
                if not owner or not repo:
                    await event.reply(self._t("ghparser.usage_langs"))
                    return
                await self._dispatch(event, ("langs", owner, repo, ""), passive=False)
            else:
                await event.reply(self._status_text())

    async def _set_toggle(self, event, key: str, value: bool, msg: str):
        self.config[key] = value
        try:
            sdk.config.setConfig("GitHubParser", self.config, immediate=True)
        except Exception as e:
            self.logger.warning(f"保存配置失败: {e}")
        await event.reply(self._t("ghparser.saved", msg=msg, default=msg))

    async def _cmd_rate(self, event):
        try:
            info = await self._client.rate_limit()
        except Exception as e:
            await event.reply(self._t("ghparser.rate_fail", err=str(e)))
            return
        if not info.get("available"):
            await event.reply(self._t("ghparser.rate_unavailable"))
            return
        reset = (info.get("reset_at") or "?").replace("T", " ").replace("Z", "")
        token_line = (self._t("ghparser.rate_token_on") if info.get("has_token")
                      else self._t("ghparser.rate_token_off"))
        await event.reply("\n".join([
            self._t("ghparser.rate_title"),
            self._t("ghparser.rate_line", remaining=info["remaining"], limit=info["limit"], used=info["used"]),
            self._t("ghparser.rate_reset", reset=reset),
            token_line,
        ]))

    def _status_text(self) -> str:
        on = self._t("ghparser.toggle_on")
        off = self._t("ghparser.toggle_off")
        return self._t(
            "ghparser.help",
            auto=(on if self.config.get("auto_parse") else off),
            image=(on if self.config.get("image_enabled") else off),
            token=(self._t("ghparser.token_yes") if self.config.get("token") else self._t("ghparser.token_no")),
            theme=self.config.get("theme", "auto"),
        )

    async def _card_bytes(self, kind, owner, repo, number):
        self.config["lang"] = self._resolve_lang()
        data = await self._fetch(kind, owner, repo, number)
        avatar = None
        if kind == "user" and self.config.get("avatar_enabled", True):
            try:
                avatar = await self._client.fetch_avatar_data_uri(data.get("avatar_url", ""))
            except Exception as e:
                self.logger.debug(self._t("ghparser.avatar_fail", err=str(e)))
        png = None
        if self.config.get("image_enabled", True):
            png = self._render_image(kind, owner, repo, data, avatar)
        return data, png

    async def _dispatch(self, event, parsed, passive: bool):
        kind, owner, repo, number = parsed
        try:
            data, png = await self._card_bytes(kind, owner, repo, number)
        except GitHubError as e:
            if passive:
                if e.kind in ("rate_limit", "not_found", "auth", "network", "forbidden", "invalid"):
                    await event.reply(self._error_msg(e))
                else:
                    self.logger.warning(f"被动解析失败 {kind} {owner}/{repo}/{number}: {e}")
            else:
                await event.reply(self._error_msg(e))
            return

        if png is not None:
            try:
                await event.reply(png, method="Image")
                return
            except Exception as e:
                self.logger.warning(self._t("ghparser.send_fail_log", err=str(e)))

        await event.reply(render_text(kind, owner, repo, number, data, self.config["lang"]))

    def _register_routes(self):
        r = self.sdk.router
        r.register_http_route("GitHubParser", "/", handler=self._api_info, methods=["GET"])
        r.register_http_route("GitHubParser", "/status", handler=self._api_status, methods=["GET"])
        r.register_http_route("GitHubParser", "/rate", handler=self._api_rate, methods=["GET"])
        r.register_http_route("GitHubParser", "/card", handler=self._api_card, methods=["GET"])

    def _unregister_routes(self):
        try:
            r = self.sdk.router
            for p in ["/", "/status", "/rate", "/card"]:
                try:
                    r.unregister_http_route("GitHubParser", p)
                except Exception:
                    pass
        except Exception:
            pass

    async def _api_info(self, request):
        return {
            "module": "GitHubParser",
            "description": "Passive GitHub link parsing with Takumi card images",
            "endpoints": ["/", "/status", "/rate", "/card?url=<github-link>"],
        }

    async def _api_status(self, request):
        return {
            "passive": bool(self.config.get("auto_parse")),
            "image": bool(self.config.get("image_enabled")),
            "token": bool(self.config.get("token")),
            "theme": self.config.get("theme", "auto"),
            "lang": self.config["lang"],
        }

    async def _api_rate(self, request):
        from fastapi.responses import JSONResponse
        try:
            return JSONResponse(await self._client.rate_limit())
        except Exception as e:
            return JSONResponse({"available": False, "error": str(e)}, status_code=500)

    async def _api_card(self, request):
        from fastapi.responses import JSONResponse, Response
        url = (request.query_params.get("url") or "").strip()
        parsed = _parse_gh_url(url) if url else None
        if not parsed:
            return JSONResponse({"ok": False, "error": "无法识别的 GitHub 链接，示例: ?url=https://github.com/o/r/issues/1"}, status_code=400)
        kind, owner, repo, number = parsed
        try:
            _, png = await self._card_bytes(kind, owner, repo, number)
        except GitHubError as e:
            return JSONResponse({"ok": False, "error": self._error_msg(e)})
        except Exception as e:
            self.logger.error(f"card API 异常: {e}", exc_info=True)
            return JSONResponse({"ok": False, "error": f"渲染异常: {e}"}, status_code=500)
        if png is None:
            return JSONResponse({"ok": False, "error": "图片不可用（Takumi 未安装或已关闭图片输出）"}, status_code=503)
        return Response(content=png, media_type="image/png")

    async def _fetch(self, kind, owner, repo, number):
        c = self._client
        if kind == "user":
            data = await c.get_user(owner)
        elif kind == "repo":
            data = await c.get_repo(owner, repo)
        elif kind == "issue":
            data = await c.get_issue(owner, repo, number)
        elif kind == "pr":
            data = await c.get_pr(owner, repo, number)
        elif kind == "commits":
            data = await c.get_commits(owner, repo, 5)
        elif kind == "langs":
            data = await c.get_languages(owner, repo)
        elif kind == "heat":
            data = await c.get_contributions(owner)
        else:
            raise GitHubError(f"未知类型: {kind}", kind="invalid")
        if kind in ("issue", "pr") and self.config.get("issue_comments", True):
            try:
                data = dict(data)
                data["comments_list"] = await c.get_issue_comments(
                    owner, repo, number, self.config.get("issue_comments_max", 3))
            except GitHubError as e:
                self.logger.debug(f"评论获取失败 {owner}/{repo}#{number}: {e}")
        return data

    def _render_image(self, kind, owner, repo, data, avatar=None):
        v = self._viz
        try:
            if kind == "user":
                return v.render_user(data, avatar)
            if kind == "repo":
                return v.render_repo(data, self.config.get("show_topics", True))
            if kind == "issue":
                return v.render_issue(f"{owner}/{repo}", data)
            if kind == "pr":
                return v.render_pr(f"{owner}/{repo}", data)
            if kind == "commits":
                return v.render_commits(f"{owner}/{repo}", data)
            if kind == "langs":
                return v.render_languages(f"{owner}/{repo}", data)
            if kind == "heat":
                return v.render_heatmap(owner, data)
        except Exception as e:
            self.logger.warning(self._t("ghparser.render_fail", kind=kind, err=str(e)))
        return None

    def _error_msg(self, e: GitHubError) -> str:
        msg = str(e)
        if e.kind == "not_found":
            return self._t("ghparser.err_not_found", msg=msg)
        if e.kind == "rate_limit":
            return self._t("ghparser.err_rate_limit", msg=msg)
        if e.kind == "auth":
            return self._t("ghparser.err_auth", msg=msg)
        if e.kind == "network":
            return self._t("ghparser.err_network", msg=msg)
        return self._t("ghparser.err_default", msg=msg)
