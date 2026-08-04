from typing import Dict

UI: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        "ghparser.loaded": "GitHubParser 已加载（被动={auto} 图片={image} token={token}）",
        "ghparser.unloaded": "GitHubParser 已卸载",
        "ghparser.help": (
            "GitHubParser\n"
            "  被动解析: {auto}  (/gh on|off)\n"
            "  图片输出: {image}  (/gh image on|off)\n"
            "  Token: {token}\n"
            "  主题: {theme}\n\n"
            "用法:\n"
            "  直接发 github.com 链接 → 自动出卡片\n"
            "  /gh rate              查看 API 余额\n"
            "  /gh heat <用户名>      贡献热力图\n"
            "  /gh langs <o/r>       语言占比饼图\n"
        ),
        "ghparser.auto_on": "被动解析已开启",
        "ghparser.auto_off": "被动解析已关闭",
        "ghparser.auto_toggled": "被动解析已{state}",
        "ghparser.image_status": "图片输出: {state}\n用法: /gh image on|off",
        "ghparser.image_on": "图片输出已开启",
        "ghparser.image_off": "图片输出已关闭",
        "ghparser.saved": "{msg}（已保存）",
        "ghparser.rate_title": "GitHub API 限额:",
        "ghparser.rate_line": "  剩余 {remaining} / {limit}（已用 {used}）",
        "ghparser.rate_reset": "  重置(UTC): {reset}",
        "ghparser.rate_token_on": "  Token: 已配置",
        "ghparser.rate_token_off": "  Token: 未配置（匿名 60/h）",
        "ghparser.rate_unavailable": "无法获取速率信息",
        "ghparser.rate_fail": "查询失败: {err}",
        "ghparser.usage_heat": "用法: /gh heat <用户名>\n例如: /gh heat torvalds",
        "ghparser.usage_langs": "用法: /gh langs <owner>/<repo>\n例如: /gh langs ErisPulse/ErisPulse",
        "ghparser.usage_image": "用法: /gh image on|off",
        "ghparser.err_not_found": "未找到: {msg}",
        "ghparser.err_rate_limit": "GitHub API 速率限制: {msg}\n建议配置 token（/gh rate 查看余额）",
        "ghparser.err_auth": "鉴权失败: {msg}",
        "ghparser.err_network": "网络错误: {msg}",
        "ghparser.err_default": "出错: {msg}",
        "ghparser.send_fail_log": "图片发送失败，降级文本: {err}",
        "ghparser.avatar_fail": "头像获取失败: {err}",
        "ghparser.render_fail": "渲染图片失败({kind}): {err}",
        "ghparser.passive_skip": "被动解析已关闭（auto_parse=false）",
        "ghparser.passive_off_log": "被动解析已关闭，跳过注册",
        "ghparser.toggle_on": "开启",
        "ghparser.toggle_off": "关闭",
        "ghparser.token_yes": "有",
        "ghparser.token_no": "无",
    },
    "en": {
        "ghparser.loaded": "GitHubParser loaded (passive={auto} image={image} token={token})",
        "ghparser.unloaded": "GitHubParser unloaded",
        "ghparser.help": (
            "GitHubParser\n"
            "  Passive: {auto}  (/gh on|off)\n"
            "  Image: {image}  (/gh image on|off)\n"
            "  Token: {token}\n"
            "  Theme: {theme}\n\n"
            "Usage:\n"
            "  Send any github.com link → auto card\n"
            "  /gh rate              API quota\n"
            "  /gh heat <user>       Contribution heatmap\n"
            "  /gh langs <o/r>       Language pie\n"
        ),
        "ghparser.auto_on": "Passive parsing enabled",
        "ghparser.auto_off": "Passive parsing disabled",
        "ghparser.auto_toggled": "Passive parsing {state}",
        "ghparser.image_status": "Image output: {state}\nUsage: /gh image on|off",
        "ghparser.image_on": "Image output enabled",
        "ghparser.image_off": "Image output disabled",
        "ghparser.saved": "{msg} (saved)",
        "ghparser.rate_title": "GitHub API quota:",
        "ghparser.rate_line": "  Remaining {remaining} / {limit} (used {used})",
        "ghparser.rate_reset": "  Reset(UTC): {reset}",
        "ghparser.rate_token_on": "  Token: configured",
        "ghparser.rate_token_off": "  Token: none (anonymous 60/h)",
        "ghparser.rate_unavailable": "Rate info unavailable",
        "ghparser.rate_fail": "Query failed: {err}",
        "ghparser.usage_heat": "Usage: /gh heat <user>\ne.g.: /gh heat torvalds",
        "ghparser.usage_langs": "Usage: /gh langs <owner>/<repo>\ne.g.: /gh langs ErisPulse/ErisPulse",
        "ghparser.usage_image": "Usage: /gh image on|off",
        "ghparser.err_not_found": "Not found: {msg}",
        "ghparser.err_rate_limit": "GitHub API rate limited: {msg}\nSet a token (/gh rate to check)",
        "ghparser.err_auth": "Auth failed: {msg}",
        "ghparser.err_network": "Network error: {msg}",
        "ghparser.err_default": "Error: {msg}",
        "ghparser.send_fail_log": "Image send failed, fallback to text: {err}",
        "ghparser.avatar_fail": "Avatar fetch failed: {err}",
        "ghparser.render_fail": "Render failed ({kind}): {err}",
        "ghparser.passive_skip": "Passive parsing off (auto_parse=false)",
        "ghparser.passive_off_log": "Passive parsing disabled, skip register",
        "ghparser.toggle_on": "on",
        "ghparser.toggle_off": "off",
        "ghparser.token_yes": "yes",
        "ghparser.token_no": "no",
    },
}

