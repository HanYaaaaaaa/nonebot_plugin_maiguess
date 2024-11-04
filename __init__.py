from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from .guess import *
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-maimaiguess",
    description="舞萌DX的key音猜歌插件",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)
