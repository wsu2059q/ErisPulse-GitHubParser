from typing import Any, Dict, List

from .I18n import card_labels


def _fc(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 10_000:
        return f"{n / 10_000:.1f}w"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _trunc(text: str, max_len: int = 120) -> str:
    text = "" if text is None else str(text).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)] + "…"


def render_text(kind: str, owner: str, repo: str, number, data: Any, lang: str = "zh-CN") -> str:
    L = card_labels(lang)
    if kind == "user":
        return _user(data, L)
    if kind == "repo":
        return _repo(data, L)
    if kind in ("issue", "pr"):
        return _issue_pr(kind, owner, repo, data, L)
    if kind == "commits":
        return _commits(owner, repo, data, L)
    if kind == "langs":
        return _langs(owner, repo, data, L)
    if kind == "heat":
        return _heat(owner, data, L)
    return str(data)


def _user(d: Dict[str, Any], L) -> str:
    lines = [f"{d.get('name', '')} (@{d.get('login', '')})"]
    if d.get("bio"):
        lines.append(d["bio"])
    lines.append(
        f"{L['repos']} {_fc(d.get('public_repos', 0))} · {L['followers']} {_fc(d.get('followers', 0))} · "
        f"{L['following']} {_fc(d.get('following', 0))} · {L['gists']} {_fc(d.get('public_gists', 0))}"
    )
    extras = []
    if d.get("company"):
        extras.append(f"{L['company']}: {d['company']}")
    if d.get("location"):
        extras.append(f"{L['location']}: {d['location']}")
    if d.get("blog"):
        extras.append(f"{L['website']}: {d['blog']}")
    extras.append(f"{L['joined']}: {d.get('created_at', L['unknown'])}")
    lines.append(" | ".join(extras))
    if d.get("html_url"):
        lines.append(d["html_url"])
    return "\n".join(lines)


def _repo(d: Dict[str, Any], L) -> str:
    lines = [d.get("full_name", "")]
    lines.append(d.get("description") or L["no_desc"])
    lines.append(
        f"★ Stars {_fc(d.get('stars', 0))} · ⑂ Forks {_fc(d.get('forks', 0))} · "
        f"Watchers {_fc(d.get('watchers', 0))} · {L['issues']} {_fc(d.get('open_issues', 0))}"
    )
    info = [f"{L['language']}: {d.get('language', L['lang_unspecified'])}",
            f"{L['license']}: {d.get('license', L['none'])}"]
    if d.get("homepage"):
        info.append(f"{L['homepage']}: {d['homepage']}")
    info.append(f"{L['pushed']}: {d.get('pushed_at', L['unknown'])}")
    lines.append(" | ".join(info))
    if d.get("topics"):
        lines.append(", ".join(d["topics"][:8]))
    if d.get("html_url"):
        lines.append(d["html_url"])
    return "\n".join(lines)


def _issue_pr(kind: str, owner: str, repo: str, d: Dict[str, Any], L) -> str:
    tag = L["pr_label"] if kind == "pr" else L["issue_label"]
    if d.get("merged_at"):
        state = L["state_merged"]
    elif d.get("state") == "open":
        state = L["state_open"]
    else:
        state = L["state_closed"]
    lines = [f"{owner}/{repo} #{d.get('number', '?')} [{state}] {d.get('title', '')}"]
    body = f"{L['author']}: {d.get('user', '')} · {L['comments']}: {_fc(d.get('comments', 0))}"
    if kind == "pr":
        body += (f" · {L['commits_label']}: {_fc(d.get('commits', 0))}"
                 f" · +{_fc(d.get('additions', 0))}/-{_fc(d.get('deletions', 0))}"
                 f" · {_fc(d.get('changed_files', 0))} {L['files']}")
    lines.append(body)
    if d.get("labels"):
        lines.append(", ".join(d["labels"][:6]))
    comments = d.get("comments_list") or []
    for c in comments[:3]:
        cbody = _trunc(c.get("body", ""))
        if cbody:
            lines.append(f"  {c.get('user', '')}: {cbody}")
    if d.get("html_url"):
        lines.append(d["html_url"])
    return "\n".join(lines)


def _commits(owner: str, repo: str, commits: List[Dict[str, Any]], L) -> str:
    if not commits:
        return f"{owner}/{repo}: {L['no_commits']}"
    lines = [f"{owner}/{repo} {L['commits_n'].format(n=len(commits))}"]
    for c in commits:
        lines.append(f"  [{c.get('sha', '')}] {c.get('message', '')} — {c.get('author', '')} ({c.get('date', '')})")
    return "\n".join(lines)


def _langs(owner: str, repo: str, langs: Dict[str, int], L) -> str:
    total = sum(langs.values()) or 1
    ranked = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)
    lines = [f"{owner}/{repo} {L['lang_ratio']}"]
    for name, val in ranked[:8]:
        lines.append(f"  {name}: {val / total * 100:.1f}%")
    return "\n".join(lines)


def _heat(username: str, contrib: Dict[str, Any], L) -> str:
    streak = _streak(contrib.get("days", []))
    best = max((d.get("count", 0) for d in contrib.get("days", []) if d), default=0)
    lines = [
        L["heat_text_total"].format(name=username, n=contrib.get("total", 0)),
        L["heat_text_streak"].format(cur=streak["current"], max=streak["longest"], best=best),
        L["heat_text_source"].format(src=contrib.get("source", "unknown")),
        f"https://github.com/{username}",
    ]
    return "\n".join(lines)


def _streak(days):
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
    longest = run = 0
    for d in valid:
        if d.get("count", 0) > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return {"current": current, "longest": longest}
