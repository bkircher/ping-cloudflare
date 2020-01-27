import asyncio
import os
import re
import sys

import aiohttp
import async_timeout
import tqdm

pattern = re.compile(r"^- \[((?:\w+\.)+\w+)\]\((http[s]?://(?:\w+\.)+\w+)\)$")
progressbar = True


def report(msg):
    if not progressbar:
        print(msg)


def sites(filename):
    with open(filename, "r") as f:
        for line in f.readlines():
            match = re.search(pattern, line)
            if match:
                yield match.groups()


async def fetch(session, url):
    with async_timeout.timeout(60000):
        async with session.get(url) as response:
            return response


async def bound_fetch(semaphore, session, url):
    async with semaphore:
        try:
            response = await fetch(session, url)
            report("{} → {}".format(url, response.status))
        except asyncio.TimeoutError:
            report("{} → timeout".format(url))
        except aiohttp.client_exceptions.ClientOSError as exc:
            report("{} → {}".format(url, exc.strerror))
        except Exception as exc:
            report("{} → {}".format(url, str(exc)))


async def run():
    work = [url for _, url in sites("sites-using-cloudflare-dns.md")]
    tasks = []
    sem = asyncio.Semaphore(1024)

    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for url in work:
            task = asyncio.ensure_future(bound_fetch(sem, session, url))
            tasks.append(task)

        if progressbar:
            [await res for res in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks))]
        else:
            await asyncio.gather(*tasks)

    print("Done.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print("Interrupted")
        try:
            sys.exit(0)
        except SystemExit:
            # noinspection PyProtectedMember
            os._exit(0)
    print("Pending tasks at exit: {}".format(asyncio.Task.all_tasks(loop)))
    loop.close()
