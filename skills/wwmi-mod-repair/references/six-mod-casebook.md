# 六个 Mod：分类、修复及证据边界

归纳截至 2026-10-10 的本轮会话。使用当前文件、精确 diff、部署清单和用户反馈；没有独立操作游戏或逐项测试全部场景。这些资源号与 SHA256 只标识本轮版本，不是角色通用配置。

## 问题分类与角色结果

| Mod | 问题类别 | 实际处理 | 最新可用结论 |
|---|---|---|---|
| 坎特蕾拉 summer_cantarella | Fixer 后橙脸；后来仍有轻微脸/身体色差 | 保留 Fixer 与其他组件 RabbitFX；先仅取消脸部 Lightmap 注入，后来仅取消剩余脸部 Diffuse 注入 | 严重橙脸用户确认改善；轻微色差后续实验无独立明确成功反馈，不记为色差完全消除 |
| 莫宁 Moonlight Mirage Mornye Normal SFW | 初次衣服破碎/缺件；后来视距、启动和骑乘后错色 | 有来源的 hash/检查与配套 TexCoord 修补；低分辨率别名；最后 Component3 四类材质绑定 | 模型修复成功；最终用户反馈比较稳定 |
| 洛瑟菈 Frozen Frame Reminiscence Lucilla SFW | 菜单/大世界搭配不同，起初被视为大世界不生效 | 帧确认 Mod 绘制执行；共享持久状态，ASCII namespace，迁移已选搭配 | 用户确认成功，后被列入稳定对照；未发动 Ult 的未命中不算 Ult 故障 |
| 绯雪 Hiyuki Sanguine Petal | 搭配重启不一致；视距及切人/下车后服装错色 | namespace/按键条件；实测别名；Component3 身体绑定后补 Component4/5 服装绑定 | 用户反馈比较稳定；设置成功与材质成功分别记录 |
| 爱弥斯 Aemeath | 首次显示、变形、骑乘及切人后服装错色，拉近恢复 | 精确别名曾改善；组件材质绑定；最终给 Component3 补默认 Diffuse，保留已识别 Charged 分流 | 三版后用户反馈“这次效果很好”；不推导所有距离/Toggle/形态已逐项验证 |
| 奥古斯塔 Augusta SFW | 用户提供的稳定对照 | 只读研究组件级直接贴图绑定与搭配分支，本轮未实施修补 | 稳定参考，不能写成 Codex 修好了它 |

## 坎特蕾拉：两条贴图通路，局部取消注入

完整初次 diff、资源解码与缓冲区检查见 [verified-cases.md](verified-cases.md)。用户指定 BAK 不是真正 hash 更新前原版；不能从 BAK 名字假定全部版本差异。

脸部实测定位在 Component2，R6 为脸部 atlas，R5 为 Lightmap。全局删除 RabbitFX 会破坏其余替换；删除 Component0/4/6/7 注入、给 R6 增加 filter_index 的实验均未解决。

初次成功是将 `Resource\RabbitFX\Lightmap = ref ResourceTexture5` 改为 null，保留 Diffuse、传统 TextureOverrideTexture5 和其余组件。后来用户报告菜单/大世界/近景均轻微偏橙，说明严重橙脸改善不等于肤色完全一致。

后续单变量实验再将脸部 `Resource\RabbitFX\Diffuse = ref ResourceTexture6` 改为 null，保留 SetTextures、Lightmap=null、传统脸部 override、其余组件及所有 DDS/BUF。当前该版已安装，但用户没有单独确认轻微色差消失；后来的“稳定 Mod”评价只支持整体表现稳定。没有独立脸部 shader/槽位采集，亦不能排除 atlas 自身色差。

复用经验：优先隔离已定位的脸部材质注入，保留传统替换和有效版本适配；不能机械给脸填完整四类材质，也不盲调 DDS 色相。

## 莫宁：模型适配与材质稳定分阶段处理

