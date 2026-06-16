# bili-live-keeper

`bili-live-keeper` 是一个用于 Linux 服务器 headless 长期运行的 Bilibili 直播后台守护工具。它使用 `biliup` 生成的 cookies 作为认证来源，通过公开直播间接口、后台 HTTP 和 Playwright Chromium 逐级判断直播状态；当连续确认未开播后，进入 Bilibili 开播后台，确认分区为 `电台 · 聊天电台`，再点击 `开始直播`。

它不会点击 `关闭直播`，不会使用固定鼠标坐标，不会绕过验证码/短信/人脸/二次验证，也不会在日志里输出 cookies、直播码或推流密钥。

## 安装

在源码目录执行：

```bash
cd /home/ubuntu/codex-server-admin/bili-live-keeper
bash scripts/install.sh
```

安装脚本会执行这些操作：

- 安装 Python、venv、pip、Playwright Chromium 所需依赖。
- 创建专用系统用户 `bili-live-keeper`。
- 复制项目到 `/opt/bili-live-keeper`。
- 创建 `/var/lib/bili-live-keeper`、`/var/log/bili-live-keeper`。
- 创建 `/opt/bili-live-keeper/.env` 模板，不覆盖已有真实 `.env`。
- 安装 `/etc/systemd/system/bili-live-keeper.service`。
- 执行 `systemctl daemon-reload`，但不会在 cookies 配置完成前自动启动服务。

## biliup 登录

安装后运行：

```bash
sudo /opt/bili-live-keeper/scripts/login_biliup.sh
```

脚本会优先使用系统已有且支持 `login` 子命令的 `biliup-rs`。如果不存在，会下载并校验官方 release，把独立二进制安装到 `/opt/bili-live-keeper/bin/biliup`，不污染系统 Python。登录命令使用：

```bash
biliup -u /var/lib/bili-live-keeper/biliup-cookies.json login
```

根据 `biliup` 提示扫码、短信或浏览器确认。cookies 生成后权限会被设置为 `600`，所有者为 `bili-live-keeper`。脚本会提示是否把路径写入 `/opt/bili-live-keeper/.env`。

## 配置

编辑：

```bash
sudo nano /opt/bili-live-keeper/.env
```

关键配置：

```env
BILI_ROOM_ID=23559761
BILI_LIVE_CENTER_URL=https://link.bilibili.com/p/center/index?spm_id_from=333.1387.0.0#/my-room/start-live
BILIUP_COOKIE_FILE=/var/lib/bili-live-keeper/biliup-cookies.json
CHECK_INTERVAL_SECONDS=30
STOP_CONFIRM_TIMES=2
START_COOLDOWN_SECONDS=300
MAX_START_ATTEMPTS_PER_HOUR=3
HEADLESS=true
DRY_RUN=false
LIVE_AREA_PARENT=电台
LIVE_AREA_CHILD=聊天电台
RUNTIME_STREAM_ENV=/opt/bili-live-keeper/runtime/stream.env
SAVE_FAILURE_SCREENSHOT=false
LOG_LEVEL=INFO
```

`BILI_ROOM_ID` 可选，但建议填写；它用于先走公开直播间状态接口。`BILIUP_COOKIE_FILE` 是 `start-once` 和 `daemon` 必需配置。`.env` 不要提交到 git。

## 验证

打印脱敏配置：

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env HOME=/var/lib/bili-live-keeper XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli print-config --redacted
```

单次状态检查：

```bash
sudo /opt/bili-live-keeper/scripts/run_once_check.sh
```

单次 dry-run 开播流程，不点击 `开始直播`：

```bash
sudo /opt/bili-live-keeper/scripts/run_once_start.sh --dry-run
```

单次真实开播：

```bash
sudo /opt/bili-live-keeper/scripts/run_once_start.sh
```

也可以直接执行：

```bash
cd /opt/bili-live-keeper
sudo -u bili-live-keeper env HOME=/var/lib/bili-live-keeper XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli check

sudo -u bili-live-keeper env HOME=/var/lib/bili-live-keeper XDG_CACHE_HOME=/var/lib/bili-live-keeper/.cache \
  /opt/bili-live-keeper/.venv/bin/python -m bili_live_keeper.cli start-once --dry-run
```

## 启动守护服务

dry-run 正常后再启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable bili-live-keeper
sudo systemctl start bili-live-keeper
sudo systemctl status bili-live-keeper --no-pager
```

查看日志：

```bash
journalctl -u bili-live-keeper -f
```

或：

```bash
sudo /opt/bili-live-keeper/scripts/tail_logs.sh
```

## CLI

```bash
python -m bili_live_keeper.cli check
python -m bili_live_keeper.cli start-once
python -m bili_live_keeper.cli start-once --dry-run
python -m bili_live_keeper.cli daemon
python -m bili_live_keeper.cli print-config --redacted
```

在 `/opt` 部署后推荐使用 `.venv/bin/python` 并以 `bili-live-keeper` 用户执行。

## 状态判断

输出格式：

```json
{
  "live": true,
  "source": "api",
  "reason": "room_live_status_1",
  "checked_at": "2026-06-11T00:00:00+00:00",
  "confidence": "high"
}
```

规则：

- 检测到 `关闭直播`：认为已开播，高置信度。
- 检测到 `服务器地址` 且检测到 `直播码`、`推流密钥` 或 `串流密钥`：认为已开播，高置信度。
- 检测到 `开始直播`：认为未开播，高置信度。
- API 明确返回直播中：认为已开播。
- 状态未知时不会自动点击开播。

