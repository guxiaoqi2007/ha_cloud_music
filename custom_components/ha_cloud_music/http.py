import base64
import requests
import logging
from urllib.parse import parse_qsl, quote
from homeassistant.components.http import HomeAssistantView
from aiohttp import web
from .models.music_info import MusicSource
from .manifest import manifest
_LOGGER = logging.getLogger(__name__)

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

        not_found_tips = quote(f'当前没有找到编号是{id}，歌名为{song}，作者是{singer}的播放链接')
        play_url = f'http://fanyi.baidu.com/gettts?lan=zh&text={not_found_tips}&spd=5&source=web'
        headers={
                "Cache-Control": "no-cache, private",
                "Server": "nginx",
                "Strict-Transport-Security": "max-age=31536000",
        }
        # 缓存KEY
        play_key = f'{id}{song}{singer}{source}'
        if self.play_key == play_key:
           return web.HTTPFound(self.play_url,headers=headers)

        source = int(source)
        if source == MusicSource.PLAYLIST.value \
                or source == MusicSource.ARTISTS.value \
                or source == MusicSource.DJRADIO.value \
                or source == MusicSource.CLOUD.value:
            # 获取播放链接
            url, fee = await cloud_music.song_url(id)
            if url is not None:
                # 收费音乐
                if fee == 1:
                    url = await hass.async_add_executor_job(self.getVipMusic_gdstudio, id)
                    #_LOGGER.warning(f'获取到收费音乐：{url}')
                    if url is None or url == '':
                        result = await cloud_music.async_music_source(song, singer)
                        if result is not None:
                            url = result.url

                play_url = url
            else:
                # 从云盘里获取
                url = await cloud_music.cloud_song_url(id)
                if url is not None:
                    play_url = url
                else:
                    result = await cloud_music.async_music_source(song, singer)
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
        return web.HTTPFound(play_url,headers=headers)

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
             'br': ['999', '320'][1]
            })
            data = res.json()
            return data.get('url').replace("https", "http")
            #return data.get('url')
        except Exception as ex:
            pass
    
