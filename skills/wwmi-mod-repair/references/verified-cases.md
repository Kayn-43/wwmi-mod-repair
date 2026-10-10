# 早期案例：2026-10-07

这些是同一修复会话早期阶段的历史证据。SHA256 标识当时文件，不是当前游戏的全局适配标准。后续骑乘/形态问题、成功阶段和仍未确认的脸部轻微色差见 [six-mod-casebook.md](six-mod-casebook.md)。未来使用前必须重新核对目标目录和最新规则。

## 夏装 Cantarella / summer_cantarella

### 症状与输入

用户反馈：原版脸正常但替换破碎；Fixer 版基本恢复，却在菜单/大世界出现橙脸。全局删除 RabbitFX 会重新破碎，删除 component0/4/6/7 的注入没有解决。

用户指定的原始文件是 `mod.ini_2026-10-07 03-15-39.BAK`。它与操作前 `mod.ini` 的 hash、匹配范围、drawindexed、ResourceTexture 文件映射完全相同；正文差异只有 component1–7 的 RabbitFX 注入。两者均无 component0 RabbitFX 注入。

另一个更早备份 `mod.ini.qaqm-inibak-20261007-031531-143-5311f1` 提供18个旧贴图 hash，说明用户指定 BAK 已处于贴图 hash 更新之后。没有 mesh 匹配或 draw call 变化证据。

### 文件定位

实际 DDS 解码确认：

- component2 的 R6：`Components-2 t=87821a93.dds`，脸部肤色图；操作前 override hash 为 `c5961a74`。
- component2 的 R5：`Components-2 t=0c868365.dds`，橙色 Lightmap；操作前 override hash 为 `91fca2ee`。
- R16 为眼睛贴图，属于 component6。

Color.buf/TexCoord.buf 对应 BAK 各有4921个顶点改变，仅落在自定义 component4/7；脸部 component2 的引用顶点没有改变。因此本次没有回退缓冲区。

### 实验结果

| 版本 | 独立改动 | 结果 |
|---|---|---|
| v1 | 给 TextureOverrideTexture6 增加 `filter_index = 1718.3` | 用户截图仍橙脸，身体肤色看起来正常 |
| v2 | 仅取消 component2 的 RabbitFX Lightmap 引用 | 用户反馈“成功了”，采用为最终版 |
| v3 | 仅移除 component2 的整段 RabbitFX 注入 | 已生成但未测试 |

最终相对于操作前 Fixer 版唯一修改：

```diff
- Resource\RabbitFX\Lightmap = ref ResourceTexture5
+ Resource\RabbitFX\Lightmap = null
```

位置为 `[TextureOverrideComponent2]`，保留脸部 Diffuse R6、传统 TextureOverrideTexture5、其余组件 RabbitFX、所有有效 hash 和 Toggle。v2 从最初 Fixer 基线生成，没有叠加失败的 v1 分类标记。

操作前 INI SHA256：`79319a6ca7e4a43d1732f456d9c7af12fa633d263eada21a83e6fb11c969d4ba`。

最终 INI SHA256：`fc279656f0e50705a97567862fbf7cee98b90a4ec5e37b7b1d7f3e186e6bbfd2`。

这支持该 Mod 的脸部 RabbitFX Lightmap 注入通路与橙脸有关；没有捕获 shader/纹理槽，不把底层分类机制宣称为已证实。菜单、LOD、表情和每项 Toggle 没有获得分项反馈。

## Moonlight Mirage Mornye Normal SFW

### 症状与检查

用户反馈：衣服破碎、部件消失，基本没有生效，未运行 Fixer。当前 INI 与 qaqm 备份已有20处贴图 hash 变化，但无 RabbitFX 注入。

资源全部存在；Position、Vector、Color、TexCoord、Blend 各对应190862个顶点。Index.buf 有933612个索引，最大190861；全部自定义绘制未越界。

本机 WWMI 自述1.10、Mod 要求1.00。骨骼 INI 注释提到其他输入方式，但实际 SkeletonMerger.hlsl 仍读取 b8，故保留原骨骼与 BlendRemap 逻辑。

### 有来源的配套修补

使用 Wuwa_Mod_Fixer 提交 `6fa4d31e6fd2763cd5b8c98f7c387c1c8988a8d0`，配置自述3.6.1：

