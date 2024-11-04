from .config import Config
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Dict
from nonebot import get_driver
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupMessageEvent
from nonebot.params import CommandArg
import httpx
import asyncio

global_config = get_driver().config

guesspath = Path(global_config.guesspath)
picpath = Path(global_config.picpath)

music_dir = guesspath
cover_dir = picpath

# 柚子别名库API
API_BASE_URL = "https://api.yuzuchan.moe/maimaidx"


guess_music_start = on_command("猜歌", priority=5)
guess_music_solve = on_message(rule=lambda event: is_now_playing_guess_music(event), priority=5)
end_guess_music = on_command("结束猜歌", priority=5)
toggle_guess_music = on_command("猜歌设置", priority=5)

games = {}
# 仿照了下柚子的猜歌逻辑，但是懒得写开关了，存字典里

locks = {}  # 锁！

# kb币的json
user_data_file = Path(__file__).parent / "user_data.json"
settings_file = Path(__file__).parent / "settings.json"  # 存储猜歌开关

def load_user_data() -> Dict[str, Dict[str, int]]:
    if user_data_file.exists():
        with open(user_data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(data: Dict[str, Dict[str, int]]):
    with open(user_data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_settings() -> Dict[str, bool]:
    if settings_file.exists():
        with open(settings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(settings: Dict[str, bool]):
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def is_now_playing_guess_music(event: GroupMessageEvent) -> bool:
    """判断猜歌状态"""
    gid = str(event.group_id)
    return gid in games and games[gid].get("active", False)

@guess_music_start.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)


    # 加载设置，检查猜歌是否启用
    settings = load_settings()
    if not settings.get(gid, True):  # 默认启用猜歌
        await guess_music_start.finish("该群聊的猜歌功能已关闭，输入[猜歌设置]开启", reply_message=True)
        return

    # 初始化锁
    if gid not in locks:
        locks[gid] = asyncio.Lock()
    
    async with locks[gid]:  # 锁！解决并发
        if gid in games:
            await guess_music_start.finish("已有正在进行的猜歌，请稍后再试", reply_message=True)

        directories = [d for d in music_dir.iterdir() if d.is_dir()]
        selected_dir = random.choice(directories)
        
        # 提取歌曲ID并获取别名
        song_id = selected_dir.name.split('_')[0]
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/getsongsalias", params={"song_id": song_id})
            data = response.json()
        if data["status_code"] != 200:
            await guess_music_start.finish("获取歌曲别名失败，请再发一遍指令尝试", reply_message=True)
        
        song_name = data["content"].get("Name", "")
        aliases = data["content"].get("Alias", [])

        # 剪裁音频为5秒的片段
        full_audio_path = selected_dir / "4.mp3"
        trimmed_audio_path = selected_dir / "4_trimmed.mp3"
        start_time = random.randint(0, max(0, int(get_audio_duration(full_audio_path) - 5)))
        trim_audio(full_audio_path, trimmed_audio_path, start_time, 5)
        
        await guess_music_start.send(MessageSegment.record(trimmed_audio_path.as_uri()))
        await guess_music_start.send("请在30秒内告诉咖波这是哪首歌吧")

        # 存储游戏状态
        games[gid] = {
            "aliases": [song_name.lower()] + [alias.lower() for alias in aliases],
            "name": song_name,
            "answered": False,
            "trimmed_audio_path": trimmed_audio_path,
            "song_id": song_id,
            "active": True  
        }

        await asyncio.sleep(30)
        if gid in games and not games[gid]["answered"]:
            await send_answer_with_cover(bot, gid, event)

@guess_music_solve.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    gid = str(event.group_id)

    if gid not in games or games[gid]["answered"] or not games[gid].get("active", False):
        return  

    user_answer = event.get_plaintext().strip().lower()
    if user_answer in games[gid]["aliases"]:
        games[gid]["answered"] = True
        await send_answer_with_cover(bot, gid, event)

        # 这里临时加了个kb币功能
        user_id = str(event.user_id)
        user_name = event.sender.nickname
        user_data = load_user_data()
        
        if user_id not in user_data:
            user_data[user_id] = {"name": user_name, "kb": 0}
        
        user_data[user_id]["kb"] += 5
        save_user_data(user_data)

async def send_answer_with_cover(bot: Bot, gid: str, event: GroupMessageEvent):
    """发送正确答案以及封面"""
    song_name = games[gid]["name"]
    song_id = games[gid]["song_id"]
    cover_img = cover_dir / f"{song_id}.png"

    answer_text = f"猜对了，答案是：{song_name}！\n⭐kb币+5" if games[gid]["answered"] else f"时间到！这首歌是：{song_name}"
    if cover_img.is_file():
        answer = MessageSegment.text(answer_text) + MessageSegment.image(cover_img.as_uri())
    else:
        answer = MessageSegment.text(answer_text + "（封面图未找到）")

    await bot.send(event, answer, reply_message=True)

    os.remove(games[gid]["trimmed_audio_path"])
    del games[gid]

def trim_audio(input_file: Path, output_file: Path, start_time: float, duration: float):
    """使用ffmpeg剪裁音频为指定时长"""
    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-ss", str(start_time),
        "-t", str(duration),
        "-acodec", "copy",
        str(output_file)
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def get_audio_duration(input_file: Path) -> float:
    """使用ffmpeg获取音频文件的时长"""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_file)
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        return float(result.stdout.strip())
    else:
        raise ValueError("无法获取音频时长。")

@end_guess_music.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """结束当前的猜歌进程并发送答案"""
    gid = str(event.group_id)
    if gid in games:
        await send_answer_with_cover(bot, gid, event) 
        os.remove(games[gid]["trimmed_audio_path"])  
        del games[gid]
        await end_guess_music.finish("已结束当前猜歌游戏，正在发送答案", reply_message=True)
    else:
        await end_guess_music.finish("当前没有进行中的猜歌游戏", reply_message=True)


@toggle_guess_music.handle()
async def _(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """开关猜歌功能"""
    gid = str(event.group_id)
    settings = load_settings()
    arg = args.extract_plain_text().strip()
    if arg == "开":
        settings[gid] = True
        await toggle_guess_music.finish("已开启该群聊的猜歌功能", reply_message=True)
    elif arg == "关":
        settings[gid] = False
        await toggle_guess_music.finish("已关闭该群聊的猜歌功能", reply_message=True)
    else:
        await toggle_guess_music.finish("请使用“猜歌设置 开”或“关”来设置猜歌功能", reply_message=True)
    
    save_settings(settings)


leaderboard = on_command("猜歌排名", priority=5)

@leaderboard.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    user_data = load_user_data()
    rankings = sorted(user_data.items(), key=lambda x: x[1]["kb"], reverse=True)

    leaderboard_message = "猜歌排名：\n"
    for i, (user_id, data) in enumerate(rankings[:5], start=1):
        leaderboard_message += f"{i}. {data['name']} - {data['kb']} kb币\n"
    user_id = str(event.user_id)
    user_rank = next((i for i, (uid, _) in enumerate(rankings) if uid == user_id), None)
    if user_rank is not None:
        user_data_entry = user_data[user_id]
        leaderboard_message += f"\n您的排名：{user_rank + 1}. {user_data_entry['name']} - {user_data_entry['kb']} kb币"
    await leaderboard.finish(leaderboard_message)