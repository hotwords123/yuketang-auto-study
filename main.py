import asyncio
import itertools
import json
import logging
import time
from typing import Optional
from urllib.parse import unquote

from tqdm import tqdm

from yuketang_video.api import Heartbeat, YuketangAPI, get_video_duration
from yuketang_video.util import wrap_with_async_ctx

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    with open("config.json") as f:
        config = json.load(f)

    cookie_str = config["cookie"]

    if cookie_str == "FIREFOX":
        import browser_cookie3

        cookies = browser_cookie3.firefox(domain_name="pro.yuketang.cn")
        cookie_dict = {cookie.name: cookie.value for cookie in cookies if cookie.value}

    else:
        cookies = [kv.split("=", 1) for kv in cookie_str.split("; ")]
        cookie_dict = {k: unquote(v) for k, v in cookies}

    api = YuketangAPI()
    api.session.headers.update({"User-Agent": config["user_agent"]})
    api.session.cookie_jar.update_cookies(cookie_dict)

    cookie_header_map = {
        "university-id": "university_id",
        "uv-id": "uv_id",
        "X-CSRFToken": "csrftoken",
    }
    for header, cookie_name in cookie_header_map.items():
        if cookie_name in cookie_dict:
            api.session.headers[header] = cookie_dict[cookie_name]

    classroom_id = config["classroom_id"]
    leaves = await collect_leaves(api, classroom_id)
    video_leaves = [leaf for leaf in leaves if leaf["leaf_type"] == 0]
    logger.info("Total video count: %d", len(video_leaves))

    max_concurrent_tasks = config.get("max_concurrent_tasks", 8)
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    wrapped_send_heartbeats = wrap_with_async_ctx(semaphore, send_heartbeats)

    tasks: list[asyncio.Task] = []

    for leaf in video_leaves:
        leaf_id = leaf["id"]
        leaf_info = await api.get_leaf_info(classroom_id, leaf_id)
        watch_progress = await api.get_video_watch_progress(
            user_id=leaf_info["user_id"],
            course_id=leaf_info["course_id"],
            classroom_id=classroom_id,
            video_id=leaf_id,
        )

        media_data = leaf_info["content_info"]["media"]
        if "playurl" in media_data:
            media_url = media_data["playurl"]
        elif "ccid" in media_data:
            ccid = media_data["ccid"]
            playurl = await api.get_video_playurl(classroom_id, ccid)
            media_url = next(iter(playurl["sources"].values()))[0]
        else:
            logger.warning("No media URL found for %d %s", leaf_id, leaf_info["name"])
            continue

        logger.info("%d %s %s", leaf_id, leaf_info["name"], media_url)

        if watch_progress:
            if watch_progress.get("completed") == 1:
                logger.info("Finished: %d %s", leaf_id, leaf_info["name"])
                continue

            last_point = watch_progress["last_point"]
            duration = watch_progress["video_length"]

        else:
            last_point = 0
            duration = leaf_info["content_info"]["media"]["duration"]
            if duration == 0:
                duration = await get_video_duration(media_url)
            logger.info("Duration: %d", duration)

        logger.info("Last point: %d", last_point)

        tasks.append(
            asyncio.create_task(
                wrapped_send_heartbeats(
                    api, leaf_info, media_url, last_point, duration, position=len(tasks)
                )
            )
        )

    await asyncio.gather(*tasks)

    logger.info("All tasks completed.")

    await api.close()


async def collect_leaves(api: YuketangAPI, classroom_id: int) -> list[dict]:
    classroom = await api.get_classroom(classroom_id)
    logger.info(
        "Classroom: course_name=%s, name=%s, teacher_name=%s",
        classroom["course_name"],
        classroom["name"],
        classroom["teacher_name"],
    )

    chapter_data = await api.get_course_chapter(
        classroom_id, sign=classroom["course_sign"], uv_id=classroom["uv_id"]
    )

    leaves: list[dict] = []

    for chapter in chapter_data["course_chapter"]:
        logger.info("Chapter: %d %s", chapter["id"], chapter["name"])

        for item in chapter["section_leaf_list"]:
            if "leaf_list" in item:
                logger.info("  Section: %d %s", item["id"], item["name"])

                for leaf in item["leaf_list"]:
                    logger.info(
                        "    Leaf: %d %s type=%d",
                        leaf["id"],
                        leaf["name"],
                        leaf["leaf_type"],
                    )
                    leaves.append(leaf)

            else:
                logger.info(
                    "  Leaf: %d %s type=%d", item["id"], item["name"], item["leaf_type"]
                )
                leaves.append(item)

    return leaves


async def send_heartbeats(
    api: YuketangAPI,
    leaf_info: dict,
    media_url: str,
    last_point: float,
    duration: float,
    position: Optional[int] = None,
) -> None:
    builder = Heartbeat(
        leaf_info, media_url, interval=5, playback_rate=2.0, duration=duration
    )
    heartbeats = builder.make_all(time.time() - 30, last_point)

    with tqdm(
        total=duration,
        initial=last_point,
        unit="s",
        desc=leaf_info["name"],
        leave=False,
        position=position,
    ) as pbar:
        for batch in itertools.batched(heartbeats, 6):
            timestamp = int(batch[-1]["ts"]) / 1000
            progress = batch[-1]["cp"]

            await asyncio.sleep(max(0, timestamp - time.time()))

            while True:
                try:
                    await api.send_video_heartbeat(
                        leaf_info["classroom_id"], list(batch)
                    )
                    break
                except Exception as e:
                    logger.error("Error sending video heartbeat: %s", e)
                    await asyncio.sleep(1)
                    continue

            pbar.update(progress - pbar.n)

            try:
                watch_progress = await api.get_video_watch_progress(
                    user_id=leaf_info["user_id"],
                    course_id=leaf_info["course_id"],
                    classroom_id=leaf_info["classroom_id"],
                    video_id=leaf_info["id"],
                )

                pbar.set_postfix(
                    {
                        "watch_length": watch_progress.get("watch_length", 0),
                        "rate": watch_progress.get("rate", 0),
                    }
                )
            except Exception as e:
                logger.error("Error fetching watch progress: %s", e)

    logger.info(
        "Finished sending heartbeats for %d %s", leaf_info["id"], leaf_info["name"]
    )


if __name__ == "__main__":
    asyncio.run(main())
