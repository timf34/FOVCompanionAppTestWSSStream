import asyncio, json, time, math, websockets
from websockets.server import WebSocketServerProtocol
from aiohttp import web   # <-- new

MAX_X, MAX_Y = 102, 65

def build_figure8_points():
    center_y = MAX_Y // 2
    left_center_x = MAX_X // 3
    right_center_x = (2 * MAX_X) // 3
    radius_x = max(6, min(24, MAX_X // 5))
    radius_y = max(6, min(20, MAX_Y // 3))
    pts, steps = [], 72
    clamp = lambda v, lo, hi: max(lo, min(hi, v))

    for i in range(steps):
        a = (2 * math.pi * i) / steps
        x = int(round(left_center_x + radius_x * math.cos(a)))
        y = int(round(center_y     + radius_y * math.sin(a)))
        pts.append((clamp(x,0,MAX_X), clamp(y,0,MAX_Y)))

    for i in range(1, 12 + 1):
        t = i / 12
        x = int(round((1 - t) * left_center_x + t * right_center_x))
        pts.append((clamp(x,0,MAX_X), center_y))

    for i in range(steps):
        a = (2 * math.pi * i) / steps
        x = int(round(right_center_x + radius_x * math.cos(a)))
        y = int(round(center_y      + radius_y * math.sin(a)))
        pts.append((clamp(x,0,MAX_X), clamp(y,0,MAX_Y)))

    for i in range(1, 12 + 1):
        t = i / 12
        x = int(round((1 - t) * right_center_x + t * left_center_x))
        pts.append((clamp(x,0,MAX_X), center_y))

    return pts

FIG8_POINTS = build_figure8_points()

async def handler(websocket):
    print(f"Client connected from {websocket.remote_address}")

    async def ping_client():
        try:
            while websocket.open:
                await websocket.ping()
                await asyncio.sleep(20)
        except websockets.ConnectionClosed:
            pass

    ping_task = asyncio.create_task(ping_client())

    try:
        idx, total = 0, len(FIG8_POINTS)
        while True:
            x, y = FIG8_POINTS[idx % total]
            print(f"Sending coords: x={x}, y={y}, t={time.time():.3f}")
            await websocket.send(json.dumps({"x": x, "y": y, "t": time.time()}))
            idx += 1
            await asyncio.sleep(0.2)  # ~5Hz
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        ping_task.cancel()

# --- New HTTP endpoint ---
async def http_index(request):
    return web.Response(
        text="<h1>✅ FOV WebSocket server is alive</h1><p>Try connecting to <code>wss://stream.fov.ie/</code></p>",
        content_type="text/html"
    )

async def main():
    # Start WebSocket server
    ws_server = await websockets.serve(handler, "0.0.0.0", 8765)
    print("WebSocket server running on ws://0.0.0.0:8765")

    # Start tiny HTTP server (on 8080 so it doesn’t clash)
    app = web.Application()
    app.router.add_get("/", http_index)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("HTTP status page running on http://0.0.0.0:8080")

    # Keep running forever
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
