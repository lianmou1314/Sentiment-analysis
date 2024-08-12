from flask import Flask, request, render_template, redirect, url_for, session
import requests
import json
from bs4 import BeautifulSoup
import re
import random
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置一个密钥用于session加密

# 设置api调用密钥
API_KEY = "AFjZINkuAXFRfnvBAlKoBj0v"
SECRET_KEY = "TXNz7MClhlihE4HZ9JYRv7ZMNkpfOUVO"

# 模拟用户数据库
USERS = {
    'user1': 'password1',
    'user2': 'password2'
}

# 获得上传路由的token
def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))
#调用评论观点抽取api
def analyze_comments(comments):
    url = "https://aip.baidubce.com/rpc/2.0/nlp/v2/comment_tag?charset=UTF-8&access_token=" + get_access_token()
    payload = json.dumps({
        "text": comments,
        "type": 9  # 此处选择类型9
    })
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()

# 上传路由
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            comments = []
            csv_reader = csv.reader(file.read().decode('utf-8').splitlines())
            header = next(csv_reader)  # 跳过标题行
            if 'content' not in header:
                return "上传的csv数据集文件中必须有包含的评论列", 400
            content_index = header.index('content')  # 定义评论列名为“content”
            for row in csv_reader:
                if len(row) > content_index:  # 确保该行有足够的列
                    comments.append(row[content_index])
            comments_text = "\n".join(comments)
            result = analyze_comments(comments_text)
            positive_comments = set()
            negative_comments = set()
            for item in result.get('items', []):
                comment_str = f"{item['prop']}: {item['adj']} - {item['abstract']}"
                if item['sentiment'] == 2:  # 2 表示积极情绪
                    positive_comments.add(comment_str)
                elif item['sentiment'] == 0:  # 0 表示消极情绪
                    negative_comments.add(comment_str)
            return render_template('result_pinglun.html', positive_comments=positive_comments, negative_comments=negative_comments)
        else:
            return "未找到文件，请选择要上传的文件", 400
    return render_template('upload.html')

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS:
            return "用户名已存在", 400
        USERS[username] = password
        return redirect(url_for('login'))
    return render_template('register.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "登录失败", 401
    return render_template('login.html')

# 分析URL路由
@app.route('/crawling', methods=['GET', 'POST'])
def crawling():
    if request.method == 'POST':
        url = request.form['url']
        api_type = request.form['api_type']
        show_text = request.form.get('show_text', False)
        text = get_html(url)
        result = get_emotion(text, api_type)
        if result:
            if api_type == 'sentiment':
                sentiment_text = "积极" if result['sentiment'] == 2 else ("中性" if result['sentiment'] == 1 else "消极")
                return render_template('result.html', text=text if show_text else None, result=result, sentiment_text=sentiment_text)
            elif api_type == 'emotion':
                return render_template('result_emotion.html', text=text if show_text else None, result=result)
        else:
            return "情感分析失败", 500
    return render_template('crawling.html')

# 分析直接输入的文本路由
@app.route('/input', methods=['GET', 'POST'])
def input_text():
    if request.method == 'POST':
        text = request.form['text']
        api_type = request.form['api_type']
        result = get_emotion(text, api_type)
        if result:
            if api_type == 'sentiment':
                sentiment_text = "积极" if result['sentiment'] == 2 else ("中性" if result['sentiment'] == 1 else "消极")
                return render_template('result.html', text=None, result=result, sentiment_text=sentiment_text)
            elif api_type == 'emotion':
                return render_template('result_emotion.html', text=None, result=result)
        else:
            return "情感分析失败", 500
    return render_template('input.html')

# 教程使用说明界面
@app.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

# 预定义的User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko) Version/9.1.2 Safari/601.7.7",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
]

# 将text按照lenth长度分为不同的几段
def cut_text(text, lenth):
    textArr = re.findall('.{' + str(lenth) + '}', text)
    textArr.append(text[(len(textArr) * lenth):])
    return textArr  # 返回多段值

def get_emotion(data, api_type):
    # 定义百度API情感分析的token值和URL值
    token = '24.7dfc12283b63985bdc6bd19c33d0c39c.2592000.1723607279.282335-94742082'
    if api_type == 'sentiment':
        url = 'https://aip.baidubce.com/rpc/2.0/nlp/v1/sentiment_classify?charset=UTF-8&access_token={}'.format(token)
    elif api_type == 'emotion':
        url = 'https://aip.baidubce.com/rpc/2.0/nlp/v1/emotion?access_token={}'.format(token)
    else:
        return None

    if len(data.encode()) < 2048:
        new_each = {'text': data}  # 将文本数据保存在变量new_each中，data的数据类型为string
        new_each = json.dumps(new_each)
        res = requests.post(url, data=new_each)  # 利用URL请求百度情感分析API
        res_text = res.text  # 保存分析得到的结果，以string格式保存
        result = res_text.find('items')  # 查找得到的结果中是否有items这一项
        if result != -1:  # 如果结果不等于-1，则说明存在items这一项
            json_data = json.loads(res.text)
            if api_type == 'sentiment':
                confidence = json_data['items'][0]['confidence']  # 得到置信度
                negative = json_data['items'][0]['negative_prob']  # 得到消极指数值
                positive = json_data['items'][0]['positive_prob']  # 得到积极指数值
                sentiment = json_data['items'][0]['sentiment']  # 得到情感类别
                return {
                    'confidence': confidence,
                    'positive': positive,
                    'negative': negative,
                    'sentiment': sentiment
                }
            elif api_type == 'emotion':
                emotions = json_data['items']
                return {
                    'emotions': emotions
                }
        else:
            return None
    else:
        print("文章切分")
        data = cut_text(data, 1500)  # 如果文章字节长度大于1500，则切分
        if api_type == 'sentiment':
            sum_positive = 0.0  # 定义积极指数值总合
            sum_negative = 0.0  # 定义消极指数值总和
            for each in data:  # 遍历每一段文字
                new_each = {'text': each}  # 将文本数据保存在变量new_each中
                new_each = json.dumps(new_each)
                res = requests.post(url, data=new_each)  # 利用URL请求百度情感分析API
                res_text = res.text  # 保存分析得到的结果，以string格式保存
                result = res_text.find('items')
                if result != -1:
                    json_data = json.loads(res.text)  # 如果结果不等于-1，则说明存在items这一项
                    positive = json_data['items'][0]['positive_prob']  # 得到积极指数值
                    negative = json_data['items'][0]['negative_prob']  # 得到消极指数值
                    sum_positive += positive  # 积极指数值加和
                    sum_negative += negative  # 消极指数值加和
            sentiment = 2 if sum_positive > sum_negative else (1 if sum_positive == sum_negative else 0)
            return {
                'confidence': None,
                'positive': sum_positive,
                'negative': sum_negative,
                'sentiment': sentiment
            }
        elif api_type == 'emotion':
            emotions = []
            for each in data:
                new_each = {'text': each}  # 将文本数据保存在变量new_each中
                new_each = json.dumps(new_each)
                res = requests.post(url, data=new_each)  # 利用URL请求百度情感分析API
                res_text = res.text  # 保存分析得到的结果，以string格式保存
                result = res_text.find('items')
                if result != -1:
                    json_data = json.loads(res.text)  # 如果结果不等于-1，则说明存在items这一项
                    emotions.extend(json_data['items'])
            return {
                'emotions': emotions
            }

def get_html(url):
    headers = {
        'User-Agent': random.choice(USER_AGENTS)  # 随机选择一个User-Agent
    }  # 模拟浏览器访问
    response = requests.get(url, headers=headers)  # 请求访问网站
    response.encoding = 'utf-8'  # 手动指定编码格式为utf-8
    html = response.text  # 获取网页源码
    soup = BeautifulSoup(html, 'lxml')  # 初始化BeautifulSoup库,并设置解析器
    a = soup.select('p')
    text = ""
    for i in a:
        text += i.text
    return text

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
