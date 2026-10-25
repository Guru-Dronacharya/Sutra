import asyncio

async def test():
    print("INSIDE COROUTINE DIRECTLY!")
    return "SUCCESS"

loop = asyncio.new_event_loop()
res = loop.run_until_complete(test())
print("FINISHED LOOP RUN:", res)
