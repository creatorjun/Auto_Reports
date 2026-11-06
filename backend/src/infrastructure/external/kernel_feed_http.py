# backend/src/infrastructure/external/kernel_feed_http.py
import httpx


async def fetch_bytes(client: httpx.AsyncClient, url: str, maximum: int) -> bytes:
    data = bytearray()
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes(65536):
            if len(data) + len(chunk) > maximum:
                raise ValueError("Kernel metadata exceeds the source size limit")
            data.extend(chunk)
    return bytes(data)
