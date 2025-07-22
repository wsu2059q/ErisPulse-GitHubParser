# ErisPulse-GitHubParser 模块文档

## 简介
`ErisPulse-GitHubParser` 是一个智能GitHub链接解析模块，能够自动识别并解析GitHub仓库、Issue和Pull Request信息，并以最佳格式展示。

## 安装

```bash
epsdk install GitHubParser
```

## 配置
安装完毕后首次加载模块时，会自动创建一个名为 `GitHubParser` 的配置文件，配置文件内容如下：

```toml
[GitHubParser]
token = "" # GitHub API令牌（可选，可提高API速率限制）
```

## 使用示例
1. 发送包含GitHub链接的消息：
   ```
   看看这个项目：https://github.com/ErisPulse/ErisPulse
   ```

2. 模块会自动回复解析结果：
   ```
   https://github.com/ErisPulse/ErisPulse
   基于Python的异步机器人开发框架
   
   ⭐ Stars: 123 | 🍴 Forks: 45 | 👀 Watchers: 67
   💻 语言: Python | 📜 许可证: MIT
   📅 创建于: 2023年5月1日 | 更新于: 2023年10月15日
   ```

## 参考链接
- 主库：https://github.com/ErisPulse/ErisPulse