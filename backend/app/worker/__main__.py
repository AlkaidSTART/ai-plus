"""worker 进程入口：python -m app.worker。"""

from app.worker.runner import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
