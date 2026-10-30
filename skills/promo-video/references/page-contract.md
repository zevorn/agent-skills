<!-- SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission -->
<!-- SPDX-License-Identifier: MIT -->

# 合成页面约定

合成页面是一个 HTML 页面，`scripts/render_frames.py` 通过本机 HTTP 服务打开它，逐帧调用
`window.renderFrame(frame)` 后截图。`assets/page-template/` 是一个可以直接渲染的 16 秒示例。

## 接口

| 名称 | 要求 |
| --- | --- |
| `window.ready` | 字体、图片、数据加载完成并渲染第 0 帧后设为 `true` |
| `window.FPS` | 帧率，默认 30；无旁白的动效片可以用 60 |
| `window.DURATION` | 总时长（秒） |
| `window.renderFrame(frame)` | 返回 Promise；完成时画面已经完全对应 `frame / FPS` 秒，图片已解码 |
| `window.getCues()` | 音效提示点 `[{type, t, ...}]`，类型见 [配乐、音效与旁白](audio.md) |
| `window.getSubtitles()` | 字幕 `[[开始, 结束, 文本], ...]`，用于导出 SRT 与字幕检查 |
| `window.qaText(t0, t1, step)` | 返回文字重叠、出画、停留过短、从未出现的报告 |

渲染器在地址后附加 `?render=1&scale=N`；页面可以按 `scale` 选择 2 倍尺寸的图片序列。
预览时打开 `index.html?dev=1&t=秒数`，底部出现播放按钮与拖动条。

## 确定性

- 所有动画放在一条暂停的 GSAP 时间轴上，`renderFrame` 调用 `tl.time(t, false)`；每帧需要计算的内容（计数器、数据回放、粒子位置）写成以时间为参数的函数。
- 不使用 `Date.now()`、未设种子的随机数、CSS `transition` / `animation`、`<video>` 元素。视频素材先导出成 `00000.jpg` 起编号的图片序列，按帧号设置 `src` 并等待 `decode()`。
- 截图前等待两次 `requestAnimationFrame`，确保合成完成。
- 字体使用本地字体包（例如 `@fontsource-variable/noto-sans-sc`），就绪前用 `document.fonts.load(字重, 样例文字)` 加载页面上与动态文字中出现的全部字符；分区字体只下载出现过的字符。
- 通过“随机访问与连续渲染对比”检查确定性：同一帧分别直接跳转渲染与从前一秒逐帧推进渲染，像素差应接近 0。

## 时间轴文件

时间轴 JSON 同时被页面和配乐脚本读取：

```json
{
  "fps": 30, "bpm": 120, "duration": 168, "overlap": 0.45,
  "scenes": [{"id": "open", "start": 0}, {"id": "title", "start": 6}],
  "subtitles": [[0.6, 5.6, "一句完整的字幕。"]]
}
```

- 场景范围为 `[本段起点, 下一段起点 + overlap]`，相邻两段叠化 `overlap` 秒。
- 画面内事件（推力出现、状态切换、完成时刻）的偏移量也写在这里，配乐脚本用同样的数值计算音效时间。
- 场景起点放在小节线上，见 `scripts/tempo_grid.py`。

## 素材

- **三维与物理画面**：从记录中的状态（关节角、位姿）离线渲染，不重新计算物理过程；渲染分辨率取显示尺寸的 2 倍再缩小，4K 成片时再乘 2。机器人类场景可以用暗色地面、雾效与软阴影统一风格。
- **透明抠像**：封面或叠加用的主体，使用渲染器的分割通道（例如 MuJoCo segmentation rendering）只保留主体几何，排除地面与场景中的其他刚体。
- **界面与终端**：按视频风格重绘，结构与配色参考原界面，数值逐帧回放运行记录；终端输出用 `pyte` 等终端模拟库解释 ANSI 序列后逐帧显示。
- **品牌**：标志使用透明 PNG；`assets/watermark/` 有深色与浅色两个版本。

## 文字检查

`qaText` 逐帧扫描选择器匹配的文字元素：

- `overlaps`：两段可见文字的包围盒相交。长度不超过转场叠化时间的重叠来自叠化，其余需要调整版式或时间。
- `offscreen`：文字超出画面。
- `brief`：可见时间少于 0.8 s 的文字。
- `never`：从未达到可见透明度的文字。

```sh
python3 scripts/render_frames.py eval page/index.html "window.qaText(0, window.DURATION, 0.2)"
```
