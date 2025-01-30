import base64
import requests
import logging
import os
from urllib.parse import parse_qsl, quote
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.media_player import (
    BrowseError, BrowseMedia,
    async_process_play_media_url
)
from aiohttp import web, ClientSession
from aiofiles import open as aio_open

from .models.music_info import MusicSource
from .manifest import manifest
_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry

DOMAIN = manifest.domain

class HttpView(HomeAssistantView):

    url = "/cloud_music/url"
    name = "cloud_music:url"
    requires_auth = False
    cors_allowed = True

    play_key = None
    play_url = None

    async def get(self, request):

        hass = request.app["hass"]
        cloud_music = hass.data['cloud_music']
        if hass.data['enable_save_local'] is not None and hass.data['save_local_path'] is not None:
            save_local = hass.data['enable_save_local']
            tmp_save_path = hass.data['save_local_path']

        query = {}
        data = request.query.get('data')
        if data is not None:
            decoded_data = base64.b64decode(data).decode('utf-8')
            qsl = parse_qsl(decoded_data)
            for q in qsl:
                query[q[0]] = q[1]

        id = query.get('id')
        source = query.get('source')
        song = query.get('song')
        singer = query.get('singer')

        save_path = f'/media/{tmp_save_path}/{singer}/{id}-{song}.mp3'
        play_path = f'/media/local/{tmp_save_path}/{singer}/{id}-{song}.mp3'

        not_found_tips = quote(f'当前没有找到编号是{id}，歌名为{song}，作者是{singer}的播放链接')
        play_url = f'http://fanyi.baidu.com/gettts?lan=zh&text={not_found_tips}&spd=5&source=web'
        
        # 缓存KEY
        play_key = f'{id}{song}{singer}{source}'
        if self.play_key == play_key:
           return web.HTTPFound(self.play_url)

        source = int(source)
        if source == MusicSource.PLAYLIST.value \
                or source == MusicSource.ARTISTS.value \
                or source == MusicSource.DJRADIO.value \
                or source == MusicSource.CLOUD.value:
            # 获取播放链接
            url, fee = await cloud_music.song_url(id)
            _LOGGER.warning(f'歌曲播放链接: {url}')
            if url is not None:
                # 收费音乐
                if os.path.exists(save_path):
                    
                    url = async_process_play_media_url(hass, play_path)
                else:
                 if fee == 1:
                    url = await hass.async_add_executor_job(self.getVipMusic_gdstudio, id)
                    _LOGGER.warning(f'获取到收费音乐：{url}')
                    
                    if url is None or url == '':
                        result = await cloud_music.async_music_source(song, singer)
                        if result is not None:
                            url = result.url
                 _LOGGER.debug(f'是否下载本地{save_local}')
                 if save_local:
                    await self.download_audio_file_async(url, save_path)
                play_url = url
            else:
                # 从云盘里获取
                url = await cloud_music.cloud_song_url(id)
                if url is not None:
                    play_url = url
                else:
                    _LOGGER.warning(f'没有找到歌曲：{song}，作者：{singer}')
                    result = await cloud_music.async_music_source(song, singer)
                    _LOGGER.warning(f'歌曲：{result.url}')
                    if result is not None:
                        play_url = result.url
        
        self.play_key = play_key
        self.play_url = play_url
             
        #play_url = "http://192.168.6.168:888/123.mp3"
        # 重定向到可播放链接
        content_type="text/html; charset=UTF-8"

        headers={
                "Cache-Control": "no-cache, private",
                "Server": "nginx",
                "Strict-Transport-Security": "max-age=31536000",
        }
        headers_to_remove = ["Referrer-Policy", "X-Content-Type-Options","X-Frame-Options"]
        
        
        #result_local_play = await self.download_audio_file_async(play_url, save_path)
        #if result_local_play  == 1:
        #    play_url = async_process_play_media_url(hass, play_path)
        _LOGGER.debug(f"播放链接xx：{play_url}")
        #self.play_url = play_url
        return web.HTTPFound(play_url)

    # VIP音乐资源
    def getVipMusic(self, id):
        try:
            res = requests.post('https://music.dogged.cn/api.php', data={
                'types': 'url',
                'id': id,
                'source': 'netease'
            })
            data = res.json()
            return data.get('url')
        except Exception as ex:
            pass
    def getVipMusic_gdstudio(self, id):
        try:
            res = requests.get('https://music-api.gdstudio.xyz/api.php', params={
             'types': 'url',
             'source': 'netease',
             'id': id,
             'br': ['999', '128'][1]
            })
            data = res.json()
            return data.get('url').replace("https", "http")
        except Exception as ex:
            pass
    async def download_audio_file_async(self, url, save_path):
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            if os.path.exists(save_path):
                _LOGGER.warning(f"文件已存在: {save_path}")
                return 1
                
            async with ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    # 确保保存路径的目录存在

                    # 写入文件
                    async with aio_open(save_path, 'wb') as file:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            await file.write(chunk)
            _LOGGER.warning(f"音频文件已成功下载并保存到 {save_path}")
        except Exception as ex:
            _LOGGER.error(f"下载音频文件时发生错误: {ex}")
    
