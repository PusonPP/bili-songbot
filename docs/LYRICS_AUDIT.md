# 歌词导入、修订与验收

更新日期：2026-11-10（America/Vancouver，PST）。部署时间及健康检查见
`docs/codex/OPERATION_LOG.md`。

## 当前结论

用户提供的 ALL.zip 已补齐原始工程素材。之前“服务器未找到歌词源文件”的结论
只适用于附件提供前的搜索，现已解除这一素材阻塞，不再要求用户重新寻找这些文件。

- 42 首原始音频、42 张封面、26 个 LRC、16 个 TXT、42 份对应中文译文。
- 逐首对照了全部原文与译文，建立 66 项有原文匹配保护的修订；其中 61 项用于
  本轮新字幕，其余 5 项保存在待核对源文中，不能宣称已经出现在直播画面。
- 26 首沿用附件 LRC 的起始时间；6 首 TXT 引入同版参考时间轴，共 32 首、1487 个
  双语显示段。未对 TXT 按时长、字数均分，也没有推算未匹配的逐字时间。
- 另外 10 首保留旧播放视频。新素材不是“全曲歌词最终验收通过”的证明。
- 程序校验、显示边界、分段时钟与转场回归可自动验证；**所有歌曲逐句听校尚未完成**。
  LRC 自带时间轴以及公开参考 LRC 均不是精确演唱起止点的权威证明。

## 修复的生成和播放问题

原附件脚本只作参考，没有执行其中任何 Python/PowerShell 程序。

1. 原 LRC 生成器删除空时间标签，并把短句强制延长至至少 1.2 秒，造成间奏残留与重叠。
   新导入器保留清屏标签，不延长短句；时间重复、越界、缺译、额外译文均拒绝导入。
2. 相同原文不能总取第一份译文。现在按源文件中每次出现的次序绑定中文译文，
   再展开多时间标签，排序不会打乱原文/译文关系。
3. 时间换算使用 pylrc / pysubs2，覆盖毫秒、offset、跨分钟进位和 ASS 精度。
   本项目明确正 offset 表示延后，与 pylrc 一致；出现负越界时拒绝静默截断。
4. 字幕与底片分离。新的 clean.mp4 使用用户原始音频和封面，没有旧烧录字幕。
   底片 2 fps，在线渲染先转为 30 fps，再按歌曲绝对时间叠加 ASS；音频驱动频谱保留。
   分段 seek 后先恢复绝对时钟，字幕渲染后再归零，避免每 20 秒重播开头的歌词。
5. 转场仍显示原动画，但只预览下一首静止首帧，不再静音消耗并跳过约 0.55 秒的歌头。
   前一首播放到音源结束；下一首从 0 秒开始，不再按固定半转场扣除前一首尾部。
6. 新素材歌长按原始音频记录，不能统一把字幕平移 2.8 秒。旧视频多数是尾部多 2.8 秒，
   并非音频起点多 2.8 秒。song_030 的文件头标称 316.507 秒，实际解码仅 312.947 秒；
   后者与旧视频多约 2.8 秒的模式吻合。保留该异常源文件，未伪造缺失尾部或放宽构建校验。

## 译名与文本修订依据

