#!/usr/bin/env python3
"""Small localhost WebSocket event source for DeskPet UI testing."""

import asyncio
import base64
import hashlib
import json
from datetime import datetime, timezone

HOST = "127.0.0.1"
PORT = 8765
STATES = ("idle", "walk", "drink", "rest", "bark")
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def frame(payload: bytes) -> bytes:
    size = len(payload)
    if size < 126:
        return bytes([0x81, size]) + payload
    return bytes([0x81, 126]) + size.to_bytes(2, "big") + payload


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        lines = request.decode("latin1").split("\r\n")
        if not lines[0].startswith("GET /events "):
            writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            return
        headers = dict(line.split(": ", 1) for line in lines[1:] if ": " in line)
        key = headers.get("Sec-WebSocket-Key")
        if not key:
            writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            return
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        writer.write(("HTTP/1.1 101 Switching Protocols\r\n"
                      "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
        await writer.drain()
        print("DeskPet connected")
        index = 0
        while True:
            payload = json.dumps({"state": STATES[index % len(STATES)],
                                  "confidence": 0.99,
                                  "timestamp": datetime.now(timezone.utc).isoformat()}).encode()
            writer.write(frame(payload))
            await writer.drain()
            index += 1
            await asyncio.sleep(4)
    except (asyncio.IncompleteReadError, ConnectionError, TimeoutError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def main() -> None:
    server = await asyncio.start_server(handle, HOST, PORT)
    print(f"Mock gateway: ws://{HOST}:{PORT}/events")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