## 分区

默认分区：

```env
LIVE_AREA_PARENT=电台
LIVE_AREA_CHILD=聊天电台
```

如需更新分区，修改 `.env` 后执行 dry-run：

```bash
sudo systemctl restart bili-live-keeper
sudo /opt/bili-live-keeper/scripts/run_once_start.sh --dry-run
```

## FFmpeg/推流服务接入

开播成功并提取到推流信息后，会写入：

```bash
/opt/bili-live-keeper/runtime/stream.env
```

权限为 `600`，格式：

```env
BILI_RTMP_URL="rtmp://live-push.bilivideo.com/live-bvc/..."
BILI_STREAM_KEY="?streamname=...&key=..."
BILI_STREAM_UPDATED_AT="..."
```

另一个 systemd 推流服务可以使用：

```ini
EnvironmentFile=/opt/bili-live-keeper/runtime/stream.env
ExecStart=/usr/bin/ffmpeg ... -f flv ${BILI_RTMP_URL}/${BILI_STREAM_KEY}
```

如果你的推流命令需要开播后自动重启，设置：

```env
ON_STARTED_HOOK=/usr/bin/systemctl restart your-ffmpeg.service
```

hook 输出会脱敏；hook 命令本身不要包含明文密钥。

如果没有外部 OBS/FFmpeg 推流器，可以启用内置保活推流服务。它会读取
`/opt/bili-live-keeper/runtime/stream.env`，推一个黑色视频和静音音频，避免 Bilibili
因为没有推流而把直播间重新判为未开播：

```env
PUSH_KEEPALIVE_ENABLED=true
PUSH_KEEPALIVE_FFMPEG=/usr/bin/ffmpeg
PUSH_KEEPALIVE_VIDEO_SIZE=1280x720
PUSH_KEEPALIVE_FPS=15
PUSH_KEEPALIVE_VIDEO_BITRATE=800k
PUSH_KEEPALIVE_AUDIO_BITRATE=96k
```

启用服务：

```bash
sudo systemctl enable bili-live-keeper-push
sudo systemctl start bili-live-keeper-push
```

## 重新登录 cookies

cookies 过期、后台提示未登录、或 Bilibili 风控要求重新确认时：

```bash
sudo systemctl stop bili-live-keeper
sudo /opt/bili-live-keeper/scripts/login_biliup.sh
sudo /opt/bili-live-keeper/scripts/run_once_check.sh
sudo systemctl start bili-live-keeper
```

程序每次检查前都会读取 cookies 文件 mtime。如果 `biliup` 更新了同一路径，守护进程会自动重新加载。

## 回滚和卸载

停止并禁用服务：

```bash
sudo systemctl stop bili-live-keeper
sudo systemctl disable bili-live-keeper
```

移除 systemd 单元：

```bash
sudo rm -f /etc/systemd/system/bili-live-keeper.service
sudo systemctl daemon-reload
```

如需删除部署文件，先确认已备份 cookies 和 `.env`，再只删除本项目目录：

```bash
sudo rm -rf /opt/bili-live-keeper
sudo rm -rf /var/log/bili-live-keeper
```

是否删除 `/var/lib/bili-live-keeper` 取决于你是否还要保留 cookies：

```bash
sudo rm -rf /var/lib/bili-live-keeper
```

## 常见故障

`cookies 过期`：重新执行 `login_biliup.sh`，确认 `.env` 中 `BILIUP_COOKIE_FILE` 指向新文件。

`页面提示未登录`：说明 cookies 对后台不可用。停止服务，重新登录，不要让守护进程反复失败。

`出现验证码/二次验证/短信/人脸验证`：程序会停止自动操作并记录错误。必须人工完成，项目不会绕过验证。

`找不到“开始直播”`：Bilibili 页面结构可能变化，或账号没有开播权限。先运行 `start-once --dry-run`，检查日志中的当前 URL 和页面摘要。

`找不到“电台 · 聊天电台”`：确认账号可选择该分区，或更新 `LIVE_AREA_PARENT`、`LIVE_AREA_CHILD`。程序找不到目标分区时不会开播。

`开播成功但推流码提取失败`：直播状态可能已经成功，但页面字段名称变化。检查后台页面是否显示 `服务器地址` 和 `串流密钥`，必要时临时手动复制。

`Playwright Chromium 启动失败`：确认安装脚本执行过；在 aarch64 或特殊系统上，可设置 `.env` 里的 `CHROMIUM_EXECUTABLE=/usr/bin/chromium-browser` 或其他可执行路径。

`systemd 反复重启`：查看 `journalctl -u bili-live-keeper -n 200 --no-pager`，重点检查配置缺失、cookies 权限、Chromium 启动失败。

## 安全注意事项

- 不要提交 `.env`、cookies、`runtime/stream.env`、日志截图。
- 默认不保存失败截图，因为页面可能包含推流密钥。
- 如需 `SAVE_FAILURE_SCREENSHOT=true`，截图会设置为 `600`，但仍应视为敏感文件。
- 日志会脱敏 `SESSDATA`、`bili_jct`、`DedeUserID`、`streamname`、`key` 等字段。
- 只用于你自己拥有或管理的 Bilibili 账号/直播间。
- 该项目不会绕过 Bilibili 的验证码、人脸、短信或二次验证。