CARD: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        "repos": "仓库", "followers": "关注者", "following": "关注中",
        "gists": "Gists", "profile_section": "基本信息 Profile",
        "company": "公司/组织", "location": "所在地", "website": "网站",
        "joined": "加入于", "homepage": "主页", "org_badge": " · Organization",
        "no_desc": "暂无描述", "issues": "Issues", "detail_section": "详情 Details",
        "language": "语言", "license": "许可证", "default_branch": "默认分支",
        "created": "创建于", "pushed": "最近推送", "topics_section": "标签 Topics",
        "archived": "已归档", "fork": "Fork", "lang_unspecified": "未指定", "none": "无",
        "recent_commits": "Recent Commits", "commits_n": "最近 {n} 条提交 Recent Commits",
        "no_commits": "暂无提交记录", "unknown": "未知", "no_commit_msg": "(无提交信息)",
        "issue_label": "Issue", "pr_label": "Pull Request",
        "comments": "评论", "commits_label": "提交", "files": "文件",
        "author": "作者", "assignees": "指派给", "merged_at": "合并于",
        "closed_at": "关闭于", "labels_section": "标签",
        "state_merged": "已合并", "state_open": "开启", "state_closed": "已关闭",
        "comments_section": "评论",
        "lang_count": "种语言", "lang_breakdown": "Language Breakdown",
        "no_langs": "暂无语言数据", "lang_summary": "语言占比 · 共 {size} 代码",
        "lang_ratio": "语言占比:",
        "year_contrib": "年度贡献", "cur_streak": "连续天", "max_streak": "最长连续",
        "best_day": "单日最高", "heat_subtitle": "贡献热力图 · {n} contributions in the last year",
        "heat_title_empty": "Contribution Heatmap",
        "less": "少", "more": "多", "source": "来源", "no_heat": "暂无贡献数据",
        "heat_text_total": "{name} 的年度贡献: {n} 次",
        "heat_text_streak": "当前连续 {cur} 天 · 最长连续 {max} 天 · 单日最高 {best}",
        "heat_text_source": "数据来源: {src}",
    },
    "en": {
        "repos": "Repos", "followers": "Followers", "following": "Following",
        "gists": "Gists", "profile_section": "Profile",
        "company": "Company", "location": "Location", "website": "Website",
        "joined": "Joined", "homepage": "Homepage", "org_badge": " · Organization",
        "no_desc": "No description", "issues": "Issues", "detail_section": "Details",
        "language": "Language", "license": "License", "default_branch": "Default branch",
        "created": "Created", "pushed": "Last push", "topics_section": "Topics",
        "archived": "Archived", "fork": "Fork", "lang_unspecified": "n/a", "none": "None",
        "recent_commits": "Recent Commits", "commits_n": "Last {n} commits",
        "no_commits": "No commits", "unknown": "unknown", "no_commit_msg": "(no message)",
        "issue_label": "Issue", "pr_label": "Pull Request",
        "comments": "Comments", "commits_label": "Commits", "files": "Files",
        "author": "Author", "assignees": "Assignees", "merged_at": "Merged",
        "closed_at": "Closed", "labels_section": "Labels",
        "state_merged": "Merged", "state_open": "Open", "state_closed": "Closed",
        "comments_section": "Comments",
        "lang_count": "languages", "lang_breakdown": "Language Breakdown",
        "no_langs": "No language data", "lang_summary": "Languages · {size} of code",
        "lang_ratio": "Language ratio:",
        "year_contrib": "yearly", "cur_streak": "streak", "max_streak": "longest",
        "best_day": "best day", "heat_subtitle": "{n} contributions in the last year",
        "heat_title_empty": "Contribution Heatmap",
        "less": "Less", "more": "More", "source": "Source", "no_heat": "No contribution data",
        "heat_text_total": "{name}'s yearly contributions: {n}",
        "heat_text_streak": "Current streak {cur} days · longest {max} days · best day {best}",
        "heat_text_source": "Source: {src}",
    },
}

SUPPORTED = ["zh-CN", "en"]


def register(i18n) -> None:
    for lang, d in UI.items():
        try:
            i18n.register(lang, d, domain="GitHubParser")
        except Exception:
            pass


def card_labels(lang: str) -> Dict[str, str]:
    if lang in CARD:
        return CARD[lang]
    low = (lang or "").lower()
    if low.startswith("zh"):
        return CARD["zh-CN"]
    return CARD["en"]
