# SAFETY_AND_SECRETS.md

## Never expose

```text
RTMP_STREAM_KEY
BILI_STREAM_KEY
key=...
streamname=...
biliup-cookies.json
SESSDATA
bili_jct
DedeUserID
full RTMP push URL
```

## Safe masking commands

For stream env:

```bash
sed -E 's/(key=)[^&"]+/\1***MASKED***/g; s/(streamname=)[^&"]+/\1***MASKED***/g' \
  /opt/bili-live-keeper/runtime/stream.env
```

For logs:

```bash
grep -Ei "RTMP|stream|key|Broken pipe|End of file|Conversion failed" /srv/bili-songbot/logs/systemd.log \
  | sed -E 's/(key=)[^&"]+/\1***MASKED***/g; s/(streamname=)[^&"]+/\1***MASKED***/g'
```

## Recommended permissions

```bash
chmod 600 /srv/bili-songbot/config/.env
chmod 600 /srv/bili-songbot/logs/systemd.log
chmod 600 /opt/bili-live-keeper/runtime/stream.env
chmod 600 /var/lib/bili-live-keeper/biliup-cookies.json
```

## If a push key is leaked

1. Do not repost it.
2. Continue current stream only if interruption is unacceptable.
3. At the next safe maintenance window, stop live and let keeper open a fresh live session.
4. Truncate old logs.

```bash
truncate -s 0 /srv/bili-songbot/logs/systemd.log
```

## FFmpeg log risk

If FFmpeg is run with `-loglevel info`, it may print the full RTMP URL including key.

Preferred long-term change:

```text
-loglevel warning
```

Change this only during a controlled restart window.