初次修复包括 Component4 有来源的三项 texture hash、必要检查及缺失 LOD，另配套修改 TexCoord 遮罩。先核对索引、stride、真实引用顶点；保留主 UV、其他字节和眼睛。用户只验证 combined，不能归因单独 hash 或 UV 修改。数值、来源与算法限制见 [verified-cases.md](verified-cases.md)。

后续低分辨率 hash 分批补齐曾达到约 1 秒内恢复；骑乘等新触发条件仍出错。最终仅在 Component3 骨骼就绪分支、旧贴图检查前加入：Diffuse=R3、Lightmap=R17、Normalmap=R18、Materialmap=R4，调用 RabbitFX SetTextures。四项用途由固定作者配置与正常帧核对，不是照抄奥古斯塔槽位。

用户先确认莫宁稳定性提高，后来确认比较稳定。此次仅改 INI；已成功 TexCoord 必须保留，不回退到修模型之前的缓冲区。

## 洛瑟菈：绘制命中不等于搭配一致

旧浮窗显示 Bottom/Ult 未命中，完整帧却证明 Top/Bottom 使用 Mod 缓冲区绘制。菜单上衣/下装选择与大世界保存值不同，问题属于状态分支，不能继续盲改 mesh hash。

路径式共享变量候选仍失败；成功版使用 `LucillaOutfitMenu` 明确 namespace，迁移八项菜单保存选择，以 ASCII 跨 INI 引用同步 Top/Bottom。未改 mesh、draw、缓冲区；保留 Ult 独立系统。详见 [toggle-state.md](toggle-state.md)。此结果不证明当前 DLL 普遍不支持中文路径。

## 绯雪：先保留选择，再修正确服装组件

保存搭配用稳定 namespace 与合法按键条件修复；保持用户已选值，不在 Present 强制重置。视距错色需另行处理，不能把设置保存成功当成材质成功。

首次组件实验只给 Component3 绑定 Normalmap=R44、Lightmap=R45、Materialmap=R46、Diffuse=R19。用户后续指出主要服装异常，结合实际 draw 注释和旧正常帧定位到 Component4 的丝袜/脚/鞋饰、Component5 的旗袍/袖子等，才扩展：

| 组件 | Normalmap | Lightmap | Materialmap | Diffuse |
|---|---|---|---|---|
| 4 | R47 | R48 | R49 | R31 |
| 5 | R50 | R51 | R52 | R35 |

此处 Rn 指完整 `ResourceTextureN`。当前作者配置缺少 Hiyuki 的材质 meta；用途从旧正常帧 000669/000662、格式/分类值、实际资源赋值和本机 RabbitFX Main 规则推导，并实际解码八张 DDS 交叉检查。缺少原始 PS 反汇编，仍区分“推导映射”与“作者配置确认”。用户最终反馈比较稳定。

复用经验：身体修补后服装仍错，先定位遗漏的服装组件；同样症状不能据此全组件填图。

## 爱弥斯：默认 Diffuse 缺口与形态选择

早期作者 LOD 一条规则不足，有效异常/正常帧各 27 次绘制，补八处实测绑定后用户曾反馈一切正常。后续骑乘/变形暴露新条件，不抹掉历史改善，但不再把早期版本当作全场景稳定。

组件材质一版绑定 Component3 的 L=R34、N=R33、M=R30，Component4 的 L=R35、D=R36、N=R37、M=R38，Component6 的 D=R19、L=R40、N=R45、M=R18。Component3 Diffuse 因普通 R31 与 Charged R33aa 不同而暂缺。用户一度反馈大招稳定、切人/骑乘仍错，不能直接复用该阶段的结论到后续版。

二版在六个既有 Diffuse 回调中、限定组件3/槽3/支持 PS，追加 t60 引用；补一个旧帧同范围/VS/PS 的低 hash `0c80e5aa`。用户后续仍报告启动、变形、骑乘服装异常，故二版是覆盖不完整的实验，不是最终成功版。

