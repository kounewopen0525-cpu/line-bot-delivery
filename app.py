"""
LINE公式アカウント 自動配信システム
- 友達追加 → 1通目（ウェルカムメッセージ）
- 「続き」受信 → 2通目（Brain誘導メッセージ）
"""

import os
import threading
import time
import urllib.request
from flask import Flask, request, abort, render_template
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
)

from messages import WELCOME_MESSAGE, CONTINUATION_MESSAGE

load_dotenv()

app = Flask(__name__)

# LINE API設定
configuration = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhookエンドポイント"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature")
        abort(400)

    return "OK"


def send_reply_or_push(api_client, reply_token, user_id, messages):
    """reply_message を試し、失敗したら push_message にフォールバック"""
    line_bot_api = MessagingApi(api_client)
    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=messages)
        )
        app.logger.info("Reply sent to %s", user_id)
    except Exception as e:
        app.logger.warning("Reply failed (%s), falling back to push_message", e)
        line_bot_api.push_message(
            PushMessageRequest(to=user_id, messages=messages)
        )
        app.logger.info("Push sent to %s", user_id)


@handler.add(FollowEvent)
def handle_follow(event):
    """友達追加イベント → 1通目を送信"""
    with ApiClient(configuration) as api_client:
        send_reply_or_push(
            api_client,
            event.reply_token,
            event.source.user_id,
            [TextMessage(text=WELCOME_MESSAGE)],
        )
    app.logger.info("Sent welcome message to user: %s", event.source.user_id)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """メッセージ受信 → 「続き」なら2通目を送信"""
    user_text = event.message.text.strip()

    if user_text == "続き":
        with ApiClient(configuration) as api_client:
            send_reply_or_push(
                api_client,
                event.reply_token,
                event.source.user_id,
                [TextMessage(text=CONTINUATION_MESSAGE)],
            )
        app.logger.info("Sent continuation message to user: %s", event.source.user_id)


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/guide")
def guide():
    return render_template("guide.html")


@app.route("/brain")
def brain():
    return render_template("brain.html")


@app.route("/screencast")
def screencast():
    return render_template("screencast.html")


@app.route("/animation")
def animation():
    return render_template("animation.html")


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック用エンドポイント"""
    return "OK"


def keep_alive():
    """10分ごとに自分自身の/healthを叩いてRenderのスリープを防止"""
    url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("BASE_URL")
    if not url:
        return  # ローカル開発時はスキップ
    health_url = f"{url.rstrip('/')}/health"
    while True:
        time.sleep(600)  # 10分
        try:
            urllib.request.urlopen(health_url, timeout=10)
        except Exception:
            pass


# Render上でのみkeep-aliveスレッドを起動
if os.environ.get("RENDER"):
    threading.Thread(target=keep_alive, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
