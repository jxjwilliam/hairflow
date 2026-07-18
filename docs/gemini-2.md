# **基于Mac M3 Pro与ComfyUI的美容美发头像组合API工作流技术研究与系统设计报告**

## **1\. 硬件基础设施与多实例路径重定向（Mac M3 Pro & 外置硬盘）**

在Apple Silicon架构（特别是搭载18GB或36GB统一内存的MacBook M3 Pro）上部署ComfyUI人像生成与美发组合系统，其核心在于平衡高速的数据读取需求与板载固态硬盘（SSD）的寿命保护1。美发与头像组合任务涉及多种庞大的扩散模型（如Flux.1-Fill、SDXL及SD 1.5等），通常会产生数百吉字节（GB）的模型读取量1。

### **1.1 外置存储拓扑与多实例路径映射**

为了避免频繁下载和读取数十吉字节的模型对板载SSD造成写入磨损1，本系统采用高速外置NVMe固态硬盘（通过雷电3/4或USB4接口连接，读取速度不低于![][image1]），并将所有模型、权重和LoRA重定向至该外置硬盘1。  
在Pinokio一键式本地AI管理器的运行环境下7，ComfyUI默认安装在特定的Git仓库目录下，其标准路径通常为 \~/.pinokio/api/comfy.git/app/8。由于macOS系统在独立运行ComfyUI Desktop与Pinokio托管实例时，其配置文件存储机制存在差异，本设计采用统一的重定向拓扑方案8：

1. **Pinokio内置实例路径管理**：在 /Users/YourUsername/Library/Application Support/Pinokio/api/comfy.git/app/（或自定义安装路径）下，定位或创建 extra\_model\_paths.yaml 配置文件8。  
2. **ComfyUI Desktop独立实例路径管理**：在macOS系统默认沙盒路径 \~/Library/Application Support/ComfyUI/ 下定位或创建 extra\_models\_config.yaml 配置文件9。

由于YAML语法对缩进与空白字符极其敏感，配置文件中禁止使用制表符（Tab），必须使用空格进行对齐8。通过在配置文件中定义 base\_path 指向外置硬盘中的统一模型存储根目录，可实现多实例间的模型共享，极大释放Mac本地磁盘空间10：

| 运行平台 (macOS M3 Pro) | 配置文件物理路径 | 配置字段名 | 外置硬盘指向路径示例 |
| :---- | :---- | :---- | :---- |
| **Pinokio ComfyUI 实例** \[cite: 8, 12\] | \~/.pinokio/api/comfy.git/app/extra\_model\_paths.yaml \[cite: 8, 10\] | a111 或 comfyui \[cite: 10\] | base\_path: /Volumes/ExternalSSD/AI\_Models/ \[cite: 10\] |
| **ComfyUI Desktop 实例** \[cite: 9\] | \~/Library/Application Support/ComfyUI/extra\_models\_config.yaml \[cite: 9, 11\] | comfyui\_desktop \[cite: 9\] | base\_path: /Volumes/ExternalSSD/AI\_Models/ \[cite: 11\] |

对于不规范的第三方自定义节点，若其硬编码路径无法正确解析 extra\_model\_paths.yaml 的配置8，本设计在macOS底层使用软链接（Symbolic Link）技术进行强行目录级映射6：

Bash  
\# 导航至Pinokio安装路径下的ComfyUI models目录  
cd \~/Library/Application\\ Support/Pinokio/api/comfy.git/app/models  
\# 移除非空文件夹并建立映射  
rm \-rf checkpoints loras controlnet vae  
ln \-s /Volumes/ExternalSSD/AI\_Models/models/checkpoints ./checkpoints  
ln \-s /Volumes/ExternalSSD/AI\_Models/models/loras ./loras  
ln \-s /Volumes/ExternalSSD/AI\_Models/models/controlnet ./controlnet  
ln \-s /Volumes/ExternalSSD/AI\_Models/models/vae ./vae

### **1.2 M3 Pro 底层加速与显存优化配置**

Apple Silicon的统一内存架构允许CPU与GPU共享内存空间，消除了传统的PCIe显存拷贝时延2。为了最大化榨取M3 Pro芯片的推理效能，ComfyUI在启动时需应用特定的底层显存调度策略2：

* **启动参数微调**：在Pinokio启动配置中，建议将启动参数调整为： python main.py \--gpu-only \--highvram \--force-fp16 其中 \--gpu-only 能够强制常驻物理图形管线，减少CPU到GPU的交换时延；--force-fp16 强制将计算图权重压缩为半精度，防止重型模型（如Flux.1-Dev）在M3 Pro的18GB/36GB统一内存上频繁触发系统物理内存交换（SWAP）导致的卡顿。  
* **GGUF量化卸载**：针对大语言模型与Diffusion Transformer（DiT）模型，引入 ComfyUI-GGUF 插件，将底模量化为 Q4\_K\_S 或 Q8\_0 精度15。这使底模在运行过程中的内存占用大幅降低，从而将更多的高速统一内存留给面部特征提取及超分辨率上采样工作流。

## **2\. 核心生成底座与多模态编码机制（Checkpoints, CLIPs, VAEs, and PhotoMaker）**

在美容美发头像组合工作流中，生成结果不仅需要具备极高的真实质感，更需要在发丝细节上达到无损的微米级呈现。单一的模型架构无法同时解决人像质感、发丝边缘和角色身份（Identity）一致性三大难题，因而系统采用异构多模型联合驱动的架构10。

### **2.1 基础模型选型与 VAE/CLIP 最佳实践**

系统的基础底模和特征编码器按照处理精度和底层算法的不同进行分层组合，具体参数与技术细节如下表所示10：

| 技术模块 | 底层基架 | 推荐模型/权重文件名 | 专属 VAE 选型 | 专属 CLIP / 文本编码器 | 运行特征与技术定位 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **毛发迁移底模** | SD 1.55 | realisticVisionV60\_v60B1.safetensors | 内嵌或搭配 vae-ft-mse-840000-ema-pruned.safetensors | CLIP-ViT-H-14-laion2B-s32B-b79K \[cite: 19\] | 用于运行 StableHair\_ll 管线，其在低维度的毛发流向控制上具备极佳的收敛效率5。 |
| **角色特征保留** | SDXL4 | juggernautXL\_v9RdPhoto2Lightning.safetensors | sdXL\_v10VAEFix.safetensors \[cite: 21\] | CLIP-ViT-L \+ OpenCLIP-ViT-bigG | 配合 InstantID 或 PhotoMaker 执行高保真角色特征注入与姿态控制4。 |
| **超清环境重构** | Flux.1-Dev22 | flux1-dev-fp8.safetensors \[cite: 3, 16\] | ae.safetensors (Flux 官方 VAE) | t5xxl\_fp8\_e4m3fn.safetensors \+ clip\_l.safetensors | 用于基于自然语言指令（ACE++）的智能修复、发色变更与场景无损融合3。 |

### **2.2 PhotoMaker 与多模态面部保留技术解析**

在美容美发组合中，传统的面部特征注入（如单图 IP-Adapter Face）往往会带来严重的“面部粘滞感”——即生成的脸部光影、肤质与周围新生成的头发不协调，显得边缘生硬且立体感缺失24。为了打破这一局限性，本系统设计了 PhotoMaker 与 InstantID 双轨并行的解决方案：

                      \[ 真实真人照片 (多张多角度) \]  
                                    │  
                       \[ PhotoMaker 特征提取器 \]  
                                    │  
                                    ▼  
                     \[ 堆叠身份嵌入 (Stacked ID Embed) \]  
                                    │  
                        ┌───────────┴───────────┐  
                        ▼                       ▼  
            \[ Cross-Attention 交叉注意力 \]    \[ InstantID 关键点对齐 \]  
                        │                       │  
                        └───────────┬───────────┘  
                                    ▼  
                         \[ 最终保真面部潜在特征 \]

* **PhotoMaker 机制**：PhotoMaker 支持输入多张相同角色的多视角照片25，并在 CLIP 的 Token 空间中将这些面部图像的全局特征提取并堆叠为一个统一的“身份嵌入”（Stacked ID Embedding）4。这避免了因单一参考图所包含的角度、光影不全而导致的“侧脸变形”问题26。其与 CLIP 的结合实现了非凡的风格化与超写实头像生成：

![][image2]

