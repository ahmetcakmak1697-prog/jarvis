import asyncio
import websockets

async def main():
    uri = "ws://127.0.0.1:8000/ws/chat"
    try:
        async with websockets.connect(uri) as ws:
            try:
                await ws.send('{"message":"yetkisiz test"}')
                msg = await ws.recv()
                print("UNEXPECTED_OPEN:", msg)
            except websockets.exceptions.ConnectionClosed as e:
                print(f"A2 unauthorized closed: code={e.code}")
    except Exception as e:
        print("A2 unauthorized exception:", type(e).__name__, str(e))

asyncio.run(main())
