"""有道ocr
"""
import base64
import json

import requests

from utils.AuthV3Util import addAuthParams
from ocr_json2text_line import OCRJsonToTextLine

# 您的应用ID
APP_KEY = '57de4a67883a784c'
# 您的应用密钥
APP_SECRET = 'MW3xKi21eLXyGSHOLAHVhTb7bTwM4jqz'

# 待识别图片路径, 例windows路径：PATH = "C:\\youdao\\media.jpg"
PATH = '2_dsk.jpg'


def createRequest():
    '''
    note: 将下列变量替换为需要请求的参数
    取值参考文档: https://ai.youdao.com/DOCSIRMA/html/%E6%96%87%E5%AD%97%E8%AF%86%E5%88%ABOCR/API%E6%96%87%E6%A1%A3/%E9%80%9A%E7%94%A8%E6%96%87%E5%AD%97%E8%AF%86%E5%88%AB%E6%9C%8D%E5%8A%A1/%E9%80%9A%E7%94%A8%E6%96%87%E5%AD%97%E8%AF%86%E5%88%AB%E6%9C%8D%E5%8A%A1-API%E6%96%87%E6%A1%A3.html
    '''
    lang_type = 'zh-CHS'
    detect_type = '10012' #按行识别：10012
    angle = '0' # 是否进行360角度识别  0：不识别，1：识别。默认不识别（0）
    column = 'onecolumn' # 是否按多列识别	false	onecolumn：按单列识别；columns：按多列识别。默认按单列识别
    rotate = 'donot_rotate' # 是否需要获得文字旋转角度 donot_rotate：不需要旋转，返回angle倾斜角度，可自行旋转；rotate：根据angle旋转，不返回angle倾斜角度。默认旋转
    doc_type = 'json'
    image_type = '1' # 目前只支持Base64：1

    # 数据的base64编码
    img = readFileAsBase64(PATH)
    data = {'img': img, 'langType': lang_type, 'detectType': detect_type, 'angle': angle,
            'column': column, 'rotate': rotate, 'docType': doc_type, 'imageType': image_type}

    addAuthParams(APP_KEY, APP_SECRET, data)

    header = {'Content-Type': 'application/x-www-form-urlencoded'}
    res = doCall('https://openapi.youdao.com/ocrapi', header, data, 'post')

    if res is not None:
        # 解析JSON响应
        json_response = json.loads(str(res.content, 'utf-8'))

        # 转换为文本
        converter = OCRJsonToTextLine()
        text_content = converter.convert_json_to_text(json_response)

        # 保存文本文件
        output_filename = PATH.replace('.jpg', '.txt').replace('.png', '.txt')
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(text_content)

        print(f"OCR识别完成，文本文件已保存为: {output_filename}")
        print("\n转换结果:")
        print(text_content)

        # 同时保存原始JSON结果
        json_filename = PATH.replace('.jpg', '_ocr.json').replace('.png', '_ocr.json')
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_response, f, ensure_ascii=False, indent=2)

        print(f"\n原始JSON结果已保存为: {json_filename}")
    else:
        print("OCR请求失败")


def doCall(url, header, params, method):
    if 'get' == method:
        return requests.get(url, params)
    elif 'post' == method:
        return requests.post(url, params, header)
    return None


def readFileAsBase64(path):
    f = open(path, 'rb')
    data = f.read()
    return str(base64.b64encode(data), 'utf-8')


# 网易有道智云通用OCR服务api调用demo
# api接口: https://openapi.youdao.com/ocrapi
if __name__ == '__main__':
    createRequest()
