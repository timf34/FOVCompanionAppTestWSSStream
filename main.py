import asyncio, json, time, math, websockets, os
from websockets.server import WebSocketServerProtocol
from aiohttp import web

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

# ----- WebSocket handler -----
async def handler(websocket):
    print(f"Client connected from {websocket.remote_address}")

    # (Optional) One-time hello so clients know grid/fps/etc.
    hello = {
        "type": "hello",
        "version": 1,
        "name": "Test Stream — Figure-8 demo",
        "sport": "generic",
        "grid": {"max_x": MAX_X, "max_y": MAX_Y},
        "fps": 5
    }
    try:
        await websocket.send(json.dumps(hello))
    except Exception as e:
        print("Failed to send hello:", e)

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
            payload = {"type":"pos","x": x, "y": y, "t": time.time()}
            await websocket.send(json.dumps(payload))
            idx += 1
            await asyncio.sleep(0.2)  # ~5Hz
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        ping_task.cancel()

# ----- HTTP handlers -----
async def http_index(request):
    return web.Response(
        text="<h1>✅ FOV WebSocket server is alive</h1><p>WS at <code>wss://stream.fov.ie/</code><br/>JSON at <code>/api/streams.json</code></p>",
        content_type="text/html"
    )

async def http_streams(request):
    # Allow overriding host via env if you ever move this
    public_host = os.environ.get("PUBLIC_WSS_HOST", "stream.fov.ie")
    directory = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "streams": [
            {
                "id": "test-figure8",
                "title": "Test Stream — Figure-8 demo",
                "url": f"wss://{public_host}/",
                "status": "test",
                "sport": "generic",
                "venue": "Demo Field",
                "fps": 5,
                "grid": {"max_x": MAX_X, "max_y": MAX_Y}
            }
            # Add live entries here later
        ]
    }
    body = json.dumps(directory).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=15, stale-while-revalidate=60",
        "Access-Control-Allow-Origin": "*"  # safe: read-only JSON
    }
    return web.Response(body=body, headers=headers)

async def main():
    # WS server (8765)
    ws_server = await websockets.serve(handler, "0.0.0.0", 8765)
    print("WebSocket server running on ws://0.0.0.0:8765")

    # HTTP server (8080)
    app = web.Application()
    app.router.add_get("/", http_index)
    app.router.add_get("/api/streams.json", http_streams)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("HTTP server running on http://0.0.0.0:8080")

    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
