import asyncio
import itertools
import json
import logging
import time
from typing import Optional
from urllib.parse import unquote

from tqdm import tqdm

from yuketang_video.api import Heartbeat, YuketangAPI, get_video_duration

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
    leaf_ids = await collect_leaf_ids(api, classroom_id)
    logger.info("Total video count: %d", len(leaf_ids))

    tasks: list[asyncio.Task] = []

    for leaf_id in leaf_ids:
        leaf_info = await api.get_leaf_info(classroom_id, leaf_id)
        watch_progress = await api.get_video_watch_progress(
            user_id=leaf_info["user_id"],
            course_id=leaf_info["course_id"],
            classroom_id=classroom_id,
            video_id=leaf_id,
        )
        playurl = await api.get_video_playurl(
            classroom_id, leaf_info["content_info"]["media"]["ccid"]
        )
        media_url = next(iter(playurl["sources"].values()))[0]

        logger.info("%d %s %s", leaf_id, leaf_info["name"], media_url)

        if watch_progress:
            if watch_progress.get("completed") == 1:
                logger.info("Finished: %d %s", leaf_id, leaf_info["name"])
                continue

            last_point = watch_progress["last_point"]
            duration = watch_progress["video_length"]

        else:
            last_point = 0
            duration = await get_video_duration(media_url)
            logger.info("Duration: %d", duration)

        logger.info("Last point: %d", last_point)

        tasks.append(
            asyncio.create_task(
                send_heartbeats(
                    api, leaf_info, media_url, last_point, duration, position=len(tasks)
                )
            )
        )

    await asyncio.gather(*tasks)

    logger.info("All tasks completed.")

    await api.close()


async def collect_leaf_ids(api: YuketangAPI, classroom_id: int) -> list[int]:
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

    leaf_ids: list[int] = []

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

                    if leaf["leaf_type"] == 0:
                        leaf_ids.append(leaf["id"])

            else:
                logger.info(
                    "  Leaf: %d %s type=%d", item["id"], item["name"], item["leaf_type"]
                )
                if item["leaf_type"] == 0:
                    leaf_ids.append(item["id"])

    return leaf_ids


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
            await api.send_video_heartbeat(leaf_info["classroom_id"], list(batch))

            watch_progress = await api.get_video_watch_progress(
                user_id=leaf_info["user_id"],
                course_id=leaf_info["course_id"],
                classroom_id=leaf_info["classroom_id"],
                video_id=leaf_info["id"],
            )

            pbar.update(progress - pbar.n)
            pbar.set_postfix(
                {
                    "watch_length": watch_progress.get("watch_length", 0),
                    "rate": watch_progress.get("rate", 0),
                }
            )

    logger.info(
        "Finished sending heartbeats for %d %s", leaf_info["id"], leaf_info["name"]
    )


if __name__ == "__main__":
    asyncio.run(main())
