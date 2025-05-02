import feedparser
import datetime
import pytz
import time
import json
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
from llm_tools import LLM

# Load environment variables
load_dotenv()

# 原始分类数据，包含了不同学科的分类编码和描述
# raw_cls = """
# astro-ph.CO - 宇宙学和非银河系天体物理学
# q-fin.CP - 计算金融
# q-fin.MF - 数学金融
# q-fin.RM - 风险管理
# q-fin.GN - 一般金融
# cs.GT - 计算机科学中的博弈论
# eess.SY - 电气工程与系统科学中的系统与控制
# econ.EM - 经济学中的计量经济学
# econ.GN - 经济学中的一般经济学
# econ.TH - 经济学中的经济理论
# cs.AI - 人工智能
# cs.CL - 计算与语言
# cs.CV - 计算机视觉与模式识别
# cs.LG - 机器学习
# cs.GL - 通用文献
# cs.SY - 系统与控制
# cs.NE - 神经与进化计算
# cs.RO - 机器人学
# """

raw_cls = """
astro-ph.CO - 宇宙学和非银河系天体物理学
cs.AI - 人工智能
cs.CL - 计算与语言
cs.CV - 计算机视觉与模式识别
cs.LG - 机器学习
"""

# 将原始分类数据分割成列表，每个元素都是一个包含编码和描述的列表
classes = [cls.strip().split(" - ") for cls in raw_cls.strip().split("\n")]

# 论文摘要分析的模板
# paper_mask = """Based on the provided abstract of the paper, output the answer under each question. Please strictly follow the template format. The asterisks (**) in the template are for bolding, and they must be retained in the output:

# **1. What is the problem this paper is trying to solve?**

# **2. What is it adding to the literature?**

# **3. What's their result?**

# """

paper_mask = """根据提供的论文摘要，在每个问题下输出答案。请使用HTML格式回答：

<h2><strong>1. 这篇论文试图解决什么问题？</strong></h2><br>
{answer1}<br>

<h2><strong>2. 它为文献贡献了什么新内容？</strong></h2><br>
{answer2}<br>

<h2><strong>3. 他们的研究结果是什么？</strong></h2><br>
{answer3}<br>
/no-think
"""

# 初始化LLM工具
llm = LLM(
    os.getenv("LLM_API_URL"),
    model_name=os.getenv("LLM_MODEL_NAME"),
    api_key=os.getenv("LLM_API_KEY"),
    history_length=0,
    mask=None,
)

# Rate limiting and retry configuration
MAX_RETRIES = 3
RATE_LIMIT = 5  # requests per second
MIN_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds

# 获取当前的UTC时间和星期几
utc_now = datetime.datetime.now(pytz.utc)
weekday = utc_now.weekday()  # Monday=0, Sunday=6

# 检查过去24小时的数据
hours_to_check = 24

# 格式化日期范围
today_utc = utc_now.strftime("%Y%m%d")
last_day_utc = (utc_now - datetime.timedelta(hours=hours_to_check)).strftime("%Y%m%d")


# 处理arXiv条目的函数
def process_entry(entry, llm):
    entry_id = entry.id  # 提取条目的ID
    title = entry.title
    authors = ", ".join(author.name for author in entry.authors)
    summary = entry.summary
    
    # 带重试机制的LLM调用
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # 速率控制
            if attempt > 0:
                delay = min(MIN_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                time.sleep(delay)
                
            qs = llm(paper_mask + summary)  # 使用LLM处理摘要
            break
        except Exception as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed for {entry_id}: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                qs = f"Error processing: {str(last_error)}"
                print(f"Max retries reached for {entry_id}, skipping...")

    link = entry.link
    # 提取并格式化更新日期
    updated_date = datetime.datetime.strptime(
        entry.published, "%Y-%m-%dT%H:%M:%SZ"
    ).strftime("%Y-%m-%d")
    return entry_id, title, authors, summary, qs, link, updated_date


# 遍历所有分类
for cls, name in classes:
    # 构建查询URL
    url = f"http://export.arxiv.org/api/query?search_query=cat:{cls}+AND+submittedDate:[{last_day_utc}+TO+{today_utc}]&start=0&max_results=500&sortBy=submittedDate&sortOrder=descending"
    feed = feedparser.parse(url)  # 解析feed

    # 构建文件路径（只使用分类号）
    folder_path = f"./arxiv/{cls}"
    json_file_path = f"{folder_path}/{today_utc}_{cls}.json"

    # 如果文件夹不存在，则创建
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # 加载或创建文章文件
    data = []
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 保留现有条目不做修改

    # 初始化新条目计数器
    new_entries_count = 0
    # 记录已存在的ID
    existing_ids = {entry['ID'] for entry in data}

    # 使用线程池处理条目
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for entry in feed.entries:
            entry_id = entry.id
            if entry_id not in existing_ids:
                futures.append(executor.submit(process_entry, entry, llm))
                # 速率控制
                if len(futures) % RATE_LIMIT == 0:
                    time.sleep(1)

        # 添加进度跟踪
        total_new = len(futures)
        processed = 0
        for future in concurrent.futures.as_completed(futures):
            processed += 1
            print(f"Processing {processed}/{total_new} ({processed/total_new:.1%})")
            
            result = future.result()
            entry_id = result[0]

            # 将结果转换为字典并添加到数据中
            try:
                entry_dict = {
                    'ID': result[0],
                    '标题': result[1],
                    '作者': result[2],
                    '摘要': result[3],
                    'QA': result[4],
                    '链接': result[5],
                    '更新日期': result[6]
                }
                data.append(entry_dict)
                new_entries_count += 1
            except Exception as e:
                print(f"添加 {result[-1]} 时失败: {e}")

    # 保存文章文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 输出保存或更新的文件信息
    if new_entries_count > 0:
        print(
            f"JSON文件 '{json_file_path}' 已保存或更新，包含 {new_entries_count} 篇新论文。"
        )
    else:
        print(f"JSON文件 '{json_file_path}' 没有新论文需要更新。")