* **InstantID 协同控制**：通过提取 14 区面部关键点与深度高维特征向量，InstantID 可以在大角度倾斜（如侧头展示发型）的情况下，强行锁住五官分布比例4，使发型边缘的融合不发生漂移。  
* **语义预处理器增强**：引入 comfyui-ethnicity\_hairstyle\_clip\_encoder 自定义节点，通过外置 CSV 选项动态生成人种、发型和表情的精确词串27。此节点将描述符（如“蓬松卷发”、“美式渐变”）前置附加在正向 CLIP 提示词中，在 Tokenizer 阶段深度干预交叉注意力权重（Cross-Attention Weights），从语义根源上约束毛发的粗细与生长方向27。

## **3\. 图像局部编辑与多轮控制技术（ACE++, ControlNet, StableHair\_ll）**

美容美发任务的本质是局部高质量重绘。如何在保留面部主要身份（ID）的前提下，实现干净的“剥离”与“再生”，是工作流设计的难点。

### **3.1 深度解构 ACE++ 框架与参数微调**

ACE++ 是由阿里巴巴达摩院开源的高阶多模态语义编辑框架，其基于上下文感知的局部填充技术（Context-Aware Content Filling），使用户仅通过简单的自然语言指令，即可对图像局部进行服装替换、发型变更及人脸对齐3。

                        \[ Flux.1-Fill-Dev 基础潜空间 \]  
                                      │  
          \[ 原始图像 Latent \] ──(384通道)──┼──(64通道追加)── \[ 掩码与编辑参考 Latent \]  
                                      │  
                                      ▼  
                        \[ 448通道全调优模型 (FFT) \]

* **模型通道结构设计**：在底座上，ACE++ 基于 Flux.1-Fill-dev22。为了将图像重绘（Repainting）与语义编辑（Editing）两个异构任务完美兼容，ACE++ FFT（Fully Fine-Tuned）模型引入了 64 个额外的通道维度23。这使其在扩散 Transformer 的处理中，输入通道从原始 Flux 填充模型的 384 通道扩展至 448 通道23：

![][image3]  
其中，![][image4] 代表 Flux 原生图像潜空间，![][image5] 专门用于高维语义边界引导23。

* **LoRA 推荐与局限规避**：尽管 FFT 模型在理论上支持更丰富的重绘任务23，但其由于是在 Flux.1-Dev 这种经过强蒸馏（Distilled）的基础模型上进行的后训练（Post-training），训练过程极易表现出不稳定性，在边缘和手部容易产生严重的伪影23。因此，在人像美发替换垂直领域，官方及社区强烈推荐使用特定领域的微调模型——comfyui\_portrait\_lora64.safetensors3。随后的技术演进也表明，多模态编辑的主流重心已逐渐转向基于万网（Wan Series）系列底模的微调23。  
* **Mac 内存策略（max\_seq\_length 调优）**：在 M3 Pro 上运行 ACE++ 节点时，内存开销和生成细节可以通过关键参数 max\_seq\_length 调节23。  
  * 范围设定在 ![][image6] 之间23。  
  * 对于 M3 Pro (18GB 内存)，推荐将其下调至 2048。该设置会在保证发梢语义连续性的前提下，将显存占用降至最低，防止因 VRAM 溢出而导致的生成中断23。对于更高内存（36GB及以上）的设备，可以设为 4096 以换取更高的毛发纹理边缘解析度23。

### **3.2 StableHair\_ll 专属美发重构管线**

在针对常规男女性发型进行精确迁移（如短发变长发、长发去留、Bald-Try-On）时，ComfyUI\_StableHair\_ll 提供了业界极为专业的两阶段生成闭环20：

* **阶段 A：Bald Converter 局部秃头重塑**：加载 hair\_bald\_model.bin 模型，自动检测人眼、额头与头发交界处（发际线），对待替换的发区实施强力剥离并转成无发的秃头过渡图像，为新发型的生成扫清障碍20。  
* **阶段 B：特征迁移与色彩控制**：利用发型提取器（Hair Extractor）提取参考发型的纹理特征20，在潜空间中使用 Latent IdentityNet 进行角色轮廓锁死20。为了防止新生成的头发与原人像的边缘肤色存在过渡色差，本设计在此阶段并联引入 Latent ControlNet，将参考发型的明暗色彩（Chrominance）投影到头皮区域，实现毛发的无缝生长过渡20。  
* **运行物理指标规范**：该节点对于输入的比例及角度有着极为严苛的要求5。两张输入图像必须为完全对齐的正脸人像，且分辨率尺寸（Width / Height）必须保持一致，并严格向下整除至 8 的倍数5。

### **3.3 多重并联 ControlNet 结构约束力场**

在生成具有特定卷度与动态方向的发型时，单纯通过自然语言极易导致发梢在三维空间中产生视觉畸变29。本工作流引入并联的 ControlNet 控制链来构建立体“约束力场”16：

1. **头骨深度约束 (Depth Everything, 权重 ![][image7])**：获取原作者的立体头型骨架信息16，防止生成的新长发刺穿后背、肩膀或下巴。  
2. **柔性边缘引导 (SoftEdge Control, 权重 ![][image8])**：通过获取参考发型的柔性毛茸感边缘29，替代生硬的 Canny 边缘，使新生发梢呈现极佳的松弛感与写实细节29。

下表规范了在美容美发局部替换任务中，各技术模块在 ComfyUI 工作流中的核心参数配置与控制机制：

| 控制模块 | 核心控制参数名 | 生产环境推荐参数/阈值 | 潜空间运算机制 | 失败红线与解决方案 |
| :---- | :---- | :---- | :---- | :---- |
| **StableHair\_ll** \[cite: 20\] | denoise\_strength crop\_size\_alignment | 0.75 True (8倍数对齐) | 基于 Bald-Latent 与 Hair-Embedding 进行二阶段重构20。 | 输入图像非绝对正面或光影差异过大，导致发梢产生色彩色差20。建议加入色彩匹配节点20。 |
| **ACE++ (LORA)** \[cite: 3\] | max\_seq\_length flux\_guidance | 2048 \[cite: 23\] 50.0 \[cite: 3\] | 通过 64 个扩展通道进行语义局部内容填充22。 | 参数高于 4096 会导致 M3 Pro 内存交换引起假死23。限制计算长度以换取稳定性23。 |
| **Depth ControlNet** \[cite: 16\] | strength ending\_step | 0.70 \[cite: 16\] 0.85 | 提取三维几何距离图（Midas/Zoe）约束发梢骨架16。 | 头部扭转角度过大（大于75度）导致深度图畸变33。限制输入头部侧偏角33。 |
| **SoftEdge ControlNet** \[cite: 31\] | strength starting\_step | 0.45 0.0 | 柔性 HED 线条明暗过渡捕捉，指导蓬松细节29。 | 边缘引导过高导致整体画面饱和度过爆（Overcooked）16。将权重上限控制在 0.6 之下16。 |

## **4\. 三维资产重建与动态视频渲染（3D Pack, LivePortrait, AnimateDiff）**

当静态的美容美发头像组合完成后，为了满足全方位的动态展示和多角度发型试戴需求，系统需要升级到三维资产重构与动态微表情合成阶段。

                    \[ 完美融合静态头像 2D 图像 \]  
                                  │  
          ┌───────────────────────┼───────────────────────┐  
          ▼                       ▼                       ▼  
   \[ 3D 资产重构管线 \]     \[ 动作重定向管线 \]      \[ 物理飘动渲染管线 \]  
  (ComfyUI-3D-Pack)         (LivePortrait)          (AnimateDiff)  
          │                       │                       │  
 3D高斯泼溅与多视角色彩  面部关键点与姿态微调     16帧无限上下文平滑  
          │                       │                       │  
          └───────────────────────┬───────────────────────┘  
                                  ▼  
                        \[ 最终三维动态演示空间 \]

### **4.1 基于 ComfyUI-3D-Pack 的发型三维空间重建**

通过部署 ComfyUI-3D-Pack15，本系统支持将生成的 2D 发型无损地转换为 3D 资产，供全角度 3D 头像场景使用34：

* **3D 神经网络重构（TripoSR & InstantMesh）**：将静态 2D 美发头像输入 3DGS（3D Gaussian Splatting）和 NeRF 处理节点34，重构出头部三维拓扑网格（Mesh）与多视角 UV 贴图34。  
* **发丝质感与反射约束**：由于毛发表面存在高度复杂的非各向同性（Anisotropic）光泽，系统接入神经网格渲染器，可生成极具真实的丝绸光泽反射，使发型在 3D 转动时能呈现动态的受光面偏移，打通从 2D 设计到 3D 互动展示的闭环。

### **4.2 基于 LivePortrait 的微表情与姿态对齐**

发型试戴API需要输出角色生动的展示效果。使用 ComfyUI-LivePortraitKJ 节点，能够将洗剪吹展示视频的动作（Driving Video）映射到生成的美发头像（Source Image）上15：

