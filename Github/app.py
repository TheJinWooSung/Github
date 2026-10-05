import asyncio
import uvicorn
from .bot import build_bot
from .config import Config

async def main():
    config = Config.from_env()
    bot = build_bot(config)
    await bot.start()
    port = config.port
    server = uvicorn.Server(uvicorn.Config(bot.web, host=config.host, port=port, log_level="info"))
    web_task = asyncio.create_task(server.serve())
    try:
        await asyncio.Event().wait()
    finally:
        server.should_exit = True
        await web_task
        await bot.stop()

def run():
    asyncio.run(main())
