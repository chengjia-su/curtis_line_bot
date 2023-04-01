import requests
import re
import random
import configparser
import os
import os.path
import psycopg2
import json
from urllib.request import urlopen
from bs4 import BeautifulSoup
from flask import Flask, request, abort, render_template, url_for, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from imgurpython import ImgurClient
import pygsheets

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

carousel ='''
{{
  "type": "carousel",
  "contents": [{bubble}]
}}
'''

bubble = '''
{{
  "type": "bubble",
  "hero": {{
    "type": "image",
    "url": "{img_src}",
    "size": "full",
    "aspectRatio": "20:13",
    "aspectMode": "cover",
    "action": {{
      "type": "uri",
      "uri": "{img_src}"
    }}
  }},
  "body": {{
    "type": "box",
    "layout": "vertical",
    "contents": [
      {{
        "type": "text",
        "text": "{number:04d}",
        "weight": "bold",
        "size": "xl"
      }},
      {{
        "type": "box",
        "layout": "vertical",
        "margin": "lg",
        "spacing": "sm",
        "contents": [
          {{
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
              {{
                "type": "text",
                "text": "群組",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              }},
              {{
                "type": "text",
                "text": "{group}",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5,
                "offsetStart": "xl"
              }}
            ]
          }},
          {{
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
              {{
                "type": "text",
                "text": "Line名稱:",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              }},
              {{
                "type": "text",
                "text": "{line_id}",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5,
                "offsetStart": "xl"
              }}
            ]
          }},
          {{
            "type": "box",
            "layout": "vertical",
            "contents": [
              {{
                "type": "text",
                "text": "出沒地點:",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              }},
              {{
                "type": "text",
                "text": "{place}",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5,
                "offsetStart": "xl"
              }}
            ]
          }}
        ]
      }}
    ]
  }}
}}
'''
register_msg = '''
{
  "type": "bubble",
  "body": {
    "type": "box",
    "layout": "vertical",
    "spacing": "md",
    "action": {
      "type": "uri",
      "uri": "https://linecorp.com"
    },
    "contents": [
      {
        "type": "text",
        "text": "註冊車牌",
        "size": "xl",
        "weight": "bold"
      },
      {
        "type": "separator"
      },
      {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
          {
            "type": "box",
            "layout": "baseline",
            "contents": [
              {
                "type": "text",
                "text": "註冊方式改為填寫Google表單",
                "weight": "bold",
                "margin": "sm",
                "flex": 0
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "contents": [
              {
                "type": "text",
                "text": "點選下方按鈕開啟表單",
                "weight": "bold",
                "margin": "sm",
                "flex": 0
              }
            ]
          }
        ]
      },
      {
        "type": "separator"
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "注意!",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "1. 上傳圖片後無法自行更改",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "2. 避免重複填寫",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "3. 照片請放自己愛車照",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "車牌數字需入鏡(英文可遮蔽)",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "separator"
      },
      {
        "type": "text",
        "text": "需要登入google帳號為了管控人數"
      },
      {
        "type": "text",
        "text": "避免圖片塞爆雲端空間"
      },
      {
        "type": "text",
        "text": "無google帳號者可找機器人作者協助"
      }
    ]
  },
  "footer": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "button",
        "style": "primary",
        "color": "#905c44",
        "margin": "xxl",
        "action": {
          "type": "uri",
          "label": "點擊開啟表單",
          "uri": "https://forms.gle/yPG6EYcvNFhEfQ6cA"
        }
      }
    ]
  }
}
'''

help_msg = '''
{
  "type": "bubble",
  "body": {
    "type": "box",
    "layout": "vertical",
    "spacing": "md",
    "action": {
      "type": "uri",
      "uri": "https://linecorp.com"
    },
    "contents": [
      {
        "type": "text",
        "text": "小幫手使用說明",
        "size": "xl",
        "weight": "bold"
      },
      {
        "type": "separator"
      },
      {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
          {
            "type": "box",
            "layout": "baseline",
            "contents": [
              {
                "type": "text",
                "text": "小幫手功能是用來查詢車友車牌",
                "weight": "bold",
                "margin": "sm",
                "flex": 0
              }
            ]
          },
          {
            "type": "box",
            "layout": "baseline",
            "contents": [
              {
                "type": "text",
                "text": "查看看車友是否註冊過",
                "weight": "bold",
                "margin": "sm",
                "flex": 0
              }
            ]
          }
        ]
      },
      {
        "type": "separator"
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "用法:",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "輸入「C+車號」查詢車牌",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "例如: c5656",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "輸入「++」進行註冊",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "box",
        "layout": "baseline",
        "contents": [
          {
            "type": "text",
            "text": "填完表單即完成註冊",
            "weight": "bold",
            "margin": "sm",
            "flex": 0,
            "color": "#ff0000"
          }
        ]
      },
      {
        "type": "separator"
      },
      {
        "type": "text",
        "text": "如果有任何使用上問題"
      },
      {
        "type": "text",
        "text": "不要害羞直接提問"
      },
      {
        "type": "text",
        "text": "大家都很熱情的!"
      }
    ]
  },
  "footer": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "button",
        "style": "primary",
        "color": "#905c44",
        "margin": "xxl",
        "action": {
          "type": "message",
          "label": "點擊開始註冊!",
          "text": "++"
        }
      }
    ]
  }
}
'''

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("SECRET"))

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        app.logger.error(e)
        abort(400)

    return 'ok'