* **自适应防抖平滑（Motion Smoothing）**：为了消除在逐帧动作计算中面部和细微发丝的局部抖动，将 LivePortraitProcess 节点的 relative\_motion\_mode 设置为 source\_video\_smoothed35。该技术基于前向-后向卡尔曼滤波，对转头动作过程中的运动矢幅进行二次曲线平滑，确保输出动作如丝般顺滑35。  
* **高阶面部追踪与调试覆盖（Debug Overlay）**：加载具有强抗噪的 NukeMaxNodes，在提取姿态信息前应用 CLAHE 局部直方图均衡化与自适应高斯模糊，以防止低对比度场景下的颈部姿态丢失18。其内置基于图像梯度投票（Gradient Voting）的瞳孔精准检测算子18，可高精度地追踪视线走向（gaze\_x / gaze\_y），并在生成图中无损重塑逼真的眼球转动与眼神交汇18。

### **4.3 基于 AnimateDiff 的物理发丝飘动合成**

若要在特定的模版中增加如“微风拂面、发梢飘摆”等强物理质感，需并联引入 AnimateDiff 动态合成模块19：

* **上下文窗口融合（Uniform Context Options）**：受制于运动模型原生感受野的限制，传统的动态生成往往只能输出 16 或 24 帧的不连续片段37。本工作流通过引入无上限上下文参数，将 context\_length 设定为 16（运动模型原生推荐帧数），context\_overlap 设定为 4 帧37。这使得前后相邻的动态片段在时序边缘发生 4 帧的平滑差值重叠37：

![][image9]  
其计算逻辑有效消除了多帧拼接时的突跳，呈现完美的物理平滑飘动效果。

* **MotionLoRA 精准形变**：挂载专门针对毛发物理形变训练的 MotionLoRA 权重（如 Pan 和 Zoom）36，利用轻量化的 v3\_sd15\_mm.ckpt 或经典 mm\_sd\_v15\_v2.ckpt 物理运动模型，在 M3 Pro 有限的统一内存空间中实现动态视频的高速渲染36。

## **5\. 生产级 Headless API 架构设计与并发调度**

在美容美发工作流完成测试后，为了将其封装为支持后端调用的高并发 API，需要将 ComfyUI 从可视化前端完全解耦，以无界面的 headless 模式在后台常驻运行38。

                             \[ API 客户端 \]  
                                   │  
                ┌──────────────────┴──────────────────┐  
                ▼                                     ▼  
      \[ POST /upload/image \]                  \[ POST /prompt \]  
      ( 上传人脸/发型参考图 )                  ( 提交更新后的 JSON )  
                │                                     │  
                ▼                                     ▼  
        \[ 保存至 input 目录 \]                  \[ 异步队列排队计算 \]  
                │                                     │  
                └──────────────────┬──────────────────┘  
                                   ▼  
                       \[ WebSocket /ws 通信 \]  
                     ( 实时推送执行进度与节点 ID )  
                                   │  
                                   ▼  
                         \[ GET /view 提取结果 \]

### **5.1 工作流文件解耦与节点寻址机制**

在 ComfyUI 交互面板中完成所有技术调试后，必须启用“开发者模式”以获取能够被后端代码读取的无排版拓扑结构21：

1. **导出 API 格式**：进入 ComfyUI 设置面板（齿轮图标） \-\> 勾选 "Enable Dev Mode options" \-\> 在控制主面板上点击 "Save (API Format)" 按钮，导出 workflow\_api.json 格式文件21。  
2. **提取动态控制槽位（Node ID）**：在导出的 workflow\_api.json 中，排版与渲染坐标等冗余元数据均已被剥离，每个节点都以其物理数字 ID 寻址39。本工作流解析出的核心注入参数对应关系如下表所示21：

| 节点物理 ID (示例) | 节点类型 (class\_type) | 需在 API 调起时动态更新的字段名 | 变量定义与业务数据注入逻辑 |
| :---- | :---- | :---- | :---- |
| **"10"** \[cite: 42\] | LoadImage \[cite: 38\] | image \[cite: 38\] | 注入客户端通过 API 预先上载的真实真人面部图片文件名39。 |
| **"12"** | LoadImage | image | 注入选定的发型模版图片名称39。 |
| **"25"** | CLIPTextEncode \[cite: 43\] | text \[cite: 21\] | 注入发型、发色、蓬松度等修饰提示词（Prompt Travel）21。 |
| **"3"** \[cite: 41\] | KSampler \[cite: 41\] | seed \[cite: 41\] | 生成高精度真随机数作为随机种子，以防止触发节点缓存复用21。 |

### **5.2 完整的 Python 高效 API 调用链路实现**

基于多路异步回调机制，以下 Python 实现展示了如何通过 WebSocket 实时监听生成进度，并下载最终生成的美容美发组合图片21：

Python  
import json  
import random  
import websocket  
import urllib.request  
import urllib.parse

\# 定义全局通信参数  
SERVER\_ADDRESS \= "127.0.0.1:8188"  
CLIENT\_ID \= f"mac\_m3\_pro\_api\_{random.randint(1000, 9999)}"

\# 1\. 向本地 ComfyUI 上传人像及发型图片 \[cite: 21, 42\]  
def upload\_image(file\_path, filename, folder\_type="input", overwrite=True):  
    with open(file\_path, 'rb') as f:  
        file\_data \= f.read()  
      
    \# 构造标准 multipart/form-data 表单 \[cite: 21, 45\]  
    boundary \= "----WebKitFormBoundary7MA4YWxkTrZu0gW"  
    headers \= {'Content-Type': f'multipart/form-data; boundary={boundary}'}  
      
    body \= (  
        f"--{boundary}\\r\\n"  
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\\r\\n'  
        f"Content-Type: image/png\\r\\n\\r\\n"  
    ).encode('utf-8') \+ file\_data \+ (  
        f"\\r\\n--{boundary}\\r\\n"  
        f'Content-Disposition: form-data; name="type"\\r\\n\\r\\n{folder\_type}\\r\\n'  
        f'--{boundary}\\r\\n'  
        f'Content-Disposition: form-data; name="overwrite"\\r\\n\\r\\n{str(overwrite).lower()}\\r\\n'  
        f"--{boundary}--\\r\\n"  
    ).encode('utf-8') \[cite: 21, 45\]  
      
    req \= urllib.request.Request(f"http://{SERVER\_ADDRESS}/upload/image", data=body, headers=headers) \[cite: 21\]  
    with urllib.request.urlopen(req) as res:  
        return json.loads(res.read()) \[cite: 21\]

\# 2\. 动态参数注入并推送生成任务至异步队列  
def queue\_prompt(prompt\_graph):  
    payload \= {"prompt": prompt\_graph, "client\_id": CLIENT\_ID} \[cite: 21, 42\]  
    data \= json.dumps(payload).encode('utf-8')  
    req \= urllib.request.Request(f"http://{SERVER\_ADDRESS}/prompt", data=data, headers={'Content-Type': 'application/json'}) \[cite: 21, 42\]  
    with urllib.request.urlopen(req) as res:  
        return json.loads(res.read()) \[cite: 21\]

