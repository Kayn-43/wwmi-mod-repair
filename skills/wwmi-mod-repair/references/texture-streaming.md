# 视距与低分辨率贴图漏匹配

适用症状：初进大世界错色，拉近镜头、打开菜单后恢复；或者很快自行恢复。以实测输入为依据，不预设都是初始化问题。

精确别名成功后，切人/变形/骑乘仍出错时，另读 [component-material-binding.md](component-material-binding.md)，检查实际组件材质与默认 Diffuse。两种方法分别处理输入身份覆盖和材质绑定缺口，不能把早期补别名的成功扩大到全部形态。

## 区分等待资源与漏匹配

查看异常帧时 Mod 是否启用、骨骼是否就绪、实际替换是否执行。若已就绪而特定槽位仍保留未识别的输入，优先查贴图规则。提前 RegisterMod、改变 Present/ShapeKey 时序在本轮没有单独解决错色；不要由此移除实际绘制的骨骼就绪保护。

相同角色可经历多个分辨率档位，例如128、256、512、1024。一次采集只覆盖出现过的 hash；作者 `derive.LOD` 表和第一次补丁都可能遗漏更低一档。不同角色症状类似，只能共享方法，不能共享资源号或 hash。

## 有效的成对采集

异常帧保持原视距、角色可见；恢复帧在同一地点拉近至正常，不同时重载、改搭配或进菜单。若冷启动是触发条件，经 XXMI 完全重启测试。采集键以本机配置为准；本轮临时配置为小键盘0开启 hunting、Ctrl+F8采集，不能把键位硬编码为所有安装的默认值。

先验证日志与帧内容，再做 diff：

- 记录目标 mesh、组件、原生 DrawIndexed 索引范围、VS/PS、前后槽位描述，以及输入与替换后 hash。
- 帧有目录不等于有效。`Frame analysis aborted`且尚无角色绘制时补采该帧；保留另一有效帧。中断发生在角色已完整记录之后，则按相关调用是否完整判断，不仅凭中断文字一律废弃。
- 同组件、相同原生索引范围与相同 VS/PS 是优先对照。重复 pass 的数量或对应不明确时记录未匹配项，不强行按顺序配对。VS 不同但 PS/范围相同的情况需要另查槽位与格式证据，清楚记录差异。
- 追踪 Before 与 After 能区分未匹配和替换已执行。中文隐式 namespace 的日志截断时，可在独立 ASCII namespace 用特定 mesh hash 的前/后诊断记录；不修改原 Mod namespace 只为方便日志。

只读辅助命令：

```powershell
& $python 'path/to/wwmi-mod-repair/scripts/compare_texture_frames.py' --ini '基线.ini' --mod-root '实际资源所在Mod目录' --abnormal '异常FrameAnalysis目录' --normal '正常FrameAnalysis目录' --trace-namespace 'AemeathTextureTrace' --output 'Mods以外的报告目录'
```

对旧诊断如 `WWMIStartupTrace/HiyukiBefore`，加 `--before HiyukiBefore --after HiyukiAfter`。工具只读取已具备前/后描述的采集；不创建诊断、不改游戏配置。它不能替代对条件、多个资源映射或 VS 变化的人工复核。

## 确定资源，再补规则

合格证据链是：异常输入 hash → 同 pass/槽位的正常输入 hash → 当前 INI 完整 Resource 名 → 正常回调后的绑定变化和文件尺寸。解析完整标识符，例如 `ResourceTexture33aa`；同 hash/slot 对应多个资源时保留未知，不能取首项。

正常帧也没有替换的槽位、场景纹理、格式不同或 shader 不能对齐的项，不因 hash 改变就加入补丁。DDS 彩色通道不是错色证据。原生输入描述与替换后资源描述必须分别记录。

## 避免 filter_index 冲突的绑定方式

本轮首次用私有 `filter_index` 分类低分辨率 hash，再按 ps-t 值判断赋资源，实际未解决问题。采集看到本机 RabbitFX 模糊格式规则仍返回1718.6/1718.4，覆盖了预期的私有分类。此结论针对当时本机规则；不要推导为全部 WWMI 版本的固定优先级规律。

有证据的替代方式：在组件实际绘制就绪分支、原有资源检查前，执行专用检查；用非持久化组件和槽位标记限制 hash 别名的 `this` 赋值。检查完清零上下文，原有 RabbitFX 分类保持。

```ini
; 名称、组件、槽位、hash与资源仅作结构示例，必须替换为本 Mod 的证据。
[Constants]
global $repair_component = -1
global $repair_slot = -1

[CommandListRepairTextureComponent]
$repair_component = 3
$repair_slot = 1
CheckTextureOverride = ps-t1
$repair_slot = -1
$repair_component = -1

[TextureOverrideRepairTextureAlias]
hash = 00000000
match_priority = 0
if $repair_component == 3 && $repair_slot == 1
    this = ResourceTextureExample
endif
```

这是表达结构，不能原样安装。声明与原 `[Constants]` 合并、组件入口接入原实际绘制分支；不要删除原 TextureOverride、SetTextures、骨骼保护或 Toggle。相同低 hash 在不同组件/槽位使用不同资源时必须分别约束，检查上下文不能泄漏到后续 draw。

## 本轮结果与局限

- 莫宁：首次17个低 hash/29个绑定仍漏了两种128×128输入，后补3个绑定。其先前 INI+TexCoord修复必须配套保留。
- 绯雪：首次5个低 hash别名仍漏4处；其中component3三个槽位严格同VS/PS，component2一个槽位VS不同、PS与原生范围相同，单独人工确认后纳入。
- 爱弥斯：只补作者配置1条LOD后仍严重错色。正常帧第一次采集中断；补采后两帧各27个绘制，确认8处低分辨率漏绑定，含完整资源名 `ResourceTexture33aa`。只补这8处后用户反馈“一切正常”。
- 此早期阶段用户确认爱弥斯正常，莫宁、绯雪1秒内正常。保存当时文件及配套资源；后两者不写为首帧过渡已消除。后续新增骑乘/形态失败与最新组件材质修补见 [six-mod-casebook.md](six-mod-casebook.md)，不沿用本段为当前全场景结论。

这些数量和hash是历史覆盖范围，不是未来必须达到的规则数，也不是角色通用适配表。
