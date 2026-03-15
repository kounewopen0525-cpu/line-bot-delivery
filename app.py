"""
LINE公式アカウント 自動配信システム
- 友達追加 → 1通目（ウェルカムメッセージ）
- 「続き」受信 → 2通目（Brain誘導メッセージ）
"""

import os
from flask import Flask, request, abort
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
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


@handler.add(FollowEvent)
def handle_follow(event):
    """友達追加イベント → 1通目を送信"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=WELCOME_MESSAGE)],
            )
        )
    app.logger.info("Sent welcome message to user: %s", event.source.user_id)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """メッセージ受信 → 「続き」なら2通目を送信"""
    user_text = event.message.text.strip()

    if user_text == "続き":
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=CONTINUATION_MESSAGE)],
                )
            )
        app.logger.info("Sent continuation message to user: %s", event.source.user_id)


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック用エンドポイント"""
    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
