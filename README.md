nonebot_plugin_maiguess
=======
基于nonebot框架实现的舞萌key音猜歌插件，感谢[TTsdzb/koishi-plugin-maimai-guess-chart](https://github.com/TTsdzb/koishi-plugin-maimai-guess-chart)项目提供的音频资源 和 [Yuri-YuzuChaN/nonebot-plugin-maimaidx](https://github.com/Yuri-YuzuChaN/nonebot-plugin-maimaidx)项目提供的封面资源

前置条件
--------
1、安装 [ffmpeg](https://llob.napneko.com/zh-CN/guide/ffmpeg)，并将其路径添加到 PATH 环境变量中  
2、在 [Release](https://github.com/TTsdzb/koishi-plugin-maimai-guess-chart/releases) 下载音频资源并解压，得到一个名为 maimai-guess-chart-assets 的文件夹  
3、在 [static](https://share.yuzuchan.moe/d/aria/Resource.zip?sign=LOqwqDVm95dYnkEDYKX2E-VGj0xc_JxrsFnuR1BcvtI=:0) 下载封面资源  

使用方法
--------
1、将仓库下载到本地 or `nb plugin install nonebot-plugin-maimaidx`（尚未上传）  
2、在.env配置项文件中配置绝对路径`GUESSPATH`和`PICPATH`  
例如  
`GUESSPATH=C:\bot\capoobot\guees_music\assets\maimai-guess-chart-assets`  
`PICPATH=C:\bot\capoobot\static\mai\cover`  

指令
--------
* 猜歌
* 猜歌排名
* 猜歌设置
* 结束猜歌
