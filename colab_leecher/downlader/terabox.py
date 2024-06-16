# copyright 2024 © Xron Trix | https://github.com/Xrontrix10

import aiohttp
import logging
from colab_leecher.utility.variables import Aria2c
from colab_leecher.utility.handler import cancelTask
from colab_leecher.downlader.aria2 import aria2_Download


async def terabox_download(link: str, index):
    global Aria2c
    payload = {"url": f"{link}"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    fast_download_url = ""
    slow_download_url = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://ytshorts.savetube.me/api/v1/terabox-downloader",
            data=payload,
            headers=headers,
        ) as response:
            try:
                response.raise_for_status()
                json_response = await response.json()
                fast_download_url = json_response["response"][0]["resolutions"][
                    "Fast Download"
                ]
                slow_download_url = json_response["response"][0]["resolutions"][
                    "HD Video"
                ]
            except Exception as e:
                logging.error(f"Error: {e}")
                await cancelTask(f"Error generating download link: {e}")

        async with session.get(fast_download_url) as response:
            try:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type")
                Aria2c.link_info = False
                if "application/octet-stream" in content_type:
                    await aria2_Download(fast_download_url, index)
                else:
                    logging.info("Fast donload link is unusable")
                    await aria2_Download(slow_download_url, index)
            except Exception as e:
                logging.info("Fast donload link is unusable")
                await aria2_Download(slow_download_url, index)
