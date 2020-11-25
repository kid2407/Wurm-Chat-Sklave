import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from shutil import copyfile
from typing import List

from discord import Client, TextChannel, Member, AllowedMentions, Guild, Role
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
                for singlechannel in _config["channels"][name]:
                    channel: TextChannel = client.get_channel(singlechannel)
                    guild: Guild = channel.guild
                    mention_index = message.find("@")
                    if not mention_index == -1:
                        space_index = message.find(" ", mention_index)
                        if not space_index == -1:
                            mention_end_index = space_index
                        else:
                            mention_end_index = len(message)
                        if mention_end_index - mention_index + 1 > 3:
                            mention_match: str = message[mention_index + 1:mention_end_index]
                            users: List[Member] = channel.guild.members
                            for user in users:
                                if not user.display_name.lower().find(mention_match.lower()) == -1:
                                    mention_string: str = user.mention
                                    message = message.replace("@" + mention_match, mention_string)
                                    break
                    if name == "_event":
                        roles_to_mention = []
                        for keyword in _config["events"]:
                            if not message.lower().find(keyword.lower()) == -1:
                                role_mention: Role = guild.get_role(_config["events"][keyword])
                                if role_mention is not None:
                                    if role_mention.id not in roles_to_mention:
                                        roles_to_mention.append(role_mention.id)
                        if len(roles_to_mention) > 0:
                            for blacklisted_word in _config["event_blacklist"]:
                                if message.find(blacklisted_word) > -1:
                                    return
                                for single_role_id in roles_to_mention:
                                    message = guild.get_role(single_role_id).mention + " " + message
                                asyncio.run_coroutine_threadsafe(channel.send(content=message, allowed_mentions=AllowedMentions(users=True, roles=True)), client.loop)
                    else:
                        asyncio.run_coroutine_threadsafe(channel.send(content=message, allowed_mentions=AllowedMentions(users=True, roles=True)), client.loop)
    _config["linecount"][name] = newcount


@client.event
async def on_ready():
    print('Angemeldet als {0.user}'.format(client))
    for name in _config["channels"]:
        tail_newest_log(name)


def tail_newest_log(name: str):
    if name.startswith("_"):
        filename = date.today().strftime("_" + name[1:].capitalize() + ".%Y-%m-%d.txt")
    else:
        filename = date.today().strftime(name.capitalize() + ".%Y-%m-%d.txt")
    filepath = _config["wurm_path"] + "players/" + _config["playername"] + "/logs/" + filename
    if os.path.isfile(filepath):
        for channel in _config["channels"][name]:
            if client.get_channel(channel):
                print(f"Datei {filepath} geladen.")
                if "file_path" not in _config:
                    _config["file_path"] = {}
                if "linecount" not in _config:
                    _config["linecount"] = {}
                if name not in _config["file_path"]:
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
    base_path = os.path.dirname(os.path.realpath(sys.argv[0])) + os.path.sep

    if not os.path.isfile(base_path + "config.json"):
        copyfile("config.json.example", "config.json")

    if not os.path.isfile(base_path + "config.json"):
        raise Exception("config.json konnte nicht gefunden werden.")

    with open(base_path + "config.json") as config_file:
        global _config
        _config = json.load(config_file)


load_config()
client.run(_config["token"])
