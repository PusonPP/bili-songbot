# 实现说明与已验证内容

## 已实现模块

- 弹幕监听：`bili_songbot/danmaku.py`
  - `stdin` 测试模式：不用连 B 站即可验证点歌逻辑；
  - `web` 生产模式：使用 blivedm 的 `BLiveClient` 和 `BaseHandler` 监听弹幕。
- 点歌匹配：`bili_songbot/matcher.py`
  - 精确匹配；
  - 短代号不模糊；
  - 长别名 rapidfuzz 模糊匹配；
  - 别名冲突启动时报错。
- 队列管理：`bili_songbot/queue_manager.py`
  - 队列上限 10；
  - 单用户 120 秒冷却；
  - 重复点歌拒绝；
  - 随机播放避免最近重复。
- 持久化：`bili_songbot/storage.py`
  - SQLite WAL；
  - 队列、冷却、播放历史、运行状态、事件日志。
- UI 叠加：`bili_songbot/ui_layer.py`
  - 生成透明 PNG；
  - 左侧当前播放、点歌队列、随机预告；
  - 右上角固定提示文字。
- FFmpeg 推流：`bili_songbot/pusher.py`
  - FIFO 接收 MPEG-TS；
  - 推到本地 FLV 或 RTMP。
- FFmpeg 渲染：`bili_songbot/renderer.py`
  - 歌曲片段 overlay UI；
  - 上一首尾部 + 下一首头部 + 透明转场 overlay；
  - 输出 H.264/AAC MPEG-TS。
- 健康检查：`bili_songbot/health.py`
  - `/healthz` 返回队列、推流、弹幕、CPU、内存、磁盘等状态。
- 部署：`systemd/bili-songbot.service`、`systemd/bili-songbot-logrotate`。

## 已在当前环境验证

- Python 语法编译通过；
- 样例视频可预转码为 720p30 H.264/AAC；
- 样例透明转场可预处理为 720p30 QTRLE/ARGB；
- UI PNG 可正常生成；
- 本地 FLV 输出链路已运行 20 秒并生成 `runtime/local_test.flv`；
- 透明转场 filter_complex 命令已用样例文件测试通过。

## 重要限制

当前实现为了降低 4 vCPU 服务器压力，采用“分段渲染 + FIFO 推流”的方式。分段边界处 FFmpeg 可能输出 timestamp discontinuity / Non-monotonic DTS 日志；本地 FLV 测试可生成可播放文件。生产推 Bilibili 前必须做至少 2 小时小流量测试。如果平台对分段时间戳非常敏感，可以：

1. 把 `CHUNK_SECONDS` 调大到 60 或更高，减少分段边界；
2. 临时关闭歌曲中途 UI 刷新，只在歌曲切换时刷新；
3. 如仍不稳定，升级为 GStreamer 单长管线或 FFmpeg re-encode pusher 模式。

## 生产推荐参数

```env
OUTPUT_WIDTH=1280
OUTPUT_HEIGHT=720
OUTPUT_FPS=30
VIDEO_BITRATE=4000k
VIDEO_MAXRATE=4500k
VIDEO_BUFSIZE=9000k
AUDIO_BITRATE=160k
X264_PRESET=veryfast
CHUNK_SECONDS=20
```
