import asyncio
import json
import os
import subprocess
from datetime import date
from shutil import copyfile

from discord import Client, TextChannel
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

client = Client()
_config = {}


class MyHandler(FileSystemEventHandler):
    name: str = ''

    def __init__(self, name: str):
        self._name = name

    def on_modified(self, event: FileSystemEvent):
        super().on_modified(event)
        print(f'Neue Nachricht in {os.path.basename(event.src_path)}')
        send_latest_messages_to_discord(self._name)


def get_line_count_of_file(name: str) -> str:
    filecontent = subprocess.Popen(("cat", _config["file_path"][name]), stdout=subprocess.PIPE)
    count = subprocess.check_output(("wc", "-l"), stdin=filecontent.stdout)
    filecontent.wait()
    return count.decode()


def send_latest_messages_to_discord(name: str):
    newcount = get_line_count_of_file(name)
    diff = int(newcount) - int(_config["linecount"][name])
    if diff > 0:
        messages = subprocess.check_output(("tail", "-n", str(diff), _config["file_path"][name])).decode().strip()
        message_list = messages.split(sep="\n")
        for message in message_list:
            message = message.strip()
            if len(message) > 0 and message.startswith("["):
                channel: TextChannel = client.get_channel(_config["channels"][name])
                asyncio.run_coroutine_threadsafe(channel.send(content=message), client.loop)
    _config["linecount"][name] = newcount


@client.event
async def on_ready():
    print('Angemeldet als {0.user}'.format(client))
    for name in _config["channels"]:
        tail_newest_log(name)


def tail_newest_log(name: str):
    filename = date.today().strftime(name.capitalize() + ".%Y-%m.txt")
    filepath = _config["wurm_path"] + "players/" + _config["playername"] + "/logs/" + filename
    if os.path.isfile(filepath):
        if client.get_channel(_config["channels"][name]):
            print(f"Datei {filepath} geladen.")
            if "file_path" not in _config:
                _config["file_path"] = {}
            if "linecount" not in _config:
                _config["linecount"] = {}
            _config["file_path"][name] = filepath
            _config["linecount"][name] = get_line_count_of_file(name)
            observer = Observer()
            observer.schedule(event_handler=MyHandler(name), path=filepath)
            observer.start()
        else:
            print(f"Konnte den Kanal mit der Id {_config['channels'][name]} nicht finden.")
    else:
        print(f"Datei {filepath} nicht gefunden :/")


def load_config():
    if not os.path.isfile("config.json"):
        copyfile("config.json.example", "config.json")

    if not os.path.isfile("config.json"):
        raise Exception("config.json konnte nicht gefunden werden.")

    with open("config.json") as config_file:
        global _config
        _config = json.load(config_file)


load_config()
client.run(_config["token"])
