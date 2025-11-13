# Agno智能剪辑系统 - 快速开始

## 前置条件

### 1. 获取API密钥

#### Google Gemini API密钥（必需）

1. 访问：https://aistudio.google.com/app/apikey
2. 使用Google账号登录
3. 点击"Create API Key"
4. 复制生成的密钥（格式: `AIzaSy...`）

**免费配额**：每天1500次请求，每分钟15次

#### DeepSeek API密钥（可选，用于完整工作流）

1. 访问：https://platform.deepseek.com/
2. 注册并登录
3. 进入"API Keys"页面创建密钥
4. 复制密钥（格式: `sk-...`）

**成本**：¥1-2/百万tokens，极低成本

### 2. 配置环境变量

编辑项目根目录的 `.env` 文件：

```bash
# Gemini API密钥（必需）
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# DeepSeek API密钥（可选）
DEEPSEEK_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 3. 安装依赖

```bash
pip install agno python-dotenv rich google-generativeai
```

## 快速测试

### 测试1：单Agent视频分析（5分钟）

测试ContentAnalyzer（内容分析专家）的视频分析能力。

```bash
# 准备测试视频（或使用你自己的视频）
export TEST_VIDEO="/Users/niko/Desktop/7537292399417658639.mp4"

# 运行测试
python test_agno_real_video.py
```

**预期结果**:
```
🧪 ContentAnalyzerAgent 真实视频测试
======================================================================

🔄 上传视频到Google AI...
🔄 等待视频处理...
✅ 视频处理完成

✅ 视频分析成功！
======================================================================

📊 分析结果:
   - 视频ID: test_desktop_video
   - 时长: 58.2秒
   - 分辨率: 576x1024
   - 帧率: 30
   - 时间轴片段: 6个
   - 关键时刻: 4个
   - 语音转录: 有

🎯 关键时刻:
   1. [12.5s] 视觉✓ 音频✓ 潜力:0.95
      特写镜头配合强调语气
```

**如果成功**，继续测试2；**如果失败**，检查：
- GEMINI_API_KEY是否正确配置
- 网络是否可以访问Google服务
- 视频文件是否存在且格式正确（mp4/mov/avi等）

### 测试2：完整四Agent工作流（10分钟）

测试完整的专家团队协作流程。

```bash
python test_agno_with_desktop_video.py
```

**预期结果**:
```
🧪 Agno智能剪辑Agent系统测试
======================================================================

Step 1/4: 📹 ContentAnalyzer 分析视频内容...
✅ Step 1 完成: 识别6个时间轴片段，4个关键时刻

Step 2/4: 🎨 CreativeStrategist 生成创意策略...
✅ Step 2 完成: 目标平台=抖音，叙事角度=悬念式

Step 3/4: 🔧 TechnicalPlanner 制定执行计划...
✅ Step 3 完成: 5个剪辑点，3种转场效果

Step 4/4: ✅ QualityReviewer 质量评审...
✅ Step 4 完成: 综合评分8.5/10，病毒潜力0.78

🎉 完整工作流测试成功！
======================================================================
```

## 常见问题

### Q1: 提示"GEMINI_API_KEY未设置"

**解决方案**：
1. 检查`.env`文件是否存在且包含 `GEMINI_API_KEY=...`
2. 确保密钥格式正确（`AIzaSy`开头）
3. 重启测试脚本

### Q2: 提示"Video input is currently unsupported"

**原因**：代码使用了OpenRouter而不是Google原生API

**解决方案**：
- 已在最新版本修复
- 拉取最新代码：`git pull origin main`

### Q3: 视频上传后卡在"等待视频处理..."

**原因**：视频文件过大或网络慢

**解决方案**：
- 等待时间正常：<1分钟（<100MB），1-3分钟（100MB-1GB）
- 如果超过5分钟，检查网络连接
- 尝试使用更小的视频文件

### Q4: DeepSeek API报错

**临时方案**：只测试ContentAnalyzer（测试1），跳过完整工作流
**长期方案**：注册DeepSeek账号获取API密钥（5分钟完成）

## 下一步

- [ ] 阅读完整文档：`docs/AGNO_AGENT_SYSTEM.md`
- [ ] 尝试你自己的视频
- [ ] 调整Agent参数（temperature、model等）
- [ ] 集成到自动剪辑Pipeline

## 获取帮助

- 查看详细文档：`docs/AGNO_AGENT_SYSTEM.md`
- 查看示例代码：`test_agno_real_video.py`
- GitHub Issues：提交问题反馈
