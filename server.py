from flask import Flask, render_template, jsonify
import os
import json
import markdown2
from urllib.parse import unquote
from datetime import datetime
import re
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)


# 将URL字符串转换为可点击的HTML链接的实用函数
def make_clickable(val):
    """将URL字符串转换成可点击的HTML链接。"""
    return f'<a href="{val}" target="_blank">{val}</a>'


# 清除内容中的特定IP地址的实用函数
def clear_content(text):
    if text and isinstance(text, str):
        if "43.138.103.5" in text:
            text = re.sub(r"^.*$", r"抱歉，作者暂时没有显卡可用。", text)
    return text


def get_latest_json_files(base_path):
    """获取每个分类目录下的最新JSON文件"""
    latest_files = []
    for folder in sorted(os.listdir(base_path)):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            json_files = sorted(
                [f for f in os.listdir(folder_path) if f.endswith(".json")],
                reverse=True
            )
            if json_files:
                latest_file = os.path.join(folder_path, json_files[0])
                date_str = json_files[0].split('_')[0]
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                latest_files.append(
                    (f"{folder}-{formatted_date}", os.path.relpath(latest_file, base_path)))
    return latest_files

def count_file_rows(path, filepath):
    """计算JSON文件中的记录数"""
    if "置顶说明" in filepath:
        return 999
    if "秘钥发布" in filepath:
        return 888
    with open(path, 'r', encoding='utf-8') as f:
        return len(json.load(f))

@app.route("/")
def index():
    """主页面的路由，列出包含'new'的最新JSON文件"""
    base_path = "./arxiv"
    latest_files = get_latest_json_files(base_path)
    
    # 添加行数并排序
    latest_files = [
        (folder, filepath, count_file_rows(os.path.join(base_path, filepath), filepath))
        for folder, filepath in latest_files
    ]
    latest_files.sort(key=lambda x: x[2], reverse=True)

    return render_template("index.html", 
                         files=latest_files,
                         current_date=datetime.now().strftime("%Y-%m-%d"))


def generate_html_table(data):
    """生成特殊文件的HTML表格"""
    html = '<table class="min-w-full divide-y divide-gray-200 shadow-sm rounded-lg">'
    html += '<thead class="bg-gray-50"><tr>'
    for key in data[0].keys():
        html += f'<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{key}</th>'
    html += '</tr></thead><tbody class="bg-white divide-y divide-gray-200">'
    
    for item in data:
        html += '<tr>'
        for key, value in item.items():
            if key == "说明":
                value = value.replace("\n", "<br>") if value else ""
                value = markdown2.markdown(value) if value else ""
                html += f'<td class="px-6 py-4 whitespace-nowrap" style="width:80%;max-width:800px">{value}</td>'
            else:
                html += f'<td class="px-6 py-4 whitespace-nowrap">{value}</td>'
        html += '</tr>'
    
    html += '</tbody></table>'
    return html

def process_paper_data(data):
    """处理论文数据"""
    papers = []
    for item in data:
        papers.append({
            "标题": item.get("标题", ""),
            "作者": ", ".join(str(item.get("作者", "")).split(",")[:3]),
            "摘要": item.get("摘要", ""),
            "QA": item.get("QA", ""),
            "链接": item.get("链接", "")
        })
    return papers

@app.route("/file/<path:filename>")
def file_content(filename):
    """展示文件内容的路由"""
    filename = unquote(filename).strip()
    path = os.path.join("./arxiv", filename)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "置顶说明" in path or "秘钥发布" in path:
            html = generate_html_table(data)
        else:
            papers = process_paper_data(data)
            print(f"Loaded {len(papers)} papers from {filename}")
            html = render_template('paper_cards.html', papers=papers)
            
        return jsonify(html=html)
        
    except Exception as e:
        print(f"Error loading {filename}: {str(e)}")
        return jsonify(html="")


# 启动Flask应用
if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 8010)),
        debug=os.getenv("FLASK_DEBUG", "True") == "True"
    )
