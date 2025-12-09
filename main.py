import os
from fastapi import FastAPI, Request, Header, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

from commands import (
    handle_add,
    handle_remove,
    handle_view,
    handle_count,
    handle_admin_add,
    handle_admin_remove,
    handle_admin_list
)

load_dotenv()

app = FastAPI()

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    # Get LINE display name
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except Exception:
        display_name = user_id[:8]

    lower = text.lower()
    is_admin = (user_id == ADMIN_USER_ID)

    # Default: no reply (bot stays silent)
    reply = None

    # --- Admin commands ---
    if lower.startswith("@adminadd") or lower.startswith("@adminremove") or lower.startswith("@list"):
        if not is_admin:
            # If you want *no* response for non-admin, just remove this line
            reply = "⚠️ 這個指令只有管理員可以使用。"
        elif lower.startswith("@adminadd"):
            reply = handle_admin_add(text)
        elif lower.startswith("@adminremove"):
            reply = handle_admin_remove(text)
        else:  # @list
            reply = handle_admin_list(text)

    # --- Normal user commands ---
    elif lower.startswith("@add"):
        reply = handle_add(user_id, display_name, text)
    elif lower.startswith("@remove"):
        reply = handle_remove(user_id, text)
    elif lower.startswith("@view"):
        reply = handle_view(user_id)
    elif lower.startswith("@count"):
        reply = handle_count(text)

    # If no known command matched, reply stays None → bot sends no reply
    if reply is None:
        return

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )