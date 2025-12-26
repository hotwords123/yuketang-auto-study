import asyncio
import itertools
import json
import random
import string
from collections.abc import Iterator
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode, urlparse

import aiohttp


class APIError(Exception):
    pass


class YuketangAPI:
    def __init__(self) -> None:
        self.session = aiohttp.ClientSession()
        self.session.headers.update(
            {
                "Xt-Agent": "web",
                "X-Client": "web",
                "xtbz": "ykt",
            }
        )

    async def close(self) -> None:
        await self.session.close()

    async def get_user_info(self) -> dict:
        url = "https://pro.yuketang.cn/v/course_meta/user_info"
        headers = {
            "Accept": "application/json, text/plain, */*",
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if data.get("success") is not True:
            raise APIError(data.get("msg", "Unknown error"))

        return data["data"]["user_profile"]

    async def get_classroom(self, classroom_id: int, role: int = 5) -> dict:
        params = {"role": role}
        url = f"https://pro.yuketang.cn/v2/api/web/classrooms/{classroom_id}?{urlencode(params)}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if data.get("errcode") != 0:
            raise APIError(data.get("errmsg", "Unknown error"))

        return data["data"]

    async def get_course_chapter(
        self, classroom_id: int, sign: str, uv_id: int, term: str = "latest"
    ) -> dict:
        params = {
            "cid": classroom_id,
            "sign": sign,
            "term": term,
            "uv_id": uv_id,
            "classroom_id": classroom_id,
        }
        url = f"https://pro.yuketang.cn/mooc-api/v1/lms/learn/course/chapter?{urlencode(params)}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if not data.get("success"):
            raise APIError(data.get("msg", "Unknown error"))

        return data["data"]

    async def get_classroom_activities(
        self, classroom_id: int, page: int = 0, offset: int = 20, sort: int = -1
    ) -> list[dict]:
        params = {
            "actype": -1,
            "page": page,
            "offset": offset,
            "sort": sort,
        }
        url = f"https://pro.yuketang.cn/v2/api/web/logs/learn/{classroom_id}?{urlencode(params)}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if data.get("errcode") != 0:
            raise APIError(data.get("errmsg", "Unknown error"))

        return data["data"]["activities"]

    async def get_classroom_activities_all(
        self, classroom_id: int, offset: int = 20, sort: int = -1
    ) -> list[dict]:
        results: list[dict] = []

        for page in itertools.count():
            activities = await self.get_classroom_activities(
                classroom_id, page=page, offset=offset, sort=sort
            )
            if not activities:
                break
            results.extend(activities)

        return results

    async def get_leaf_info(self, classroom_id: int, leaf_id: int) -> dict:
        url = f"https://pro.yuketang.cn/mooc-api/v1/lms/learn/leaf_info/{classroom_id}/{leaf_id}/"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if not data.get("success"):
            raise APIError(data.get("msg", "Unknown error"))

        return data["data"]

    async def get_video_watch_progress(
        self, user_id: int, course_id, classroom_id: int, video_id: int
    ) -> dict:
        params = {
            "cid": course_id,
            "user_id": user_id,
            "classroom_id": classroom_id,
            "video_type": "video",
            "vtype": "rate",
            "video_id": video_id,
            "snapshot": 1,
        }
        url = f"https://pro.yuketang.cn/video-log/get_video_watch_progress/?{urlencode(params)}"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if data.get("code") != 0:
            raise APIError(data.get("msg", "Unknown error"))

        return data["data"].get(str(video_id), {})

    async def send_video_heartbeat(self, classroom_id: int, data: list[dict]) -> None:
        url = "https://pro.yuketang.cn/video-log/heartbeat/"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }
        payload = {"heart_data": data}

        async with self.session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()

    async def get_video_playurl(self, classroom_id: int, ccid: str) -> dict:
        params = {
            "video_id": ccid,
            "provider": "cc",
            "file_type": 1,
            "is_single": 0,
            "domain": "pro.yuketang.cn",
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }
        url = f"https://pro.yuketang.cn/api/open/audiovideo/playurl?{urlencode(params)}"

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

        if not data.get("success"):
            raise APIError(data.get("msg", "Unknown error"))

        return data["data"]["playurl"]

    async def get_view_depth(self, classroom_id: int, cards_id: int) -> dict:
        url = "https://pro.yuketang.cn/v2/api/web/cards/view_depth"
        params = {"classroom_id": classroom_id, "cards_id": cards_id}
        headers = {
            "Accept": "application/json, text/plain, */*",
            "classroom-id": str(classroom_id),
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            data = await response.json()

        if data.get("errcode") != 0:
            raise APIError(data.get("errmsg", "Unknown error"))

        return data["data"]

    async def send_view_record(
        self,
        user_id: int,
        cards_id: int,
        data: list[float],
        start_time: float | None = None,
        platform: str = "web",
    ) -> None:
        if start_time is None:
            start_time = int(datetime.now().timestamp() - sum(data))

        url = "wss://pro.yuketang.cn/ws/"
        async with self.session.ws_connect(url) as ws:
            await receive_ws_message(ws, "authorize")

            payload = {
                "op": "view_record",
                "cardsID": cards_id,
                "start_time": start_time,
                "data": data,
                "user_id": user_id,
                "platform": platform,
                "type": "cache",
            }
            print(payload)
            await ws.send_json(payload)

            resp = await receive_ws_message(ws, "view_record")
            if resp.get("errno") != 0:
                raise APIError(resp.get("errmsg", "Unknown error"))


class Heartbeat:
    def __init__(
        self,
        leaf_info: dict,
        media_url: str,
        interval: float = 5,
        playback_rate: float = 1,
        duration: Optional[float] = None,
    ) -> None:
        self.leaf_info = leaf_info
        self.media_url = media_url
        self.interval = interval
        self.playback_rate = playback_rate

        self.user_id = int(leaf_info["user_id"])
        self.course_id = int(leaf_info["course_id"])
        self.classroom_id = int(leaf_info["classroom_id"])
        self.video_id = int(leaf_info["id"])
        self.sku_id = int(leaf_info["sku_id"])
        self.ccid = leaf_info["content_info"]["media"].get("ccid", "")
        if duration is not None:
            self.duration = duration
        else:
            # This field is likely incorrect and thus cannot be trusted
            self.duration = leaf_info["content_info"]["media"]["duration"]

        self.cdn_domain = urlparse(self.media_url).netloc

        self.sequence_id = 0
        self.page_suffix = "".join(
            random.choice(string.digits + string.ascii_lowercase) for _ in range(4)
        )

    def make_all(
        self, timestamp: float, progress: float = 0.0, variance: float = 0.05
    ) -> Iterator[dict]:
        if self.playback_rate != 1:
            yield self.make_heartbeat("ratechange", 0, timestamp)

        rng = random.Random()

        while progress < self.duration:
            progress = min(self.duration, progress + self.interval * self.playback_rate)
            timestamp += self.interval + rng.normalvariate(0, variance)
            yield self.make_heartbeat("heartbeat", progress, timestamp)

    def make_heartbeat(self, event: str, progress: float, timestamp: float) -> dict:
        self.sequence_id += 1

        return {
            "i": self.interval,
            "et": event,
            "p": "web",
            "n": self.cdn_domain,
            "lob": "ykt",
            "cp": progress,
            "fp": 0,
            "tp": 0,
            "sp": self.playback_rate,
            "ts": str(int(timestamp * 1000)),
            "u": self.user_id,
            "uip": "",
            "c": self.course_id,
            "v": self.video_id,
            "skuid": self.sku_id,
            "classroomid": self.classroom_id,
            "cc": self.ccid,
            "d": self.duration,
            "pg": f"{self.video_id}_{self.page_suffix}",
            "sq": self.sequence_id,
            "t": "video",
            "cards_id": 0,
            "slide": 0,
            "v_url": "",
        }


async def get_video_duration(url: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        url,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed with {proc.returncode}, stderr={stderr.decode()}"
        )

    info = json.loads(stdout.decode())
    return float(info["format"]["duration"])


async def receive_ws_message(ws: aiohttp.ClientWebSocketResponse, op: str) -> dict:
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            resp = json.loads(msg.data)
            if resp.get("op") == op:
                return resp
        elif msg.type == aiohttp.WSMsgType.ERROR:
            raise APIError("WebSocket error")
        elif msg.type == aiohttp.WSMsgType.CLOSED:
            raise APIError("WebSocket closed unexpectedly")

    raise APIError("WebSocket message not received")
