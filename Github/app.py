import asyncio
from .bot import build_bot
from .config import Config

async def main():
    config = Config.from_env()
    bot = build_bot(config)
    await bot.start()
    try:
        await asyncio.Event().wait()
    finally:
        await bot.stop()

def run():
    asyncio.run(main())