\# 3\. 阻塞获取结果并通过 WebSocket 追踪执行步骤  
def run\_hair\_workflow(user\_face\_path, hair\_style\_path, hair\_prompt):  
    \# a. 上传图像获取服务端标准化文件名  
    face\_name \= upload\_image(user\_face\_path, "user\_face.png")\['name'\] \[cite: 21, 46\]  
    hair\_name \= upload\_image(hair\_style\_path, "hair\_ref.png")\['name'\] \[cite: 21\]  
      
    \# b. 加载并更新 workflow\_api.json 模板  
    with open("workflow\_api.json", "r") as f:  
        graph \= json.load(f)  
      
    \# 动态参数覆盖 \[cite: 21, 42\]  
    graph\["10"\]\["inputs"\]\["image"\] \= face\_name \[cite: 42\]  
    graph\["12"\]\["inputs"\]\["image"\] \= hair\_name  
    graph\["25"\]\["inputs"\]\["text"\] \= hair\_prompt \[cite: 21, 42\]  
    graph\["3"\]\["inputs"\]\["seed"\] \= random.randint(10\*\*14, 10\*\*15 \- 1) \# 防止节点缓存  
      
    \# c. 链接 WebSocket 追踪进度  
    ws \= websocket.WebSocket()  
    ws.connect(f"ws://{SERVER\_ADDRESS}/ws?clientId={CLIENT\_ID}") \[cite: 21\]  
      
    prompt\_response \= queue\_prompt(graph) \[cite: 21, 42\]  
    target\_prompt\_id \= prompt\_response\['prompt\_id'\] \[cite: 21, 39, 42\]  
      
    print(f"Task submitted. Prompt ID: {target\_prompt\_id}")  
      
    \# d. 监听 WebSocket 状态消息  
    while True:  
        msg \= json.loads(ws.recv())  
        if msg\['type'\] \== 'executing':  
            data \= msg\['data'\]  
            if data\['node'\] is None and data\['prompt\_id'\] \== target\_prompt\_id: \# 执行链完全终止  
                print("Generation complete\!")  
                break  
        elif msg\['type'\] \== 'progress':  
            data \= msg\['data'\]  
            print(f"Sampling Step Progress: {data\['value'\]}/{data\['max'\]}") \[cite: 39\]  
              
    \# e. 抓取历史结果并拉取生成图像的二进制数据 \[cite: 21, 42\]  
    history\_req \= urllib.request.urlopen(f"http://{SERVER\_ADDRESS}/history/{target\_prompt\_id}") \[cite: 21\]  
    history\_data \= json.loads(history\_req.read()) \[cite: 21\]  
      
    output\_images \= history\_data\[target\_prompt\_id\]\['outputs'\]  
      
    for node\_id, outputs in output\_images.items():  
        if 'images' in outputs:  
            for idx, img in enumerate(outputs\['images'\]):  
                img\_name \= img\['filename'\]  
                sub\_folder \= img.get('subfolder', '')  
                folder\_type \= img.get('type', 'output')  
                  
                \# 请求 /view 端口下载最终图片 \[cite: 21, 42\]  
                query \= urllib.parse.urlencode({"filename": img\_name, "subfolder": sub\_folder, "type": folder\_type}) \[cite: 21\]  
                with urllib.request.urlopen(f"http://{SERVER\_ADDRESS}/view?{query}") as view\_res: \[cite: 21\]  
                    with open(f"result\_{node\_id}\_{idx}.png", "wb") as out\_f:  
                        out\_f.write(view\_res.read()) \[cite: 21\]  
                print(f"Saved: result\_{node\_id}\_{idx}.png")

\# 执行示例  
if \_\_name\_\_ \== "\_\_main\_\_":  
    run\_hair\_workflow("./raw\_face.png", "./ref\_hair.png", "long hair, curly, golden blonde color")

### **5.3 生产级容器沙箱与反向代理安全性设计**

由于 ComfyUI 属于高自由度的节点编辑器，支持加载各种执行 shell 脚本和第三方不规范依赖的自定义节点1。为了在生产环境中安全提供对外服务，必须实施多重安全加固1：

* **Podman / Docker 容器化隔离**：推荐在生产环境中使用 Podman（相较于 Docker，其原生支持无根模式 Rootless）将 ComfyUI 环境和底盘显卡（GPU/MPS）隔离，严格限制其对宿主机文件系统的读写权限，防止由于加载恶意节点导致宿主机被控或被用于加密货币挖掘1。  
* **Nginx 安全网关与 SSL/TLS 升级**：绝不允许将 ComfyUI 的 8188 物理端口直接对公网开放39。必须在宿主机架设反向代理，添加 Token 级别的请求头鉴权（Bearer Authentication），并利用 TLS 将 WebSocket 通信强制提升为安全的 wss:// 通道39：

Nginx  
server {  
    listen 443 ssl;  
    server\_name your.api.domain;

    ssl\_certificate /etc/nginx/ssl/cert.pem;  
    ssl\_certificate\_key /etc/nginx/ssl/key.pem;

    location / {  
        \# 自定义令牌验证机制  
        if ($http\_authorization \!= "Bearer SuperSecretSecureToken\_2026") {  
            return 401;  
        }  
        proxy\_pass http://127.0.0.1:8188;  
        proxy\_http\_version 1.1;  
        proxy\_set\_header Upgrade $http\_upgrade;  
        proxy\_set\_header Connection "upgrade";  
    }  
}

通过这一生产级网关拦截设计，恶意请求将在 Nginx 层被全部丢弃39，确保了 headless ComfyUI 服务在内网高速且无间断运行39。

## **6\. 总结与技术展望**

基于 Mac M3 Pro 统一内存架构与外置硬盘重定向技术，本系统成功打通了从毛发高精分割（SAM 3.1 & BiRefNet）、角色身份保留（PhotoMaker & InstantID）、局部毛发剥离与重组（StableHair\_ll & ACE++）到最终生产级 Headless API 的全流程美容美发头像组合闭环9。  
未来，随着后训练（Post-training）技术的发展，行业的前沿研发方向已表现出显著的迁移态势。针对早期在 Flux 蒸馏底模上运行局部编辑所出现的失真、噪声不匹配及伪影问题23，各大研究机构正深度加速将此类局部微调技术向全新的万网（Wan Series，如 Wan 2.1 / Wan 2.2）视频与图像底模底座上进行平移与升级23。这将为美容美发组合系统带来具有更高物理光影精确度、高细节还原度及原生三维时空连续性的下一代内容生成新体验。

#### **Works cited**

