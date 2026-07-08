# Codex+

语言：中文 | [English](README.en.md)

Codex+ 是一个 Windows 桌面端 + 手机端的 Codex 会话管理工具。它可以集中管理本机 Codex CLI 会话，在电脑上启动、查看、继续和清理会话，也可以通过手机浏览器或 Android APP 连接电脑上的 portal，随时查看最近会话、继续对话、停止回复或新建任务。

适合这些场景：

- 电脑上长期运行 Codex，会话很多，需要快速搜索、打开和继续。
- 想在手机上查看电脑里的 Codex 会话进度。
- 想用手机发消息、上传图片、停止回复或创建新会话。
- 需要在多个 Codex 账号槽位之间切换。
- 需要在 Codex Auth、内置 Token Pool、OpenAI-Compatible API 之间切换后端。

## 界面预览

截图文件保存在仓库中：

| 页面 | 截图 |
| --- | --- |
| 手机端首页 | [assets/mobile-home.jpg](assets/mobile-home.jpg) |
| 桌面端概览 | [assets/ui-overview.png](assets/ui-overview.png) |
| 账号与后端配置 | [assets/account-backend-redacted.png](assets/account-backend-redacted.png) |

## 功能

- 桌面端会话列表：查看时间、模型、目录、最后消息和会话详情。
- 会话操作：刷新、打开终端、打开目录、打开文件、删除会话。
- 启动选项：模型、审批模式、沙盒模式、搜索、管理员模式。
- 账号槽位：绑定当前账号、切换账号、重命名、备注、删除。
- 后端模式：
  - `Codex Auth`：使用本机 Codex CLI 登录状态。
  - `Built-In Token Pool`：通过本地 token pool 代理请求。
  - `OpenAI-Compatible API`：配置 Base URL、API Key、模型、协议和代理策略。
- OpenAI-Compatible 预设：支持保存、刷新模型、应用、删除。
- 图片输入：手机端和兼容 API 模式支持图片作为输入。
- 手机 portal：最近会话、全部会话、新建会话、聊天详情、停止回复。
- Android APP：可直接安装 debug APK，也可以自行构建。
- 远程辅助：可选通过 SSH/Tailscale 重启配置好的电脑。

## 环境要求

桌面端和手机 portal：

- Windows 10/11
- Python 3.11 或更新版本
- Codex CLI，并且 `codex` 命令在 `PATH` 中可用
- Python `requests[socks]`
- Tkinter，官方 Windows Python 通常自带

Android APP 构建：

- JDK 17
- Android SDK
- Android SDK Platform 36
- Android Gradle Plugin 8.13.2
- Gradle 9.0.0 或更新的兼容版本

Android APP 运行：

- Android 8.0 或更新版本
- 手机能访问电脑上的 portal 地址，例如同一局域网或 Tailscale 网络

## 安装依赖

```powershell
py -3 -m pip install -r requirements.txt
```

如果要把桌面端打包成 Windows EXE，再安装构建依赖：

```powershell
py -3 -m pip install -r requirements-build.txt
```

确认 Codex CLI 可用：

```powershell
codex --version
codex login
```

## 启动桌面端

```bat
run.bat
```

桌面端用于管理会话、账号槽位、后端模式和 OpenAI-Compatible API 预设。

## 启动手机端

```bat
run-mobile.bat
```

启动后终端会打印 portal 地址，手机浏览器打开该地址即可使用。Android APP 也连接同一个 portal 地址。

## 手机 APP

仓库里保留了一个可直接安装的 debug APK：

```text
app/CodexPlus-debug.apk
```

Android 源码在：

```text
android-app/
```

构建 debug APK：

```powershell
cd android-app
$env:ANDROID_HOME='你的 Android SDK 路径'
$env:ANDROID_SDK_ROOT='你的 Android SDK 路径'
gradle :app:assembleDebug --console=plain
```

构建输出：

```text
android-app\app\build\outputs\apk\debug\app-debug.apk
```

## OpenAI-Compatible API

桌面端账号管理窗口里可以配置 OpenAI-Compatible API 预设。每个预设支持：

- Preset name
- Base URL
- API Key
- Model
- Proxy mode：`direct`、`proxy`、`auto`
- Protocol：`responses` 或 `chat_completions`
- 是否禁用图片生成

应用预设后，新启动的 Codex 会话会按该预设请求对应后端。

## 项目结构

```text
.
├─ app.py                         # Windows 桌面管理器
├─ mobile_portal.py               # 手机 portal 服务
├─ token_pool_proxy.py            # Built-In Token Pool 本地代理
├─ custom_provider_proxy.py       # OpenAI-Compatible 协议适配代理
├─ token_pool_settings.py         # 后端模式和预设读写
├─ auth_slots.py                  # Codex 账号槽位管理
├─ controlled_browser.py          # 受控浏览器辅助逻辑
├─ process_singleton.py           # 启动时清理同项目旧进程
├─ remote_ssh.py                  # 远程重启 SSH 逻辑
├─ session_context_repair.py      # 会话上下文修复辅助
├─ run.bat                        # 启动桌面端
├─ run-mobile.bat                 # 启动手机 portal
├─ requirements.txt               # 运行依赖
├─ requirements-build.txt         # 打包依赖
├─ app/
│  └─ CodexPlus-debug.apk         # Android debug 安装包
├─ android-app/                   # Android APP 源码
├─ assets/                        # README 展示截图
└─ scripts/
   └─ ensure-boot-network.ps1     # 启动网络辅助脚本
```

## Windows EXE 打包

项目包含 PyInstaller spec：

```powershell
pyinstaller codex-session-manager.spec
```

输出目录：

```text
dist\
```

## 发布方式

当前项目没有使用 GitHub Releases。安装包直接保存在仓库：

```text
app/CodexPlus-debug.apk
```

## 社区

项目欢迎来自 [LINUX DO](https://linux.do) 社区的建议和反馈。
