# Paper Reader

一个简洁的arXiv论文阅读工具，帮助研究人员跟踪最新论文并生成摘要分析。

## 功能特点

- 自动抓取arXiv最新论文
- 生成论文关键问题分析(QA)
- 分类展示论文卡片
- 支持按序号追踪阅读进度
- 响应式设计，适配不同设备

## 安装与配置

1. 克隆仓库：
```bash
git clone https://github.com/your-repo/paper_reader.git
cd paper_reader
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 复制环境变量文件并配置：
```bash
cp .env.example .env
```
编辑`.env`文件设置您的配置：
```
# Flask配置
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=True

# LLM配置
LLM_API_URL=http://your-llm-api-url
LLM_MODEL_NAME=your-model
LLM_API_KEY=your-api-key
```

## 使用说明

1. 启动服务：
```bash
python server.py
```

2. 运行爬虫获取最新论文：
```bash
python crawler.py
```

3. 访问 `http://localhost:8000` 查看论文列表

4. 点击分类查看详细论文卡片

## 项目结构

```
paper_reader/
├── arxiv/            # 论文数据存储
├── static/           # 静态资源
├── templates/        # HTML模板
├── .env              # 环境配置
├── .gitignore
├── crawler.py        # 论文爬取脚本
├── server.py         # 主服务程序
└── README.md
