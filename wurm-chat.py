import asyncio
import json
import os
import subprocess
from datetime import date

from discord import Client, TextChannel
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

client = Client()
_config = {}


class MyHandler(FileSystemEventHandler):

    def on_modified(self, event: FileSystemEvent):
        super().on_modified(event)

        print(f'event type: {event.event_type} und path ist: {event.src_path}')

        send_latest_messages_to_discord()


def get_line_count_of_file() -> str:
    filecontent = subprocess.Popen(("cat", _config["file_path"]), stdout=subprocess.PIPE)
    count = subprocess.check_output(("wc", "-l"), stdin=filecontent.stdout)
    filecontent.wait()
    return count.decode()


def send_latest_messages_to_discord():
    newcount = get_line_count_of_file()
    diff = int(newcount) - int(_config["linecount"])
    if diff > 0:
        messages = subprocess.check_output(("tail", "-n", str(diff), _config["file_path"])).decode().strip()
        message_list = messages.split(sep="\n")
        for message in message_list:
            message = message.strip()
            if len(message) > 0 and message.startswith("["):
                channel: TextChannel = client.get_channel(_config["channel_id"])
                asyncio.run_coroutine_threadsafe(channel.send(content=message), client.loop)
    _config["linecount"] = newcount


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    tail_newest_village_log()


def tail_newest_village_log():
    filename = date.today().strftime("Village.%Y-%m.txt")
    filepath = _config["wurm_path"] + "players/" + _config["playername"] + "/logs/" + filename
    print("Dateipfad: " + filepath)
    if os.path.isfile(filepath):
        _config["file_path"] = filepath
        _config["linecount"] = get_line_count_of_file()
        observer = Observer()
        observer.schedule(event_handler=MyHandler(), path=filepath)
        observer.start()
    else:
        print("Datei nicht gefunden :/")


def load_config():
    if not os.path.isfile("config.json"):
        raise Exception("Config file not found")

    with open("config.json") as config_file:
        global _config
        _config = json.load(config_file)


load_config()
client.run(_config["token"])
