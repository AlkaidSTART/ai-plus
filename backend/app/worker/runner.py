"""worker 主循环骨架：DB 轮询发现待运行任务，租约 + fencing 版本防重复执行。

P0 单 worker、受限 ASIN 并发；Redis 仅做可选唤醒通知，不做必选依赖。
"""

import asyncio
import signal

POLL_INTERVAL_S = 2.0
LEASE_TTL_S = 60


async def poll_once() -> bool:
    """轮询一次并尝试领取任务；未实现前直接返回 False（空轮询）。"""
    await asyncio.sleep(0)
    return False


async def main() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
    except NotImplementedError:
        pass  # Windows 不支持 add_signal_handler，依赖 KeyboardInterrupt
    while not stop.is_set():
        await poll_once()
        await asyncio.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(main())
