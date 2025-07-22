from ErisPulse import sdk
import re
import aiohttp
from typing import Optional, Dict
from urllib.parse import urlparse
from datetime import datetime

class GitHubParser:
    def __init__(self):
        self.sdk = sdk
        self.logger = sdk.logger
        self.util = sdk.util
        self.adapter = sdk.adapter
        
        # 配置正则表达式匹配GitHub URL
        self.github_regex = re.compile(
            r'https?://(?:www\.)?github\.com/([^/\s]+)/([^/\s]+)/?(?:issues/(\d+)|pull/(\d+)|tree/([^/\s]+)|blob/([^/\s]+/[^/\s]+)|$)?'
        )
        
        # 缓存已解析的仓库信息
        self.repo_cache = {}
        
        github_config = sdk.env.getConfig("GitHubParser") or {}
        self.gh_token = github_config.get("token", None)
        if not self.gh_token:
            sdk.env.setConfig("GitHubParser", {"token": ""})
            self.logger.warning("未找到GitHub API令牌，你可以在你的配置文件填入token，或者你也可以不填")
            self.gh_token = ""
        
        self.headers = {"Authorization": f"token {self.gh_token}"} if self.gh_token else {}

    async def _fetch_github_data(self, url: str) -> Optional[Dict]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        sdk.logger.debug(f"GitHub API响应: {data}")
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

    def _format_date(self, date_str: str) -> str:
        if not date_str:
            return "未知"
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y年%m月%d日")

    async def parse_github_url(self, url: str) -> Optional[Dict]:
        # 检查缓存
        if url in self.repo_cache:
            return self.repo_cache[url]
        
        try:
            match = self.github_regex.match(url)
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
            
            # 获取基础仓库信息
            repo_data = await self._fetch_github_data(result["api_url"])
            if repo_data is None:
                self.logger.warning(f"获取仓库信息失败: {result['api_url']}")
                return None
                
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
            })
            
            # 如果是issue或PR，获取额外信息
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
                    "created_at": self._format_date(issue_data.get("created_at", "")),
                    "updated_at": self._format_date(issue_data.get("updated_at", "")),
                    "closed_at": self._format_date(issue_data.get("closed_at", "")),
                })
                    
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
                    "created_at": self._format_date(pr_data.get("created_at", "")),
                    "updated_at": self._format_date(pr_data.get("updated_at", "")),
                    "closed_at": self._format_date(pr_data.get("closed_at", "")),
                    "merged_at": self._format_date(pr_data.get("merged_at", "")),
                })
            
            sdk.logger.debug(f"解析GitHub URL: {url} -> {result}")
            # 缓存结果
            self.repo_cache[url] = result
            return result
        except Exception as e:
            self.logger.error(f"解析GitHub URL时出错: {str(e)}")
            return None

    def _generate_markdown(self, data: Dict) -> str:
        if data["type"] == "repository":
            return (
                f"**[{data['full_name']}]({data['url']})**\n"
                f"{data['description'] or '无描述'}\n\n"
                f"⭐ Stars: {data['stars']} | 🍴 Forks: {data['forks']} | 👀 Watchers: {data['watchers']}\n"
                f"💻 语言: {data['language']} | 📜 许可证: {data['license']}\n"
                f"📅 创建于: {data['created_at']} | 更新于: {data['updated_at']}"
            )
        elif data["type"] == "issue":
            return (
                f"**[Issue #{data['issue_number']}]({data['url']})** - {data['title']}\n\n"
                f"🔄 状态: {data['state']} | 👤 作者: {data['user']}\n"
                f"💬 评论: {data['comments']} | 📅 创建于: {data['created_at']}"
            )
        elif data["type"] == "pull_request":
            return (
                f"**[PR #{data['pr_number']}]({data['url']})** - {data['title']}\n\n"
                f"🔄 状态: {data['state']} | 👤 作者: {data['user']}\n"
                f"💬 评论: {data['comments']} | 📝 提交: {data['commits']}\n"
                f"+{data['additions']} / -{data['deletions']} 行 | 📅 创建于: {data['created_at']}"
            )
        return ""

    def _generate_html(self, data: Dict) -> str:
        if data["type"] == "repository":
            return (
                f'<b><a href="{data["url"]}">{data["full_name"]}</a></b><br>'
                f'{data["description"] or "无描述"}<br><br>'
                f'⭐ Stars: {data["stars"]} | 🍴 Forks: {data["forks"]} | 👀 Watchers: {data["watchers"]}<br>'
                f'💻 语言: {data["language"]} | 📜 许可证: {data["license"]}<br>'
                f'📅 创建于: {data["created_at"]} | 更新于: {data["updated_at"]}'
            )
        elif data["type"] == "issue":
            return (
                f'<b><a href="{data["url"]}">Issue #{data["issue_number"]}</a></b> - {data["title"]}<br><br>'
                f'🔄 状态: {data["state"]} | 👤 作者: {data["user"]}<br>'
                f'💬 评论: {data["comments"]} | 📅 创建于: {data["created_at"]}'
            )
        elif data["type"] == "pull_request":
            return (
                f'<b><a href="{data["url"]}">PR #{data["pr_number"]}</a></b> - {data["title"]}<br><br>'
                f'🔄 状态: {data["state"]} | 👤 作者: {data["user"]}<br>'
                f'💬 评论: {data["comments"]} | 📝 提交: {data["commits"]}<br>'
                f'+{data['additions']} / -{data['deletions']} 行 | 📅 创建于: {data["created_at"]}'
            )
        return ""

    def _generate_text(self, data: Dict) -> str:
        if data["type"] == "repository":
            return (
                f"{data['full_name']} - {data['url']}\n"
                f"{data['description'] or '无描述'}\n"
                f"Stars: {data['stars']} | Forks: {data['forks']} | Watchers: {data['watchers']}\n"
                f"语言: {data['language']} | 许可证: {data['license']}\n"
                f"创建于: {data['created_at']} | 更新于: {data['updated_at']}"
            )
        elif data["type"] == "issue":
            return (
                f"Issue #{data['issue_number']} - {data['url']}\n"
                f"标题: {data['title']}\n"
                f"状态: {data['state']} | 作者: {data['user']}\n"
                f"评论: {data['comments']} | 创建于: {data['created_at']}"
            )
        elif data["type"] == "pull_request":
            return (
                f"PR #{data['pr_number']} - {data['url']}\n"
                f"标题: {data['title']}\n"
                f"状态: {data['state']} | 作者: {data['user']}\n"
                f"评论: {data['comments']} | 提交: {data['commits']}\n"
                f"新增行: {data['additions']} | 删除行: {data['deletions']}\n"
                f"创建于: {data['created_at']}"
            )
        return data["url"]

    async def send_github_info(self, platform: str, target_type: str, target_id: str, url: str):
        data = await self.parse_github_url(url)
        if not data:
            return False
            
        # 获取适配器实例
        adapter_instance = self.adapter.get(platform)
        if not adapter_instance:
            self.logger.error(f"找不到适配器: {platform}")
            return False
            
        # 尝试按优先级发送消息
        send_methods = [
            ("Markdown", self._generate_markdown),
            ("Html", self._generate_html),
            ("Text", self._generate_text)
        ]
        
        for method_name, generator in send_methods:
            if hasattr(adapter_instance.Send, method_name):
                content = generator(data)
                if not content:
                    continue
                    
                try:
                    # 使用链式调用发送消息
                    sender = adapter_instance.Send.To(target_type, target_id)
                    await getattr(sender, method_name)(content)
                    return True
                except Exception as e:
                    self.logger.error(f"使用{method_name}发送GitHub信息失败: {str(e)}")
                    continue
                    
        return False

    async def handle_message(self, data):
        if data["type"] != "message":
            return
            
        platform = data["platform"]
        detail_type = "user" if data["detail_type"] == "private" else "group"
        detail_id = data["user_id"] if detail_type == "user" else data["group_id"]
        
        # 查找消息中的GitHub URL
        urls = re.findall(r'https?://github\.com/[^\s]+', data["alt_message"])
        if not urls:
            return
            
        # 处理每个GitHub URL
        for url in urls:
            await self.send_github_info(platform, detail_type, detail_id, url)

class Main:
    def __init__(self, sdk):
        self.sdk = sdk
        self.logger = sdk.logger
        self.parser = GitHubParser()
        
        # 注册消息处理器
        @sdk.adapter.on("message")
        async def on_message(data):
            await self.parser.handle_message(data)
            
        self.logger.info("GitHub解析模块已加载")

    @staticmethod
    def should_eager_load():
        return True
    