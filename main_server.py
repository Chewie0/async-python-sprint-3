import random
import asyncio


async def func():
    r = random.random()
    await asyncio.sleep(r)
    return r


async def value():
    result = await func()
    print(result)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(value())
    loop.close() 