三版相对二版仅增加一行，在 Component3 既有 SetTextures 前设置 `Resource\RabbitFX\Diffuse = ref ResourceTexture31`。不新增 hash/检查/调用；已识别 Charged 输入仍经原有回调选择 ResourceTexture33aa。用户反馈“这次效果很好”。

文件事实支持：二版未给默认 Diffuse，只有已知 hash 能补 t60；三版填补了默认绑定缺口。普通与 Charged 两张 4096×4096 DDS 像素不同，不能互换为通用规则；未知 Charged 输入使用普通兜底，未证明专用颜色细节全部保留。旧帧早于此实验，没有捕获全部过渡瞬间，不能独立证明显存污染或所有角色同一个底层故障。

## 奥古斯塔：稳定对照的正确用法

Component3 的局部命令列表直接绑定 ps-t0/1/2；Component5 同样直接绑定并保留 `$tou` 条件。存在实际角色 DDS，即使没有传统 `this = ResourceTexture`，也不能称它不替换贴图。

该 Mod 提示“绑定与实际组件绘制关联”可以更稳定；槽位用途与其他角色不同，不能复制其 t0/1/2 编号。坎特蕾拉、洛瑟菈也提供组件用途绑定参考；它们仍有共享 hash/object_detected，因此这些字段不能单独证明跨角色干扰。

## 失败实验与共通经验

- 全局删除 RabbitFX、回退整个 Fixer不适合已有效替换的版本；局部诊断后最小改变。
- 私有 filter_index 被本机模糊格式分类覆盖的实验未解决；不再把该数值当作可靠输入身份。
- 提前注册、调整 Present/ShapeKey 时序不足以单独解决持续材质错误；不因此移除骨骼保护。
- 首次补官方 LOD/若干别名不代表覆盖所有分辨率或新形态。
- 根据一人的帧向三人全组件增加 12 槽重检查、批量推断 hash 和无各自证据的共享 hash 更新，用户反馈恶化；保留为失败版本，不叠加复用。
- 完全重启仍失败时，不继续解释为仅 F10 的缓存。回退字节正确也不证明恢复的基线已稳定。
- 帧回调前输入可能包含上一绘制残留；描述变了不等于引擎一定更换了材质用途。稳定对照及用户改善不能独立证明跨角色污染。
- 在已有有效帧上研究；只补真正缺少的对照，避免反复让用户重录。空角色帧与未发动 Ult 的帧不作失败证据。

## 最终阶段文件标识与追溯

2026-10-10 已核对以下活动文件；本轮 Skill 更新不改游戏 Mod：

| 版本 | SHA256 |
|---|---|
| 莫宁组件绑定成功阶段 INI | 504fd5ed4e8e9df42de087b4d62b8d0dabee8d8bf43d711a912c249287960e3d |
| 莫宁配套 TexCoord | f51a1abe9de5b55c35ef9986a0b34a7826f0733f3f36b68f6aeb10f7cf1c7ef7 |
| 绯雪服装材质二版 INI | 4a198acd899e1b6b8220f0830d579d488d0258790ae4ce220c448dbc7fc4ce28 |
| 爱弥斯默认 Diffuse 三版 INI | f1b75952e123b5bd86b5e32fde7a6b4ede2d65c9d44bc3cb7b36b994a004367c |
| 坎特蕾拉轻微色差实验 INI（非肤色一致确认） | f10cb5adad582c1ad39acff7819898cb3f9d90bc1920891cb9e4e966627188b2 |

较早案例与哈希在 [verified-cases.md](verified-cases.md)，不能让旧默认安装器覆盖此后的成功阶段。新实验按角色冻结与当前一致的活动 INI；需要配套缓冲区时一起保存。

本地证据目录名：`cantarella-face-tone-repair`、`stable-mod-reference`、`component-material-repair`、`component-material-reuse`、`hiyuki-clothing-material-v2`、`material-transition-residuals`、`aemeath-clothing-material-v3`，以及早期 `lucilla-repair-20261007`、`verified-three-character-20261007`。它们用于追溯，不是 Skill 运行所需固定路径；不打包角色 DDS、BUF、截图或账户配置。
