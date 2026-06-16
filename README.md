# Bili Songbot Server

这是一个面向阿里云 ECS / Ubuntu 24.04 无头服务器的 Bilibili 直播点歌台项目骨架，核心链路为：

- Python：弹幕监听、点歌匹配、队列限流、状态持久化、播放状态机、健康检查；
- FFmpeg：720p30 视频合成、透明转场叠加、PNG UI 叠加、H.264/AAC 编码、RTMP/本地 FLV 输出；
- SQLite：队列、冷却、播放历史和运行状态持久化；
- systemd：24 小时守护、自启动、异常重启。

> 当前包不是伪代码，包含可运行代码。你需要填充 `config/.env`、补齐 `config/songs.yaml`，并上传 42 个视频和转场素材。

## 关键限制

当前推荐输出为 1280x720 / 30fps / H.264 / AAC / 4000k。4 vCPU + 10Mbps ECS 不建议直接 1080p 实时合成推流。

## 本地/服务器快速测试

```bash
cd /srv/bili-songbot
bash scripts/00_install_deps_ubuntu24.sh
bash scripts/01_prepare_dirs.sh
cp config/.env.example config/.env
# 把样例视频放到 media/source/songs/命.mp4
# 把透明转场放到 media/source/transition/透明底转场.mov
bash scripts/03_preprocess_all.sh
bash scripts/04_validate_alpha.sh
bash scripts/05_run_stdin_local_test.sh
```

运行后，在终端输入：

```text
命
点歌 ming
点歌 01
```

默认输出到：

```text
runtime/local_test.flv
```

## 生产启动

1. `config/.env` 设置 `OUTPUT_MODE=rtmp`；
2. 填写 `RTMP_URL` 和 `RTMP_STREAM_KEY`；
3. 设置 `BILI_ENABLED=true`、`BILI_MODE=web`、`BILI_ROOM_ID`、`BILI_SESSDATA`；
4. 运行预处理；
5. 安装 systemd 服务。

详见 `docs/DEPLOYMENT.md`。