- [Mornye 角色配置](https://github.com/Moonholder/Wuwa_Mod_Fixer/blob/6fa4d31e6fd2763cd5b8c98f7c387c1c8988a8d0/config.json)
- [ResourceOverrideFixer](https://github.com/Moonholder/Wuwa_Mod_Fixer/blob/6fa4d31e6fd2763cd5b8c98f7c387c1c8988a8d0/src-core/src/fixers/resource_override.rs)
- [Rendering33Fixer](https://github.com/Moonholder/Wuwa_Mod_Fixer/blob/6fa4d31e6fd2763cd5b8c98f7c387c1c8988a8d0/src-core/src/fixers/rendering_3_3.rs)

| 资源 | 当时旧 hash | 当时规则目标 hash |
|---|---|---|
| R20 / component4 Diffuse | 4ba9f939 | 89a5a60b |
| R21 / component4 Normalmap | d6cdd4cf | e9ac4474 |
| R22 / component4 Lightmap | da119917 | 47708382 |

配置还追加 `CheckTextureOverride = ps-t9/10/11` 及37个缺失的当时 LOD 重定向；原有重定向保留。没有增加 RabbitFX 注入。

TexCoord 修补采用上述来源的缺失部件选项：stride=16；每顶点字节4或6非零时，将字节4–7清零；该角色规则跳过component6（眼睛）。先按实际自定义 drawindexed 定位，确认连续顶点范围与准确引用集合相等。实际改变51494个顶点、204855字节。主UV字节0–3、字节8–15、眼睛和其他缓冲区逐字节保留。

这条算法是当时特定角色/版本的可选规则；非零次级UV并不天然等于损坏。不要跨角色自动应用，不要在索引格式、stride、base vertex 或组件范围未核实时使用。

### 结果与边界

用户安装配置+遮罩组合后反馈“很好，修复好了”，最终采用 combined。保留 hashes_only、masks_only、restore 对照；未分别测试，不能归因于单一修改。

初次模型修复 INI SHA256：`027ca0ffabee350689ccd553b2161a527b4db6f5a34dab9d4b3d7d08d70751d3`；后续视距修复继续以此配套缓冲区为基础，见下文。

最终 TexCoord SHA256：`f51a1abe9de5b55c35ef9986a0b34a7826f0733f3f36b68f6aeb10f7cf1c7ef7`。

43个原有文件中仅 mod.ini 与 Meshes/TexCoord.buf 改变，两份备份均通过 SHA256 核对。以后恢复此修复要配套使用 INI 与缓冲区。用户没有逐一报告所有场景、动作和 Toggle。

## Lucilla 菜单与大世界搭配不同

起初按替换失效排查；旧诊断显示Top命中、Bottom/Ult未命中。实际FrameAnalysis证明Top/Bottom的自定义绘制及绑定缓冲区已执行，菜单与大世界却各自保存了不同选择。没有发动Ult时未采到它，不能判定其损坏。

路径式共享变量候选仍失败；改为明确的 `LucillaOutfitMenu` namespace，迁移8项保存选择，用ASCII跨INI引用同步Top/Bottom后，用户反馈“成功了”。mesh、索引、draw和缓冲区保持。这是本次服装状态不同问题的已验证修复，不能归因为全部游戏版本均不支持中文路径。详见 [toggle-state.md](toggle-state.md)。

## Aemeath / Mornye / Hiyuki 视距错色

完整方法、失败的filter_index候选与采集有效性检查见 [texture-streaming.md](texture-streaming.md)。这些修复独立于此前模型/搭配问题，不能合并为单一原因。

- 提前注册、ShapeKey时序与持久化调整不足以解决持续错色。
- 私有filter_index候选被本机RabbitFX分类覆盖，改用精确hash、组件/槽位上下文约束的`this`绑定后仍需补齐遗漏的分辨率档位。
- 作者配置并非完整采集替代。爱弥斯补1条官方LOD仍错色，实际成对采集找到8处；绯雪首批5个hash之后再补4处；莫宁17个hash之后再补2个hash/3处绑定。
- 爱弥斯补采正常帧后，两帧各27个目标绘制；映射包含ResourceTexture33aa，截成ResourceTexture33会选错资源。无法对齐shader、格式不同或正常帧也未替换的槽位未自动加入。

最终用户反馈原文：“成功了，爱弥斯一切正常，莫宁1s内正常，绯雪1s内正常”。按角色记录：爱弥斯症状解决；莫宁、绯雪1秒内自动恢复。未证明后两者首帧完全正确，也未独立录制启动视频。

|当时已验证文件|SHA256|
|---|---|
|Aemeath INI|fbfbe407b7e2daeef2fcae5a5f91d11be51cc2a5c0d06993110f9478c8eb0392|
|Mornye INI|c7f7cc46abc3d82b034200caa53653c1a7a44cc71818e5c12bb699b1e93348e6|
|Mornye 配套TexCoord|f51a1abe9de5b55c35ef9986a0b34a7826f0733f3f36b68f6aeb10f7cf1c7ef7|
|Hiyuki INI|a19f882daf98e20a7597cda33a9ab2143b3eaccba5b8a49b30b8ab41c01ee3f3|

当时成功文件曾按字节保存，默认目标指向当时版；后续新触发条件又出现失败，不应将这些早期默认目标称为当前最终版。一次较早反馈曾被错误记为两者均自动恢复，用户纠正绯雪仍需拉近后撤销该记录；以各阶段补丁后的明确反馈为准。

## 证据来源

本 Skill 从实际 diff、资源/顶点计数、部署 SHA256 复核和本会话的用户成功反馈整理；没有仅从 Mod 名称推断成功。

原始记录保存在修复任务输出的 `analysis_report.md`、`deployment_verification.json`、`mod_fixed.ini.diff`，莫宁还包含 `mornye/repair_manifest.json` 与 `mornye/deployment_verification.json`。这些本地输出可用于追溯，不是 Skill 执行所依赖的固定机器路径。Skill 不打包角色贴图、网格或截图。

后续证据包括 `lucilla-repair-20261007/capture-evidence.json`、`shared-ascii-validation.json`，`startup-repair-20261007` 中前/后槽位描述报告，`aemeath-texture-repair-20261007/paired-frame-comparison.json`、`repair-manifest.json`，以及 `verified-three-character-20261007/validation.json` 的最终文件哈希与用户反馈。本 Skill 不依赖这些目录存在；复用时读取当前实际文件。
