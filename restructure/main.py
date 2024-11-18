from connect import connect_mt5
from scheduler import scheduler_main
import asyncio

async def main():
    result = await connect_mt5()
    if result:
        await scheduler_main()
    else:
        print("Failed to connect.")

if __name__ == '__main__':
    asyncio.run(main())
