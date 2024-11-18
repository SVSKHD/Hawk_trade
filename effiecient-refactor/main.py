from config import symbols_config
from utils import runBot
import asyncio

async def main():
    await runBot()

# Run the main loop
if __name__ == "__main__":
    asyncio.run(main())