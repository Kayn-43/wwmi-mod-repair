# WWMI Mod Repair

用于修复已有鸣潮 **XXMI / WWMI / 3DMigoto Mod** 的 Codex Skill。由多轮实际文件分析、成对帧对照和用户游戏验证整理，重点是可追溯的最小修补与精确回退。

## 能处理什么

- 游戏版本变化后衣服破碎、部件消失、替换失效。
- Fixer 后橙脸、脸与身体色差、其他材质错色。
- 初次显示、拉远视角、切人、变形或骑乘后错色，拉近或打开菜单恢复。
- 菜单与大世界搭配不同，退出重进后丢失选择。

修复以已有 Mod 为基础，保留有效 hash、绘制、骨骼、服装开关与资源路径。不会从零制作 Mod，也不会把某角色的资源号或旧 hash 表当成通用修复。

## 安装与使用

在支持 Skill Installer 的 Codex 中发送：

```text
$skill-installer 请从 https://github.com/Kayn-43/wwmi-mod-repair/tree/main/skills/wwmi-mod-repair 安装这个 Skill。
```

也可下载本仓库，将 `skills/wwmi-mod-repair` 整个目录放到当前 Codex 支持的 Skill 目录。当前官方文档列出的项目目录为 `.agents/skills/`，用户目录为 `~/.agents/skills/`；已有同名 Skill 时先保存原版，避免并存重复版本。具体安装位置以正在使用的 Codex / Skill Installer 为准。[OpenAI 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)

使用时提供实际 Mod 路径、具体症状、是否运行过 Fixer，以及可用的原版/备份/修复版：

```text
$wwmi-mod-repair
请修复 <实际 Mod 目录>。切人后衣服错色，拉近恢复。
先比较现有 mod.ini、备份和已有有效帧，保存备份后安装最小修补。
```

安装包只包含工作方法与工具，不附带任何角色 Mod。实际修补需要你自己的 INI、DDS、BUF 和必要的运行证据。

## 六个案例与五类问题

| 案例 | 核心经验 |
|---|---|
| 坎特蕾拉 | 局部隔离脸部 RabbitFX 注入；严重橙脸改善不等于轻微肤色差完全消除 |
| 莫宁 | hash 与 TexCoord 配套模型修补，再按组件绑定材质 |
| 洛瑟菈 | 先确认绘制执行，再同步菜单/大世界持久搭配状态 |
| 绯雪 | 搭配保存和材质分开；按实际服装组件补绑定 |
| 爱弥斯 | 补默认 Diffuse，保留已识别普通/Charged 分流 |
| 奥古斯塔 | 只读稳定对照，借鉴组件绑定结构；本轮未实施修补 |

归为模型/缓冲区适配、脸部注入、搭配状态、低分辨率漏匹配和组件材质绑定缺口。详细成功阶段、失败实验和仍未知的原因见 [案例集](skills/wwmi-mod-repair/references/six-mod-casebook.md)。

本轮案例截至 **2026-10-10**。版本/hash/资源号属于历史证据，使用时重新核对当前文件和作者规则。用户确认“成功”或“效果很好”是对应阶段的运行反馈，不代表独立测试了所有形态、距离与 Toggle。

## 只读辅助工具

Python 3.10+；基础分析使用标准库。可选 Pillow 可辅助读取部分图像尺寸，DDS 解码能力以实际环境为准。

```powershell
python -X utf8 skills/wwmi-mod-repair/scripts/audit_mod.py --mod-root '<实际含 mod.ini 的目录>' --output '<Mods 外的输出目录>' --compare '<备份 INI>'
```

`compare_texture_frames.py` 用于对比已有 ASCII namespace 的 Before/After 槽位诊断采集；它不会生成采集、修改 Mod 或自动安装候选。参数见 `--help`，方法见 [视距与低分辨率匹配](skills/wwmi-mod-repair/references/texture-streaming.md)。

两个工具均属于静态分析，不模拟全部 INI 条件、包含关系或 GPU shader；输出候选需人工核对和游戏验证。工具报告会包含实际本机路径，分享前应自行检查；本仓库没有发布个人采集日志或报告。

## 来源与内容范围

案例的规则来源包含固定版本的 [Wuwa_Mod_Fixer](https://github.com/Moonholder/Wuwa_Mod_Fixer)，以及本机 WWMI/RabbitFX 实现。第三方实现通过来源链接引用；本仓库不复制其程序、角色贴图、网格、游戏文件或第三方 Mod 整包。

保持原 Mod 作者署名和原有服装默认值。仓库与游戏、XXMI/WWMI、RabbitFX 或 Wuwa_Mod_Fixer 作者没有官方隶属关系。

维护原则：保留失败记录；优先复核已有有效帧；一次限定一个实验变量；成功版按角色冻结；安装/回退识别未知后续修改。
