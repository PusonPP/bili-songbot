# 部署手册：Bili Songbot Server

本文档按阿里云 ECS / Ubuntu 24.04.4 LTS / 4 vCPU / 16GB / 100GB SSD / 10Mbps 带宽设计。

## 1. 你必须准备的内容

### 必备文件

1. 42 个歌曲视频，建议文件名不要含奇怪控制字符；
2. 透明底转场素材：`.mov`，必须保留 Alpha；
3. `config/songs.yaml`：每首歌的歌名、代号、别名、路径、时长；
4. Bilibili 直播间号；
5. Bilibili 推流地址和推流码；
6. 推荐准备登录账号 `SESSDATA`，否则部分模式下 UID 可能为 0，单用户冷却不可靠。

### 推荐直播规格

```text
1280x720
30fps
H.264 libx264 veryfast
video bitrate 4000k
maxrate 4500k
bufsize 9000k
AAC 160k / 48kHz / stereo
GOP 60
```

## 2. 上传项目

```bash
sudo useradd -r -m -d /srv/bili-songbot -s /usr/sbin/nologin bili-songbot || true
sudo mkdir -p /srv/bili-songbot
sudo chown -R "$USER":"$USER" /srv/bili-songbot
# 解压本项目到 /srv/bili-songbot
cd /srv/bili-songbot
```

## 3. 安装依赖

```bash
bash scripts/00_install_deps_ubuntu24.sh
```

该脚本会安装：FFmpeg、Python venv、Noto CJK 字体、SQLite、logrotate、监控工具，并从 GitHub 安装 blivedm。

## 4. 上传媒体文件

```text
media/source/songs/          放 42 个歌曲视频
media/source/transition/     放 透明底转场.mov
```

例如：

```bash
ls -lh media/source/songs
ls -lh media/source/transition
```

## 5. 检测媒体

```bash
source .venv/bin/activate
python3 tools/probe_media.py media/source/songs/* media/source/transition/*
```

重点检查：

- 歌曲是否有视频流和音频流；
- 分辨率是否正常；
- 转场像素格式是否为 `argb` / `rgba` / `bgra` / `yuva*`；
- 转场编码是否为 `qtrle` / `prores 4444` / `png` 等支持 Alpha 的格式。

## 6. 填写 songs.yaml

编辑：

```bash
nano config/songs.yaml
```

每首歌必须至少包含：

```yaml
song_id: "song_001"
display_name: "命"
file_path: "media/source/songs/命.mp4"
aliases: ["命", "ming", "m", "01"]
duration: 103.0
normalized_file_path: "media/normalized/song_001_720p30.mp4"
preprocessed_file_path: "media/normalized/song_001_720p30.mp4"
transition_policy:
  enabled: true
  transition_asset: "media/transition/transition_720p30_argb.mov"
  overlap_seconds: 1.075
```

注意：

- `song_id` 必须唯一；
- `aliases` 不能冲突；
- 短代号如 `m`、`01` 只建议精确命中；
- `duration` 可先用 ffprobe 查，也可先写近似值，最终应准确。

查询时长：

```bash
ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 media/source/songs/命.mp4
```

## 7. 预转码与转场预处理

```bash
bash scripts/03_preprocess_all.sh
bash scripts/04_validate_alpha.sh
```

预转码输出：

```text
media/normalized/*.mp4
media/transition/transition_720p30_argb.mov
runtime/alpha_check.png
```

打开 `runtime/alpha_check.png` 检查。如果能看到 Alpha 形状，不是纯黑或纯白，说明透明通道有效。

## 8. 配置环境变量

```bash
cp config/.env.example config/.env
chmod 600 config/.env
nano config/.env
```

本地测试：

```env
BILI_ENABLED=true
BILI_MODE=stdin
OUTPUT_MODE=local
```

生产推流：