1. PSA: Please secure your ComfyUI instance \- Reddit, [https://www.reddit.com/r/comfyui/comments/1hjnf8s/psa\_please\_secure\_your\_comfyui\_instance/](https://www.reddit.com/r/comfyui/comments/1hjnf8s/psa_please_secure_your_comfyui_instance/)  
2. ComfyUI \- Grokipedia, [https://grokipedia.com/page/ComfyUI](https://grokipedia.com/page/ComfyUI)  
3. ACE++ Face Swap | Instruction-Based Image Editing \- RunComfy, [https://www.runcomfy.com/comfyui-workflows/ace-plus-plus-face-swap](https://www.runcomfy.com/comfyui-workflows/ace-plus-plus-face-swap)  
4. ComfyUI InstantID Faceswapper detailed guide \- RunComfy, [https://www.runcomfy.com/comfyui-nodes/comfyui-instantId-faceswap](https://www.runcomfy.com/comfyui-nodes/comfyui-instantId-faceswap)  
5. lldacing/ComfyUI\_StableHair\_ll \- GitHub, [https://github.com/lldacing/ComfyUI\_StableHair\_ll](https://github.com/lldacing/ComfyUI_StableHair_ll)  
6. Can you run a model from an external drive? : r/comfyui \- Reddit, [https://www.reddit.com/r/comfyui/comments/1s571jf/can\_you\_run\_a\_model\_from\_an\_external\_drive/](https://www.reddit.com/r/comfyui/comments/1s571jf/can_you_run_a_model_from_an_external_drive/)  
7. ComfyUI Alternatives \- Reddit, [https://www.reddit.com/r/comfyui/comments/1mfseoi/comfyui\_alternatives/](https://www.reddit.com/r/comfyui/comments/1mfseoi/comfyui_alternatives/)  
8. FNG needs help\! Noob with a technical question. : r/comfyui \- Reddit, [https://www.reddit.com/r/comfyui/comments/1iby7t3/fng\_needs\_help\_noob\_with\_a\_technical\_question/](https://www.reddit.com/r/comfyui/comments/1iby7t3/fng_needs_help_noob_with_a_technical_question/)  
9. Adding Extra Model Paths · Issue \#1736 · Comfy-Org/desktop \- GitHub, [https://github.com/Comfy-Org/desktop/issues/1736](https://github.com/Comfy-Org/desktop/issues/1736)  
10. Models \- ComfyUI Official Documentation, [https://docs.comfy.org/development/core-concepts/models](https://docs.comfy.org/development/core-concepts/models)  
11. Changing Models Path to External Drive in ComfyUI Desktop | by SophieZ \- Medium, [https://medium.com/@sophie\_62065/changing-models-path-to-external-drive-in-comfyui-desktop-1cd54f731c66](https://medium.com/@sophie_62065/changing-models-path-to-external-drive-in-comfyui-desktop-1cd54f731c66)  
12. A question for the experts: Do you have two Comfy installation? one for experimenting and one for work? : r/comfyui \- Reddit, [https://www.reddit.com/r/comfyui/comments/1j8qzxu/a\_question\_for\_the\_experts\_do\_you\_have\_two\_comfy/](https://www.reddit.com/r/comfyui/comments/1j8qzxu/a_question_for_the_experts_do_you_have_two_comfy/)  
13. fetch models folder from other drive? · Comfy-Org ComfyUI · Discussion \#5015 \- GitHub, [https://github.com/Comfy-Org/ComfyUI/discussions/5015](https://github.com/Comfy-Org/ComfyUI/discussions/5015)  
14. Support InsightFace/PuLID on macOS Apple Silicon · Issue \#13 · utensils/comfyui-nix, [https://github.com/utensils/comfyui-nix/issues/13](https://github.com/utensils/comfyui-nix/issues/13)  
15. ComfyUI-Workflow/awesome-comfyui: A collection of awesome custom nodes for ComfyUI \- GitHub, [https://github.com/ComfyUI-Workflow/awesome-comfyui](https://github.com/ComfyUI-Workflow/awesome-comfyui)  
16. ControlNet ComfyUI workflows \- Stable Diffusion Art, [https://stable-diffusion-art.com/controlnet-comfyui/](https://stable-diffusion-art.com/controlnet-comfyui/)  
17. How to use InstantID to copy faces \- Stable Diffusion Art, [https://stable-diffusion-art.com/instantid/](https://stable-diffusion-art.com/instantid/)  
18. I hope this helps everyone.... : r/comfyui \- Reddit, [https://www.reddit.com/r/comfyui/comments/1t4kkwf/i\_hope\_this\_helps\_everyone/](https://www.reddit.com/r/comfyui/comments/1t4kkwf/i_hope_this_helps_everyone/)  
19. AnimateDiff morphing transition video (ComfyUI) \- Stable Diffusion Art, [https://stable-diffusion-art.com/animatediff-morphing-transition-video-comfyui/](https://stable-diffusion-art.com/animatediff-morphing-transition-video-comfyui/)  
20. ComfyUI\_StableHair\_ll detailed guide | ComfyUI \- RunComfy, [https://www.runcomfy.com/comfyui-nodes/ComfyUI\_StableHair\_ll](https://www.runcomfy.com/comfyui-nodes/ComfyUI_StableHair_ll)  
21. Hosting a ComfyUI Workflow via API \- 9elements, [https://9elements.com/blog/hosting-a-comfyui-workflow-via-api/](https://9elements.com/blog/hosting-a-comfyui-workflow-via-api/)  
22. Alibaba Open Sources ACE++: Zero-Training Character-Consistent Image Generation, [https://comfyui-wiki.com/news/2025-02-10-alibaba-ace-plus-zero-training-image-generation](https://comfyui-wiki.com/news/2025-02-10-alibaba-ace-plus-zero-training-image-generation)  
23. ali-vilab/ACE\_plus \- GitHub, [https://github.com/ali-vilab/ACE\_plus](https://github.com/ali-vilab/ACE_plus)  
24. My workflow for multi-face swap with Reactor, IP adapter, Face ID, Instant ID : r/comfyui, [https://www.reddit.com/r/comfyui/comments/1fip0kj/my\_workflow\_for\_multiface\_swap\_with\_reactor\_ip/](https://www.reddit.com/r/comfyui/comments/1fip0kj/my_workflow_for_multiface_swap_with_reactor_ip/)  
25. IP adapter FaceID vs InstantID : r/StableDiffusion \- Reddit, [https://www.reddit.com/r/StableDiffusion/comments/1agdu29/ip\_adapter\_faceid\_vs\_instantid/](https://www.reddit.com/r/StableDiffusion/comments/1agdu29/ip_adapter_faceid_vs_instantid/)  
26. Using InstantID with ReActor ai for faceswap : r/StableDiffusion \- Reddit, [https://www.reddit.com/r/StableDiffusion/comments/1lt7lst/using\_instantid\_with\_reactor\_ai\_for\_faceswap/](https://www.reddit.com/r/StableDiffusion/comments/1lt7lst/using_instantid_with_reactor_ai_for_faceswap/)  
27. ajbergh/comfyui-ethnicity\_hairstyle\_clip\_encoder \- GitHub, [https://github.com/ajbergh/comfyui-ethnicity\_hairstyle\_clip\_encoder](https://github.com/ajbergh/comfyui-ethnicity_hairstyle_clip_encoder)  
28. ComfyUI-ACE\_Plus \- ComfyUI Cloud \- Comfy.ICU, [https://comfy.icu/extension/ali-vilab\_\_ACE\_plus](https://comfy.icu/extension/ali-vilab__ACE_plus)  
29. \[For Beginners\] Introduction to ComfyUI Portable ControlNet (Canny, SoftEdge, Depth, OpenPose \+ JSON Distribution) \- note, [https://note.com/like\_badger8355/n/n8d37088aedf8?hl=en](https://note.com/like_badger8355/n/n8d37088aedf8?hl=en)  
30. Combining Depth, Color & Canny Preprocessors within ControlNet | Bianca Mueller \- Multidisciplinary Designer, [https://bianca.works/posts/controlnet-secret-sauce-image-wizardry/](https://bianca.works/posts/controlnet-secret-sauce-image-wizardry/)  
31. ControlNet SoftEdge vs. Canny: Tool to Use for Render AI, [https://renderai.app/blog/controlnet-softedge-vs-canny-which-tool-to-use-for-render-ai/](https://renderai.app/blog/controlnet-softedge-vs-canny-which-tool-to-use-for-render-ai/)  
32. My workflow with ControlNet preprocessors to get canny, depth, pose, sketch, etc. images : r/comfyui \- Reddit, [https://www.reddit.com/r/comfyui/comments/1clxfq2/my\_workflow\_with\_controlnet\_preprocessors\_to\_get/](https://www.reddit.com/r/comfyui/comments/1clxfq2/my_workflow_with_controlnet_preprocessors_to_get/)  
33. Crossing the Uncanny Valley With RTX Neural Face Rendering | Game Developers Conference (GDC) 2025 | NVIDIA On-Demand, [https://www.nvidia.com/en-us/on-demand/session/gdc25-gdc1007/](https://www.nvidia.com/en-us/on-demand/session/gdc25-gdc1007/)  
34. ComfyUI Extensions \- Comfy.ICU, [https://comfy.icu/extension/](https://comfy.icu/extension/)  
35. ComfyUI LivePortrait Workflow | Animate Portraits | Vid2Vid \- RunComfy, [https://www.runcomfy.com/comfyui-workflows/comfyui-liveportrait-workflow-animate-portraits-vid2vid](https://www.runcomfy.com/comfyui-workflows/comfyui-liveportrait-workflow-animate-portraits-vid2vid)  
36. AnimateDiff ComfyUI Workflow/Tutorial \- Stable Diffusion Animation \- RunComfy, [https://www.runcomfy.com/tutorials/how-to-use-animatediff-to-create-ai-animations-in-comfyui](https://www.runcomfy.com/tutorials/how-to-use-animatediff-to-create-ai-animations-in-comfyui)  
37. \[GUIDE\] ComfyUI AnimateDiff Guide/Workflows Including Prompt Scheduling \- An Inner-Reflections Guide (Including a Beginner Guide) : r/StableDiffusion \- Reddit, [https://www.reddit.com/r/StableDiffusion/comments/16w4zcc/guide\_comfyui\_animatediff\_guideworkflows/](https://www.reddit.com/r/StableDiffusion/comments/16w4zcc/guide_comfyui_animatediff_guideworkflows/)  
38. GitHub \- SaladTechnologies/comfyui-api, [https://github.com/SaladTechnologies/comfyui-api](https://github.com/SaladTechnologies/comfyui-api)  
39. ComfyUI API: The Complete Developer's Guide (2026) \- Runflow, [https://www.runflow.io/blog/comfyui-api-developer-guide](https://www.runflow.io/blog/comfyui-api-developer-guide)  
40. ComfyUI Account API Key Integration, [https://docs.comfy.org/development/comfyui-server/api-key-integration](https://docs.comfy.org/development/comfyui-server/api-key-integration)  
41. 20 ComfyUI Workflows for Production in 2026 \- Runflow, [https://www.runflow.io/blog/comfyui-workflows-production-ready](https://www.runflow.io/blog/comfyui-workflows-production-ready)  
42. Building a Production-Ready ComfyUI API: A Complete Guide \- ViewComfy, [https://www.viewcomfy.com/blog/building-a-production-ready-comfyui-api](https://www.viewcomfy.com/blog/building-a-production-ready-comfyui-api)  
43. SD3.5 Large Canny ControlNet \- ComfyUI Workflow, [https://comfy.org/workflows/sd3.5\_large\_canny\_controlnet\_example-0bb057fd76e3/](https://comfy.org/workflows/sd3.5_large_canny_controlnet_example-0bb057fd76e3/)  
44. Properties \- ComfyUI Official Documentation, [https://docs.comfy.org/custom-nodes/backend/server\_overview](https://docs.comfy.org/custom-nodes/backend/server_overview)  
45. BiRefNet: Remove Image Background in ComfyUI, [https://docs.comfy.org/tutorials/utility/remove-background-birefnet](https://docs.comfy.org/tutorials/utility/remove-background-birefnet)  
46. SAM 3.1: Segment Anything in ComfyUI, [https://docs.comfy.org/tutorials/utility/video-segment-sam3](https://docs.comfy.org/tutorials/utility/video-segment-sam3)  
47. Free Video: Character Consistency in ComfyUI Using ACE++ \- Single Image Tutorial from Sebastian Kamph | Class Central, [https://www.classcentral.com/index.php/course/youtube-mindblowing-character-consistency-with-ace-one-image-only-427077](https://www.classcentral.com/index.php/course/youtube-mindblowing-character-consistency-with-ace-one-image-only-427077)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAAAZCAYAAADOtSsxAAAFXElEQVR4Xu2YB4glRRCGfyPmnEVds2IOYMQcUDFnEQ9FRUXPgCiYMOAaOUTFM3PmHDBgwLBg4hQD5syJekYEEwZM9V11v9dTO+PbeyunyHzww0x1z0zPVHV19UgtLS0t/TJnNLRMWx4yzRGN/TK36XDTBaaxpkWrzR2WMR1pGjTtENoy05t2NJ1tOlbN91rPdLLpFNNaoa3kYNPHps9Nk00PV5uHcYzpU9Nn8v63y+//kfweWZNM75veM71husi0vEbGUqa7o7FfVjA9bzrKdKjpddMPpl3KTsbm8pc42rSF6QnTbZUe0symO00PmjYxnSD/GBuUnYzj5S+9m2lf07tyx/4d4+Qf7U/TGtWmDtOZ7pP3+cA0Q7VZu6e2CcHO+N6RO2bF0FYHgbNHNPbLkGlMcb6g6TfTj+kYeJFP5B8uM5/pe1WvPcz0hWm2wsZMIMpmTOcryT/Cup0e0jamX+TB0MQZptPk1xKtdWwpnwH0eTO0Ac+h7bLYYOwnbyMwejHRNEs09gPp4lfTH6bFCjvRzWCY/rBTOl+708N52vRYcf6SPAJLtpJfu3E6J5K/6zZPgZnDGEhHTeAAxvGi6Sv5NZFr5UHTywGXxgZjdXnb1/KZ1ASp8+poHA1EAykjR2i2MZiD0jkRx/nSnR4OH5vI5dp55H2uq/Rwp2E/NZ2/Ik9lEZzyeDQWZAeQqrgf6atkLtNN6biXAy6JDfJ0Sds5sSGA8zaNRrnjCdi95GmMFNw3L8jTUE5BvBiDiwvqHcm+sHwB4/iKSg9plWQfn85ZE8i3EaL6rWgsyA4g9f1seqDarEPk7dDLAVeZ5pXfi7GTtr4xnWmavdN7ODPJZ2CcITjvZnkKZBysP3WzbERsLR9kOc0eSTYGW8IijH1l+UJWfugMbdjzgs2MqfvQrB2oiewAoLIhQMqAuEfdWdzLAW/LZyq6wfSs/J5Ni3uG5w8GG05h3GsWtgPVpwPYXDA4Sqwyx1L6MfBFChtkB7B4rp+OL6/06DqACAGil2dEeInJ0ViAA3ZOx9vJ70nkAVP+wnQMvRxQl4KoAmmjFG+CGc/7lDBjvjW9Kq8il5Qv0MuVnUYC0cPm4hoNL99ulA9u8WCn5MTOVOaBHDO9S1ZN9ovTOdUUVVGExY+XaAIH5NKY8ZHK8kwib/OcTD8OAPYbv8sX2ghrHEVHHfubfpLfGz0j3ytMFXz484rz1eS1P2DnxtH7j8rLVXIiu0LSQk41mQ3l156YzidqeKrhelITAdAEDti1OOejc9+NTPcWdujlgKb0cJe8/fzYII9u9kB1kC0WkO9pSN1UlkNlh17wcvkDZU5Sd7OxmXxg23ZanZyuMkOm54pz2Ed+LWUenC4vOcs6mtRGn7GFLcIYy8qHtJc/9BGFHfpxACU5gUF7XQVDab5QNBpLmJ4KNqohZlJZWTaCZ9lQPSl/yJB8USKvMQuAKf+aqhsgPgDTjjo/s7d8RpR7iutVjYZl5c8rd9qUu+xC4xqTYaHD0YPyD5VhqjMG0kOGl+YjsruO8PuEtlgosPbdktomVJumMGC6PxoTA/LrWAMzB8j/KPRkVnna4AZReLCMUhaXSfLNznHy/yhMuchZ8tzMdGXtwJnU6CUsovyroew7V162Ua7WQTRRIrJPQF+q+7K8KOPJvCxfY3LfD023qvsvKOdp3pnnY0P0xZl7avj6B2wQCa46BuT3YBysc1fKn1m3jowaootyk4HGPUEJkcyGhL5Ebx2sGdvLnfFf/7XLukWw1oHD5k/HvEcMtpZRso7+4V8PLVPHONUvyi3TABZ81gbK5JZ/Af6FjYnGlpaWlv8BfwHkjVG9i8C5rgAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAkAAAABPCAYAAAADU3rKAAAT5UlEQVR4Xu2dCbwlR1WHj6io0YDiwmJkhriAK4oaEQUSQcHgjgJicBJjRAQXUBFFmDEQIoq7gEs0AVFQoywqRhESkcWFxQVRBJzBENGwKC5RAZf+cvp469V0v3vvezPz3pv5vt+vfvNuVXffXqpO/euc03ciRERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERkD3DToXxYXym7Ap7Nh/eVsmVu01ecpNhvZMf50KF80VA+ayjv27XJNO81lA+JHMCnIqcN5eZ95XHkvYfy20O5c98gu4IPGMrLh/LxfcMuAPt2r6HcO/I8i4+O3Wnv7jGUZ/eVJym7ud/ISc6XD+UFQ3n3UP53LM/bsMXJz8OGcu1Q/mEsfz+UI0N501j/tKGcEyl4Cu7ReyLv112a+p3kNUN5y1g4bwz+HB80lNdGXivXzLWueh30mRsir/3pXdvx5EcinwUgOv91KG8byvVD+cexvHUo7xzKXcfttsP3DeWfIo9Zx+e73h4pxE4W7hl5z7jOupf8y73lHq/DFw/lb4fyEX3DDnGHofx65HP8/aH87FCuHMpDhnLryH7PudJf/mYobxj/fX3zL2Ol55LIbWu7+vuBQ3lGLMYV5brIe8KYZJsnDuUTYp4zI8fwxzV1nz2UP1mhvGwoVw/ljrnbnmG39Rs5BfieSOX9qUN5/6F8YeSk9lvtRqcQT428/oc2daxOvjpywsew1OoRMfQdcewF0PlD+ci+cg1uFml83xWbryC/bih/Fnn+F3Rtq3DLyHtyogQQBpLJmEkLuP+fMRaut8Q7oo+608fttgPPgWMdisXxf22su/1isz0PfYZr4h7XdR4Z6yjrgjj8xb5yB7hPpLBjgfdRTf1NhnLpUP498lrbSZexUItAtlsG18n2397V461kQULbJzb1txjKE8Z6hNAUrxjKD3V1CLdXR14T13Krofxu5HG+LDKERP2Bse5jcrc9xW7pN3IK8C1D+Z/IgVSw8rgmTl1X5A9EGo/zu3r4icg2RGPxFWPdsRRAvxcbDea6IAwwlKx6EUFzsXXaHx95/vfr2laF1e2JEkCs3r+7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PX5m0YpnCdsMeIDmBBAe3fIIcr54vEv88z30kfrMNTEOHhNH/99lxVb7jcgxBWFDAh9hEVy9gBsccUP45HGRnZ0B8OmRoRcS5vASPXbcnoH87EjX66FxO8CVjQv2wZG/Zlyu6TaUI9JzRqShLoO7Cojzp0R6FI5ECh28Zy14F9qQwDog9AkXVXiEck27wQie01oJ7xR43q6Jo3NhVoUwaIVRgHAbtqEXjniICPm0eXGyHk+KFJtz4cxlIFJYrJID9dzIsB+i4tzIlxL+Ijb+x8J4LdkHu054usKReKMIuT0v0tODvb8uMo3i0ZHP+ZrIvo0AekdkOgHeUMKlbZ8nHYJx1n5vi/1G9gTEcRmYCBZyFlD4rDJQ9SS79dwqpkMCp4//Et44rW0QmQFvC6vKWp0eC+4fG19rPtYgks7rK3cAvFNn9ZVrwBhtxzF/c209eBfmQmOyGtjSq2I6L20VEDN4a/DurBpyRiDhBdqq6GpDYIynqePM5biB/UZEZAn3jeW/YC47A5PtE2N68pP1YIG4FUFAnhceTzx2UwvS4wE5ngciQ2e86bUu9hsRERHZFngbCUEhgE5UsjdvCBLa4nvJHRUREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREZGTm/8DaZqOI+G/LVQAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGYAAAAaCAYAAABFPynYAAAElElEQVR4Xu2ZV4gkVRSGf+Oac1ZwF7MiPph90FHEnAPmBwOKihEDGMecc8RVXMU1RxSzmBVBDLiIKAZMDyooJkRB/T/PLfvunZqxu2elZmfrh4+uPrd7p/qee1Kt1KrVONAcZk8zaLadfknrmlPN3mb+Yg3NZa4qja1mjM42B5gJ5jNzcLJvYM5VOITrKcmea9B8URr71Zpme7NYuTCL6jFzRrq+3zyari80+6dr9I6ZM3u/jrlNo3TMguYS87H5K/GVIozHg/h995ovzQPmHvONec1MMx8qImNS9YUaLWE+Nzun93uYn83RZndzWLIjHHS12USjcMx65j3FH1jJLGK+TeQnYDzocjNRkQ3uNrMlO07Zzkw2hyZbLmrL8+a8wn6r4hCzV6tk9uPMqmYj9emYjc1P6bUSOfNHRQSNVS2nKLwcKiD9diPSDxu4tLkms1OkT0nX15tls7VcpLIr0vWOisjjPt5SOGBRs7o5Kn2mL8csbD41FxT2I80vGjmsmxCnm6h+w0w11yoigAN0Wva5kXS+wjHLaGi3dHt63c/sk675mwepU2/Zm9/MQuZNs0Cy41jua1fFft5ibjSPKNLdDarv2mp1mflBQ79ArtywsDWteRRFmM1cqljrRXRRlWOuLNbuTK/sC10WIrWTqthwxPe/M7MrHDEx2RFOLyNtB/UYMXiYvFidkrGuS82JpbEPnaN6x+xrTldExB2ZHV2kOBDHmk8UHSva3DxnDlR87/hkr7Sbedp8r6hdZQDUihPASdirXBiDWlLRnHCYRqvcMfybtLNs7q/mKUW2qOtEiVJqWdkMzaeIrnkLe9+6WOGYKmSHEwWRUKRjaUpbKu6Dgj8ctLLdKHcMeZ8ooe3dxZycfa4xPahwDEPQf+kldXr3JkSqeN3cNQLX/fvpkVXWGCLgcUUjdJO67+7+Nz2hcAz9dp2YZeg8EKHepGM2U3RfM0IU6JU1fY0hRRE9tLrsC41GY+KH4pgnywXFMPW1WTG9f1ZR2Bi8KMJ5G43DSAEMaLnzNlW0tqSOvB1nE2hvD1fMEt2IDojJfLVyoQ8xx1SOydtlUvuA4hAwsTcm8vaf5g9ziOLHA53E+2aNzkf/cQxdBT07P+ojs1Zae9fspCiYXPMIgutX0jriEQjaRnEiKeIDmb0bbaG4j8XLhR5FK7y8oiYxZ1SieHNvvHII6cAa01nmd0XkMATxbOxhDS2kbEg1cCGGJ76LcCbFl+L5tiJKsJG3XzYnqRMZzAkMXKTPExRPF+ZOa92ISZtDcaZZQZFy+FvdiBrClE7ryvR+n2KG43DQ9aEB86LimRpd2mCyNyLyKk9It9bwLV/pGFIAzQPiR0wxa6frY5Kd9pKTR33iJLKB0xROIWIqehUTOC0tG8t9vaDYTN7PcmID6IwqUZe2MusrnrNVDwKfUaQAWtCbkw29qmgksE/N7ERZP85plfSQIvUQNaQxCj1ikuW0UjhpDHj4R22hZn2gKPJHqPN/GTiBWkVrS8MwMwy3M4UmqP6Ekw4rMRcQQaRFrutaT9JRL7WlVatWrVq1atVqfOpvJ+fbsLWrz1kAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIcAAAAaCAYAAACdH0+XAAAFbElEQVR4Xu2ad+xkUxTHv1i9C6IEQaIH0bsE0Xb1IKKXVaOLXn5EokXNKhtddKIsQnQr+h8kRGf1BBGyWoLgfPbc693f/c2b38yb329iuZ/km5m59819b+4975xzzxupUCj85xljGms607R61gczmy7PGwv/D64yHWta0vSGacbB3RowfZ619cRKcmtcIO8o/KvYz3RPeL+Q6ayqaxqrmW7WCBjH3KaLTB+Z/gr60jRTelBhVLjA9I7padNdpndNb5leMX1qus603j9HV9xtOs20g+kE0zxJH+HmCtMG6tE41jK9aTrKtKxpPtO3QZykMPpsL/cEMMk0e3i/hel00/FyI0nhRkZzmbY1vWiaIfQRapaTG1Vj41jf9GN4jcxpmir3JIXu4O5dQ37DRXXifbc2jQ/v8QgpMVwcJDeCyAfysBH5w7SpaQXTkaGtsXHMa5piOi9rP8L0s2nprL1QD3f4ZNOD8iTxUvnNRchYODmuji1VGQehJeUGuQdf3DQxaceIjks+/2LaW76e15uukV/PT6ar5Td9x1xs+kFDv3SIad2srVDPufJQsGre0QUYV51x3B5etzOdmLSfrMq7E4YwjiWq7mmMUwPPwf6XnOKWvKPQFUz+I3ljAzZXa+NY3nSv3LM8ocE7SELYs6YDTbeZDk/6YGfT46bvTddqqBOoZSf5jmT3vKPQFa/Kk/heSY3jBXlYeMj0jel1uXciDcihrrGRhnqMnrhQbhzr5B0Z5B8fy2PZ9Ajx/in5biyyr9yN98pspvtNiw2jTkiNA0/BZ7aiS5nujAf1i/vkxkGhZDg49oC8sQX8oB3zxgaM1DiRleU1mwiTfkzyuen5SNjZSt4xjBaJX2hDq5yD6yT3Y+4JHX3jUblxsB9uBbWOWFThYjsxDlzhrnljA0ZqnAj7/dQ4cpqejyTweVW1hV4gp2CrCtE4KEyyTrPIdyb8jr5widw4Hss7jG1MX8ldGuDWonGsKK/XnyG/++LEsKX6VZ6csY2LyQ9ulRDGsauENjJsJoB6wCmm88NxUDdOO3YznWPaR+7qgRjM9wmL9EfjWFO+NTw6fG5yvhQS+v3zxgZQ58iNA8bK6xyEx4dNsyZ9owZu7E/T7/KLIrFBZLhvy40gkhoHrg7DAvbOJ4X3WPdzpj1VLRCZNfnKgvJkiqINBSF+KHUUFoNzUv1jLGg1TjvY0/NEEgbkxR/GfE+VMZJjRONgl8YWPu7Suj1fzqLyhDGdryawTeUagJwj5UZ5aKSgdav8N4w6Z5t+k3sQCiVM4APyxUxJjQNPwUJvFtrJRyLPaLB7Plj+jIDQhT6UZ9bwnbx6CEwK27RIPk4dGMEX8sVm/CtNT8rvwsnJcTzKTsMKW75oHNDp+erAMF4z3SRfRLxPJ1XRCIUybiKuGa/xtdyjbxz6WQ/6CC2fyZ/B9IX5TXuZtlJVz8/BCGJCxPOXl+SLTKggW48wyWyN8RjcURPkxoalR8UwRI2Fp7+wh3xRI/k4dTBpGDbhKY7PorDtS8NlbhyHaqhxdHK+dnDuXeQhi9oCY+KRUKc7lukSLJbQw8RPVXXH80SQxeeJILAgeIFN5GGL1ymq3CAVRIo6gOdIjYPtZiQfpx18b3zyGQ+wjOl9Vf9t2FCeQ0UO02Dj6OZ8hQQm/hPTy/JJvkzuLUjCSEqJ7SSVwMKQvZOAzhHa8DS4SgyIci/gUTCySfKnkXgi7mxyD2g1Th0kzVwPIXJAnnACXo1nC9Rn+CcU+RVhBwOgcMVjcQqB0M35CsPAI+LoDcakHfLJjXdshHDVqrrXjnScU2u0dugHagn5lpJrJMkk6aSf1zpaXXehUCgUCoVCoVDoN38DFVIVDw/gJxMAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAAAZCAYAAADQfBuCAAAE50lEQVR4Xu2Yd4glRRCHyxwwIZjFiIqiiBEP0TsToqIohkMxJzBjRgUTKp45Bzz1H7OeqJgVbxVzRkXMrijmHDCH32dN79arN/P2rcouyHzwY3eqe+ZNV3VXV49ZS0tLS0vL/595pf2kM6WDpUU6m4dYRjpQOk3aIrXVMZt0p7RkbhCrSEdJB0hLpLbxYDFpb+k4abXUlllK2i0bA4z3MOlsaf3UVujX540sLz0tHSTtK70ifS9tHTuJDaT3pEOkDaWHpBs7enQzRfpTWjHZeeEHpG2lzcx//9COHmPLmtIz5pNognS9dFtHDx/D6dJz0h/SXZ3NQ+C3j6QjpYnSk9K5HT3693lPBqxz9iwg/Sb9UP0PM0kfSEeUTmJ+6Ttrnnlrmz8jB46XflWaIdh41tdV23jwrnVnBQK5S7hmPHtKa0g/W33gyEjfSqcGG2PCB5sH24CN7POezCj9Yj6DFg12VhM/RuqArarr1Yd6OI9KDyYbkCIfls6y7sDtLH0uzRNs8KK0fbKNBYubv+O6yX6edHGyFZoCd6L5s7ZJ9i/MVzH06/MRucT8JWZONh7CDAMGwfXSQz2cO8wHEe8FZtxO5ntYDtyqle1e830FVpA+te5gjgU4kon0prROZZtTes2a96emwBEcxkb6jwxKn4Xrfnz+jyBNsHTLsr3W/KF5A725si8UbGzs06r/6wIHZXZ9Ix0jPSut19FjbDnB/H1+l843n1TsP000Be5yq19xBA37LMkeyT4fNZuY/8jUYLuvssUAAcVJDAwzaLoNp4CmwJFKX6jaEBt1Xs1NzCddIH0i3W7d6TuyRzb04FIbfh+eTQHWRFPgdjW/P/4uk520WOe/Qp3PR8Xc5iniVmnWYGcG8uCFgw1K4EpRQSkdX7oucKQm0sIN0nbS+1UfKtamgRWYGAScCpQigb+D0l6hT+TKbGiAIuR5aVPpcfP3YR+aGDsFCNzd2Wg+Nu5nf6egA45OVIwEjwmbafJ53+CUe8wHW360cI35YMqeVLilslMVEhz2vEhd4A6XHrPhqpJ97SrzfqSaXmxZKUKwcRSFRBw4qW6fcN3EWtJX0oLVNc7nDPaT9HrplCBw+KqOuczH85J0k3naZAV/HDtV9PJ533DzlHDNAZmzG2DPAYD7zUtYgrC/+aoZlN6pxB7GfawqzjPwhnWW2YVHzAfbizOyoQIHnGNeZOAsnsM5rG6GZ66w+pV5sg1PykyvwGWYCOxdZd+P9PJ5X5wkHZ1sx5qnMphkPghSSaQs8SYutO6AU/bXBY6DPYfyXsTyuY6VzL/scHzpdwZTMdcFjur3R+uumIHAsX1kmChknd2DbZK5DzYKNhjJ5yPCyZ2D9HTzam/APE+zWpgBgBNeNh9kgX2NgW0cbJnLzF8aJxSOl56S5gg2/udMODnYxgr2sS+lZZOdz1UULBkqQ/Y/MkQOKjXAr+ZVOPBZa0C6rnSo6MfnPcFhLGOcm0VpPPtw17+/Jw6a52/2gLekHUN7hDPc2+ZfQ/iSgGOeqNpIHTgE20XSKeafkZht4wXVICmfdMbxhC2A4onzXIEvH5z1PjQfE2LvIvUToAL+udrcR/QnaDHAo/H5fwYvMMH8C0c+040WCh02bsTXi/EG55M9mHQrp7bRspy0g3VX4S0tLS0tLS0tLS0tLf+GvwBfMz4UXoJDwAAAAABJRU5ErkJggg==>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAZCAYAAACmRqkJAAADj0lEQVR4Xu2XaahNURTHlzmzSMbMQ+ZCQuZIEpG5TB988KJkiAglU8oHITNlHpOUeUgyZ8qcofeMZciQhCj+/9Y53j7rnbuPT1fp/OpX766zzrv77LP3WvuKpKSkpKSQwrAfXAgnw2rRy4kUhb3gPNhV9P/9K+rBiXAR7GuuJdECTocTYC1zLSPF4T54CHYR/QcvYQc3yUNdmAtni95/GE6LZGSP7vApnAR7wNNwdyQjMznwBBwE+8AroospkfHwNSzlxLgSH4muLB/l4B04KvhcDH6HN/5kZI8i8IVEX15F+BmOcWJxNIL3YCEnxns/Bte8XIcHTawn/AU7mbhlh+ig3YnmAwxxPmeL/qJjbm3i5+BJE7OMhO9EF4TLTUl4lgqiX7rZxDkIxueYuOUDPBD8XV2iqzjbLBMdM0uKCxcHd4VvN7USvfcorBHEGsM3UnBSIzQUvXGtiTcL4qtN3KW+aM52uBOuh8/gJtHtlG04Do7HNsC9QbyKiVtYL5n3Cc6EV2HnSEYMbBRxE9UkiPsK8FDRnK+waRArKdqAVoVJHjjJ7Jac9EtwcPRyhAGiu8XHMYmfKD4D43wmHyVEazdzKZuIXc0FaC+avMbEwwlkjcsEWz1zbH3ZBb+JFmEfW+FS0TGwCV0W3QlxW205LG2DBm4/jqeqiYcT6GsGPHbxpXPsfJHPRe9hR7cvJEID0URuP5fmQZwDzwSLK3PWmfiGIO4rvpXgYhNjB18Bz0p0G7aDG53Pmdgm+r1hDQvhEY1x3wudCs9Lfhdm3WMp4n22vEUoA39Kwa3aUfTmGSbu0lbiJ5kvg/HhJu4yTjKvCK7Gt/AIPAXvwtqRjHiWiH6v3arH4ReJHlEsDyX/KObCl3nLBi1n4EUT48NzMC2dWGXRFRvCAb0SffMubCjcwr6TPDu2D34XJ3m0JNe+kG6iY+5t4g/gfhNrI7riQ3hciZtAHsh5uPYyTPQNuQ+1RXRiXXLhD1jHifHXByexfPCZ9StPdDVkGzal26LHmRCucjY5nmtDxopONEtNyFzRGswmGMK/eYbk/CQyH94XnXGuqAtS8PzDhsJfHdz2ISy+e0RbPn8HPxE9U5Z1crIJV32eaP2aAh/DEW6CaHlik8hxYnwOnkTew5VwAbwGZzk5ibB78WjCo427vP8GbnVuOW6Nfw13AZ+BTcyeCZNgAxoYWNNcS0lJSUlJSUn5X/gN01u5yBczTL8AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAABmklEQVR4Xu2UPShFYRjHH0KSZKAQJZFEFAvyNRgsNl/jlUUWWUghkuEaKAtiIZSYFBnlcxCTkiSTYrOwUPyfnvfcnvPcc+8u91e/bud/nvOe933u+x6iBH+JZNgJ5+AIzPffjkkb7Ic1MB1WwwHYqmoipMF9eAhb4Ch8gQ26KAYz8Md4TjEmOgjfYIbKeGWPMEVlQUzDO3gNt+EQTNUFmlt4YLJ2ktk1mdwyBUM2DCKbZMANk9e6fNLkFr4fsmEQZSQDrpq80uXLJrdMwDDcg2fwCBb5Khz8hwcNWOHyXZNbxuENzHHXXfAddkQqHPUkA66Y3HvRjskteSTt1zzDJ5IjE6GUZMA1HYIqly+Z3JJkA3BB8myJDjPhN0W3qJGkeMzkmgKSY7Fo8lOSZ3myPk7glcn6SIr5pHvkknTAo5ykZl1lzAP8pIDz1As/SGbosUkyAQ33/gsWq+wYFqrrOpKX8yYJZBbew2G4BS9hlq9CNgZ/BbjdHs0k3ViA8/DV/cb9ovAO6iHZ8lHLjgNvCH6mm/yrTZDgP/ALUGBQg3k4/GIAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,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>