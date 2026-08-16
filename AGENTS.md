# IPTV 节目列表

自用 IPTV 组播节目列表（公开仓库 `hex-ci/IPTV`）。三个 m3u 文件直接用于播放器/udpxy 拉流，北京联通列表有维护脚本，天津联通手动维护。无构建、无测试、无第三方依赖（脚本仅用 Python 标准库）。

## 文件结构

- `beijing-unicom.m3u` — 北京联通频道列表，有维护脚本
- `tianjin-unicom-1.m3u` / `tianjin-unicom-2.m3u` — 天津联通，手动维护
- `beijing-tianjin.m3u` — 北京+天津合并列表（`merge_tianjin.py` 生成，勿手改）
- `scripts/update_channels.py` — 北京联通的维护脚本（对比 + 重新生成）
- `scripts/merge_tianjin.py` — 生成北京+天津合并列表
- `README.md` — 各列表的 raw 地址（供播放器订阅）

## 维护命令（北京联通）

```bash
python3 scripts/update_channels.py           # diff：拉 islc+gist 对比本地，打印新增/删除
python3 scripts/update_channels.py --apply   # 用脚本内置映射表重新分组+排序+补 EPG/台标（幂等）
python3 scripts/merge_tianjin.py             # 生成 beijing-tianjin.m3u = 北京 + 天津独有频道（幂等）
```

维护信息来源（URL 在脚本顶部 CONFIG 段）：
- islc `https://raw.githubusercontent.com/islercn/BeiJing-Unicom-IPTV-List/refs/heads/master/iptv.m3u`
- gist `https://gist.github.com/sdhzdmzzl/93cf74947770066743fff7c7f4fc5820`
- gist 评论（API `https://api.github.com/gists/93cf74947770066743fff7c7f4fc5820/comments`）—— 表格外的频道失效/新增/地址变更信息在这里，维护时必看
- EPG/台标 `http://epg.51zmt.top:8000/`（e1.xml.gz 为 tvg-id 基准，e.xml 只有 101 频道太窄不能用）

## m3u 格式约定

- 首行 `#EXTM3U x-tvg-url="...e1.xml.gz"`。
- 每个频道两行：`#EXTINF:-1 tvg-id="…" tvg-name="…" tvg-logo="…" group-title="…",名称` + `http://192.168.1.1:7088/rtp/<组播ip>:<port>`。频道名不带频道号、不带 `[高清]/[标清]/[4K]` 标签（清晰度由 group-title 前缀表达）；4K 版保留「4K」字样、北京卫视保留 SDR/HDR 以区分画质。
- group-title 体系：`[4K]`/`[高清]`/`[标清]` × `央视`/`北京`/`卫视`/`少儿`/`教育`/`数字付费`/`购物`/`IPTV专区`，另加 `[测试]`。

## 维护约定

- 频道身份 = 组播地址 `ip:port`；同名判断靠组播地址，不是靠标题字符串。
- 本地已有频道：名称/EPG/编号以本地为准（不要改动）；地址以基准为准（漂移时改地址）。
- 基准有、本地无 → 新增；本地有、基准无 → 删除。
- 新增频道需在脚本 `M` 表补一行映射（分组、tvg-id、台标路径）后再 `--apply`。
- **不自动 commit/push**：改动完成后交给用户 review，由用户自己提交。

## Pitfalls

- `192.168.1.1:7088` 是个人 udpxy 内网前缀，脚本从现有文件继承、不硬编码；换环境时从文件改。
- `scripts/update_channels.py --apply` 会整体重写 m3u（重排序），改完核对 `git diff` 是否只动了该动的。
- 脚本 diff 模式只看 islc+gist 两个文件、不含评论，所以「新增/删除」列表需结合 gist 评论解读（例：广东/深圳 4K 是 203/202，islc 的 27/28 是旧地址别收录）。
- CCTV5+ 频道号是 18，但排序需紧跟 CCTV5（脚本 sort_key 里已特判，别删）。
- tvg-id 以 51zmt e1.xml 为准；历史常见错误 id（BTV 1873-1880、金鹰纪实 2025、财富天下 6623、教育4台 7245 等）不要再写。
- 完整的维护流程细节（分组全集、EPG id 表、5 处「就近映射」待确认项）见 skill `iptv-channel-maintenance`。
