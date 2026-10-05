from pyrogram import filters
from ..buttons import start, start_text

def register(app):
    @app.on_message(filters.command("start"))
    async def handle_start(client, message):
        await message.reply_text(start_text(), reply_markup=start())
    return handle_start
