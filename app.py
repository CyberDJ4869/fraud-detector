from flask import Flask, request, jsonify
import joblib
import jieba
import os
from flask_cors import CORS  # 添加CORS支持
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 启用跨域支持

# 检查模型文件是否存在
if not os.path.exists('model/rf_model.pkl') or not os.path.exists('model/vectorizer.pkl'):
    raise FileNotFoundError("模型文件不存在，请先运行train_model.py训练模型")

# 加载模型和向量器
logger.info("加载模型和向量器...")
model = joblib.load('model/rf_model.pkl')
vectorizer = joblib.load('model/vectorizer.pkl')
logger.info("模型加载完成")

# 文本预处理函数
def preprocess_text(text):
    if isinstance(text, str):
        words = jieba.cut(text)
        return ' '.join(words)
    return ''

# 添加后处理函数，基于关键词增强识别能力
def post_process(text, prediction):
    """
    对模型预测结果进行后处理，增强诈骗检测能力。
    """

    # 强制判定词（只要出现就判定为诈骗）
    force_fraud_keywords = [
        "打款", "转账", "账户", "银行卡", "支付密码",
        "验证码", "冻结账户", "资金安全", "汇款"
    ]

    # 组合关键词（两个同时出现才判定诈骗）
    fraud_patterns = [
        ["老师", "被撞"], 
        ["中奖", "领取"],
        ["贷款", "额度"],
        ["账户", "打钱"],
        ["银行卡", "转账"],
        ["冻结", "验证"],
        ["紧急", "转账"]
    ]

    text = text.lower()

    # 1. 检查强制关键词，只要出现直接判定诈骗
    for keyword in force_fraud_keywords:
        if keyword in text:
            return 1

    # 2. 检查关键词组合
    for pattern in fraud_patterns:
        if all(pat in text for pat in pattern):
            return 1

    # 3. 保留模型原有预测
    return prediction

# 健康检查端点
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "message": "诈骗检测服务运行正常"
    })

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    # 处理预检请求
    if request.method == 'OPTIONS':
        return '', 200
        
    # 处理POST请求
    try:
        start_time = time.time()
        logger.info(f"收到预测请求，来源: {request.remote_addr}")
        
        data = request.get_json()
        
        if not data or 'text' not in data:
            logger.warning("请求格式错误，缺少'text'字段")
            return jsonify({"error": "请求格式错误，需要包含'text'字段"}), 400
            
        # 获取文本
        text = data['text']
        logger.info(f"预测文本: {text[:20]}...")
        
        # 预处理
        processed_text = preprocess_text(text)
        
        # 向量化
        text_vec = vectorizer.transform([processed_text])
        
        # 预测
        prediction = model.predict(text_vec)[0]
        result = int(prediction)
        
        # 使用后处理增强结果
        final_result = post_process(text, result)
        
        # 如果后处理改变了结果，记录日志
        if final_result != result:
            logger.info(f"后处理调整: 原始预测={result}, 最终结果={final_result}")
        
        # 计算响应时间
        elapsed_time = time.time() - start_time
        logger.info(f"预测完成，结果: {final_result}, 耗时: {elapsed_time:.2f}秒")
        
        # 返回结果
        return jsonify({"result": final_result})
        
    except Exception as e:
        logger.error(f"预测过程中发生错误: {str(e)}", exc_info=True)
        return jsonify({"error": f"预测过程中发生错误: {str(e)}"}), 500

# 添加一个快速测试路由
@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        "result": 1,
        "message": "这是一个测试响应"
    })

if __name__ == '__main__':
    logger.info("启动Flask服务...")
    # 设置线程模式，提高并发处理能力
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True) 