```env
BILI_ENABLED=true
BILI_MODE=web
BILI_ROOM_ID=你的直播间ID
BILI_SESSDATA=你的SESSDATA
OUTPUT_MODE=rtmp
RTMP_URL=rtmp://你的B站推流地址
RTMP_STREAM_KEY=你的推流码
```

严禁把真实 `SESSDATA`、推流码提交到 Git 或发给别人。

## 9. 本地链路测试

```bash
bash scripts/05_run_stdin_local_test.sh
```

在终端输入：

```text
点歌 命
点歌 ming
点歌 01
```

另开窗口查看健康状态：

```bash
curl http://127.0.0.1:8787/healthz | jq
```

检查输出文件：

```bash
ls -lh runtime/local_test.flv
ffprobe runtime/local_test.flv
```

## 10. 生产推流测试

确认 `.env`：

```env
OUTPUT_MODE=rtmp
BILI_MODE=web
```

手动启动：

```bash
source .venv/bin/activate
python -m bili_songbot
```

确认：

- Bilibili 后台显示推流在线；
- 弹幕点歌能入队；
- 左侧 UI 会显示队列；
- 转场没有黑底；
- CPU 长时间不要持续 100%。

## 11. 安装 systemd

```bash
sudo chown -R bili-songbot:bili-songbot /srv/bili-songbot
sudo chmod 600 /srv/bili-songbot/config/.env
sudo cp systemd/bili-songbot.service /etc/systemd/system/bili-songbot.service
sudo cp systemd/bili-songbot-logrotate /etc/logrotate.d/bili-songbot
sudo systemctl daemon-reload
sudo systemctl enable bili-songbot
sudo systemctl start bili-songbot
sudo systemctl status bili-songbot
```

查看日志：

```bash
journalctl -u bili-songbot -f
sudo tail -f /srv/bili-songbot/logs/app.log
```

## 12. 防火墙

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw enable
```

健康接口默认只绑定 `127.0.0.1`。不要直接暴露公网。

## 13. 正式直播前检查清单

- [ ] 42 个视频均已上传；
- [ ] `songs.yaml` 中 42 首均 enabled；
- [ ] 所有别名无冲突；
- [ ] 所有视频已预转码；
- [ ] 转场已预处理；
- [ ] `alpha_check.png` 验证通过；
- [ ] `.env` 已填写真实直播间和推流信息；
- [ ] `OUTPUT_MODE=rtmp`；
- [ ] `BILI_MODE=web`；
- [ ] `BILI_SESSDATA` 有效；
- [ ] 手动运行测试通过；
- [ ] systemd 启动通过；
- [ ] 日志轮转已安装；
- [ ] UFW 未暴露管理端口；
- [ ] 阿里云安全组只开放 SSH 和必要端口；
- [ ] 连续 2 小时测试 CPU 不长期满载；
- [ ] 连续 24 小时测试无异常退出。

## 14. 常见问题

### 1. 转场变黑底

原因通常是转场被转成 H.264 / yuv420p，Alpha 丢失。重新运行：

```bash
bash scripts/03_preprocess_all.sh
bash scripts/04_validate_alpha.sh
```

确认 `media/transition/transition_720p30_argb.mov` 是 `qtrle + argb`。

### 2. 弹幕 UID 都是 0

填写有效 `BILI_SESSDATA`。没有登录态时，Web 模式可能无法可靠获取真实用户标识，单用户冷却会受影响。

### 3. CPU 太高

按顺序降级：

1. `X264_PRESET=superfast`；
2. `VIDEO_BITRATE=3500k`；
3. `CHUNK_SECONDS=12`；
4. 减少 UI 显示行数；
5. 关闭转场测试；
6. 升级到 8 vCPU。

### 4. Bilibili 推流断开

检查：

- RTMP 地址和推流码是否过期；
- ECS 出口是否稳定；
- 视频码率是否超过带宽；
- systemd 是否自动重启；
- 日志中是否有 `BrokenPipe` 或 RTMP 错误。
