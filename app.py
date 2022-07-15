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
    "aspectRatio": "16:9",
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
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
              {{
                "type": "text",
                "text": "暱稱",
                "color": "#aaaaaa",
                "size": "sm",
                "flex": 1
              }},
              {{
                "type": "text",
                "text": "{name}",
                "wrap": true,
                "color": "#666666",
                "size": "sm",
                "flex": 5
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

def query_car(number):
    records = getsheet()
    all_bubble = []
    for data in records:
        if int(data['車號']) == int(number):
            img_id = data['上傳圖片'].split("=")[-1]
            img_url = "https://drive.google.com/file/d/{}/view".format(img_id)
            rs = requests.get(img_url)
            print(rs.content)
            soup = BeautifulSoup(rs.content, 'html.parser')
            meta = soup.find("meta", property="og:image")
            img_src = meta["content"]
            print(img_src)
            if not img_src:
                return None
            bubble_msg = bubble.format(img_src=img_src, number=data['車號'], name=data['名稱'], line_id=data['LINE上顯示名稱'], place=data['常出沒地點'])
            all_bubble.append(bubble_msg)
    if all_bubble:
        carousel_msg = carousel.format(bubble=",".join(all_bubble))
        json_final = json.loads(carousel_msg)
        print(json_final)
        return json_final
    else:
        return None

def register_car():
    buttons_template_message = TemplateSendMessage(
        alt_text='註冊車牌',
        template=ButtonsTemplate(
            title='CX30 中區車友交流群 - 車牌登記表單',
            text='目前已更改註冊方式, 請自行填Google表單註冊車牌.\n注意!!上傳的圖片無法自行修改, 如需修改請洽版主/機器人作者\n目前透過google帳號管制人數, 避免表單外流. 沒有google帳號者, 可以找版主/機器人作者協助',
            actions=[
                URITemplateAction(
                    label='點此開啟表單',
                    uri='https://forms.gle/9N1VFcpbFz8FivkXA'
                )
            ]
        )
    )

    return buttons_template_message

def unregister_car():
    TextSendMessage(text="如果重複註冊, 導致有多筆資料. 請洽版主or機器人作者進行修改")

    return TextSendMessage    

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)

    req_msg = str(event.message.text).strip()
        
    if req_msg.startswith("++") and req_msg[2:6].isnumeric():
        reply_msg = register_car()
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith(("C", "c")) and req_msg[1:5].isnumeric():
        number = req_msg[1:5]
        ret = query_car(number)
        if ret is not None:
            reply_msg = FlexSendMessage('query car result', ret)
        else:
            reply_msg = TextSendMessage(text="查詢車牌【{}】:\n尚無車主註冊".format(number))
        line_bot_api.reply_message(event.reply_token, reply_msg)
        return 0

    if req_msg.startswith("--") and req_msg[2:6].isnumeric():
        reply_msg = unregister_car()
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
