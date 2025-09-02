# 雨课堂自动学习脚本

这是一个用于自动完成 [荷塘雨课堂](https://pro.yuketang.cn/) 视频观看的 Python 脚本。

## ✨ 功能

- 自动获取指定课堂下的所有视频。
- 模拟视频播放，通过发送心跳包来更新观看进度。
- 支持多视频并发处理，以提高效率。
- 支持手动配置 Cookie 或自动从 Firefox 浏览器获取 Cookie。
- 使用 `tqdm` 库显示每个视频的观看进度条。

## 🚀 安装与准备

1.  **克隆项目代码**
    ```bash
    git clone https://github.com/hotwords123/yuketang-auto-study.git
    cd yuketang-auto-study
    ```

2.  **安装依赖**
    你可以使用 [`uv`](https://docs.astral.sh/uv/getting-started/installation/) 来安装项目所需的依赖包。

    ```bash
    # 创建虚拟环境，并安装所有依赖
    uv sync
    ```

3.  **创建并配置 `config.json`**
    在项目根目录下创建一个名为 `config.json` 的文件。脚本将从此文件读取运行所需的配置。

    文件内容模板如下：
    ```json
    {
      "cookie": "YOUR_COOKIE_HERE",
      "user_agent": "YOUR_BROWSER_USER_AGENT",
      "classroom_id": 12345678
    }
    ```

    **如何获取配置信息:**
    - `classroom_id`: 在浏览器中进入你想要学习的雨课堂课程，地址栏 URL 的末尾会有一串数字，即为 `classroom_id`。例如，`https://pro.yuketang.cn/v2/web/studentLog/12345678` 中的 `12345678`。
    - `user_agent`: 你浏览器的 User-Agent 字符串。可以在浏览器开发者工具的控制台中输入 `navigator.userAgent` 来获取。
    - `cookie`:
        - **方法一 (自动获取 - 推荐)**: 如果你使用 **Firefox** 浏览器并已登录雨课堂，可以将此字段的值直接设置为 `"FIREFOX"` (包含双引号)。脚本会自动加载所需的 Cookie。
        - **方法二 (手动复制)**:
            1. 登录雨课堂。
            2. 按 `F12` 打开开发者工具，切换到“网络”（Network）标签。
            3. 刷新页面，在网络请求列表中找到任意一个对 `pro.yuketang.cn` 的请求。
            4. 在“请求标头”（Request Headers）中找到 `Cookie` 字段，复制其完整的字符串值。这个字符串应当形如 `key1=value1; key2=value2; ...`。
            5. 将复制的 Cookie 粘贴到 `config.json` 文件中。

## 🏃‍♂️ 运行脚本

完成配置后，在项目根目录下执行以下命令：

```bash
uv run main.py
```

脚本启动后，将自动开始处理视频。

## ⚠️ 免责声明

本项目仅供学习和技术交流使用。请勿用于任何商业或非法用途。因使用本脚本而导致的任何后果，由使用者自行承担。
