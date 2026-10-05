import asyncio
from .config import Config

def run():
    Config.from_env()
    asyncio.run(asyncio.sleep(0))