- To My Dearest 保留英文；Never ending saga、We are FranChouChou! 保留原英文标题。
  参考[官方唱片目录](https://zombielandsaga.com/1st/discography/detail.php?id=1017016)、
  [Bilibili 歌曲集](https://www.bilibili.com/video/BV1MJ411X79Z/)与
  [AcFun 歌曲集](https://m.acfun.cn/v/?ac=4866686)。旧中文显示名保留为点歌别名。
- song_025/026 与直播间投稿的“谢谢你 现在与未来”“如果今天将被铭刻于历史”统一，
  参见[前者](https://www.bilibili.com/video/BV1ihyoBeEUT/)及
  [后者](https://www.bilibili.com/video/BV1Hxy4BxEXx/)。日文原名及“历史”等关键词仍保留。
- Drive-in Tori 是[伊万里餐厅的店名](https://www.drivein-tori.jp/)，不是泛指“鸟”。
  宣誓！ALIVE センセーション 保留原名，不继续把 sensation 简化为“活着的感觉”。
- 唐津曲的ツガニ不是特指筑后川蟹；[佐贺官方旅游资料](https://www.asobo-saga.jp/files/tmp/227a6f79b9369a4b2217b11a10ca5f2a.pdf)
  将其列为唐津当地河蟹。けえらん 是米皮包豆沙的和果子，并非蛋糕，见
  [唐津观光协会](https://www.karatsu-kankou.jp/sp/libraries/detail/210)。
- ルート・グランブルー 是具体滨海道路，见[佐贺官方介绍](https://www.asobo-saga.jp/route_grand_blue/)。
  おおち うすにごり 是[小松酒造的烧酎](https://manrei.jp/shouchu/)，不是“大地薄浊酒”。
  松露馒头是当地豆沙点心，不能让观众误认成松露食材或中式馒头。
- 修正原文识别错误及其造成的中文误译，例如马尾辫“枝垂れた”、否定的“成れない”、
  ハート/鳩、トレードマーク/トレド幕、UMA/上前等。参考
  [JOYSOUND](https://www.joysound.com/web/search/song/942050)、
  [演唱者访谈](https://www.animatetimes.com/news/details.php?id=1619767202&p=2)、
  [授权歌词页](https://utaten.com/lyric/ac22092108/)。完整歌词来自用户附件，不转载整首网络歌词。
- 29時按次日凌晨五点理解；儚さ改为“短暂易逝”；佐贺地名谐音与超大/ちょうだい的
  双关保留在译文语境中。以上是具体文本审校，不代表对全部译名进行了平台流行度统计。

手工修订位于 `config/lyric_corrections.yaml`，必须匹配指定原文才允许应用，
避免文件换版后误改另一句。保留未修订的原始附件与旧视频用于复核、回退。

## 时间轴证据与剩余风险

7 首 TXT 的参考来源、源文件哈希、显示段覆盖的原始行号及起始毫秒记录在
`config/lyric_reference_timings.json`；此文件不含完整歌词、音频或账号数据。
其中 song_030 在解码验收时被阻止部署，`blocked_reason` 保证后续导入默认也不会启用。

- song_005、015、029 的规范化原文字流与参考版本完全一致；005 将连续短句合并显示，
  没有凭空插值。015 的 58 句全部逐句对应。
- song_013、027、033 另行检查了假名/汉字、数字、注音和合并句差异。
  使用参考段落起点展示用户原文和译文，不复制网络译文，不将分组误称为逐字卡拉 OK。
- 公开参考轴只证明文本对应和时间来源，不证明每个起点都听校过。
- 7 首没有明确末句清屏标签，暂用受音频长度限制的 5 秒显示尾时，明确标记
  `unverified_last_line_hold`，这不是声乐结束点。
- 超过 12 秒的显示段在每首 manifest 的 `long_display_cues` 中。有的是长句，
  有的是源 LRC 缺少间奏清屏；不能一律按 5 秒截断并宣称精确。
- 不以 ffprobe 粗略音轨 duration 判定丢音。逐包检查的 20 秒样例实际 AAC 包跨度
  为 20.032 秒；AAC 编码延迟和 30 fps 帧量化仍需在端到端验收时考虑。

尚未替换的 10 首：

| ID | 曲名 | 原因 |
|---|---|---|
| 003 | DEAD or RAP!!! | 对话标签、分句及参考时间顺序需要重新核对 |
| 004 | 让FLAG迎风飘扬吧 | 参考版比本地长约 1.56 秒，不能只凭同名套轴 |
| 008 | To My Dearest | TXT 与完整参考轴不全对应，存在缺段/重复段问题 |
| 009 | We are FranChouChou! | 成员口号、对白、拟声段展开方式不一致 |
| 010 | ゾンビランドDEMPA!! | 同版曲目公开接口未返回带时轴歌词 |
| 016 | Drive-in Tori | 参考版与本地时长不同，短曲对偏移尤其敏感 |
| 022 | Little Parappo | 大量 scat，无轴拟声词不能当作精确字幕 |
| 023 | 激昂Survive Complete Edition | 呼应、rap 与版本分句不同，需要听校 |
| 030 | 宣誓！ALIVE センセーション | 原始 FLAC 文件头时长与实际解码相差约 3.56 秒 |
| 038 | 生命 | 所供日文更接近释义，不能当作逐字演唱原文 |

《生命》的版本/演唱者可参考[发行页面](https://music.amazon.co.jp/tracks/B0BF8S5YBM)。
本轮不把外部文本差异归咎为“歌曲不存在”，也不覆盖成不相干版本。

## 导入与复核

安全解包结果在 `runtime/lyrics-import/`；正式资产分别位于
`media/lyrics/20261110-v1/`（26 LRC + 3 参考轴）和 `media/lyrics/20261110-v2/`（3 参考轴 + 1 阻止部署的候选）。
每首保存原文、译文、cues、ASS、音频、封面和无字底片。Git 只提交代码、纠错表、
无歌词的时间映射和文档，不提交压缩包、完整歌词或媒体。

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q bili_songbot scripts/import_lyrics.py scripts/build_lyric_media.py tests
git diff --check
# 使用新目录；不自动改正式曲库或重启服务。
.venv/bin/python scripts/import_lyrics.py --manifest runtime/lyrics-import/catalog-map.json --reference-index config/lyric_reference_timings.json --output media/lyrics/NEW_RELEASE
.venv/bin/python scripts/build_lyric_media.py media/lyrics/NEW_RELEASE
```

低优先级构建后检查音频时长和分辨率，所有目标文件验证通过后才修改曲库路径。
后续应听校全部 42 首，优先处理上表 10 首、长显示段、7 个末句结束点，
再从直播接收端核验长时间播放和版本切换，才能签署全曲逐句验收。

当前验收：工程回归与已导入时间轴结构检查通过；全曲逐句翻译/演唱时轴最终验收未通过。