def getsheet():
    gc = pygsheets.authorize(service_account_env_var = 'GDRIVE_API_CREDENTIALS')
    survey_url = os.environ['SHEET_URL']
    sh = gc.open_by_url(survey_url)

    wk1 = sh[0]
    records = wk1.get_all_records()
    return records

def get_img_url(input_url):
    target_str = ""
    print(input_url)
    for sub_str in input_url.split(',"'):
        if "https" in sub_str and "viewer" in sub_str:
            target_str = sub_str[:-1]
            break
    print(target_str)
    img_url = "{}=w1200-h630-p".format(target_str.split("=")[0])

def query_car(number):
    records = getsheet()
    all_bubble = []
    for data in records:
        if int(data['車號']) == int(number):
            img_id = data['顯示照片'].split("=")[-1]
            img_url = "https://drive.google.com/file/d/{}/view".format(img_id)
            rs = requests.get(img_url)
            # print(rs.content)
            soup = BeautifulSoup(rs.content, 'html.parser')
            meta = soup.find("meta", property="og:image")
            if meta:
                img_src = meta["content"]
            else:
                try:
                    html_str = rs.content.decode("utf-8")
                    m = re.search(r'itemJson.+]', html_str)
                    img_src = get_img_url(m.group())
                except Exception as e:
                    print(e)
                    img_src = "https://lh4.googleusercontent.com/5P0TRsFBU2vXIBwQVZARwnHdnUNkP0VveAN4nA_KJn9BYA8jRDG8oJvs8ymZuiDqIBI=w1200-h630-p"
            #print(img_src)
            if not img_src:
                print("img_src = {}".format(img_src))
                img_src = "https://lh4.googleusercontent.com/5P0TRsFBU2vXIBwQVZARwnHdnUNkP0VveAN4nA_KJn9BYA8jRDG8oJvs8ymZuiDqIBI=w1200-h630-p"
            img_src = img_src.replace("=w1200-h630-p", "=w2400")
            bubble_msg = bubble.format(img_src=img_src, number=data['車號'], group=data['所在群組(可多選)'], line_id=data['Line名稱'], place=data['常出沒地點'])
            all_bubble.append(bubble_msg)
    if all_bubble:
        carousel_msg = carousel.format(bubble=",".join(all_bubble))
        json_final = json.loads(carousel_msg)
        #print(json_final)
        return json_final
    else:
        return None

def register_car():
    json_final = json.loads(register_msg)
    return json_final

def dump_usage_msg():
    json_final = json.loads(help_msg)
    return json_final

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)

    req_msg = str(event.message.text).strip()
        
    if req_msg.startswith("++"):
        ret = register_car()
        reply_msg = FlexSendMessage('註冊車牌表單', ret)
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith(("C", "c")) and req_msg[1:5].isnumeric():
        number = req_msg[1:5]
        ret = query_car(number)
        if ret is not None:
            reply_msg = FlexSendMessage('查詢車牌結果', ret)
        else:
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n尚無車主註冊".format(number))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("--"):
        reply_msg = TextSendMessage(text="如果重複註冊, 導致有多筆資料. 請洽機器人作者進行修改")
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("?小幫手"):
        ret = dump_usage_msg()
        reply_msg = FlexSendMessage('小幫手說明', ret)
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0
        
"""
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    print("package_id:", event.message.package_id)
    print("sticker_id:", event.message.sticker_id)
    # ref. https://developers.line.me/media/messaging-api/sticker_list.pdf
    sticker_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 21, 100, 101, 102, 103, 104, 105, 106,
                   107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125,
                   126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 401, 402]
    index_id = random.randint(0, len(sticker_ids) - 1)
    sticker_id = str(sticker_ids[index_id])
    print(index_id)
    sticker_message = StickerSendMessage(
        package_id='1',
        sticker_id=sticker_id
    )
    line_bot_api.reply_message(
        event.reply_token,
        sticker_message)
"""

if __name__ == '__main__':
    app.run()
