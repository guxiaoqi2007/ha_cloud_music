from bs4 import BeautifulSoup
import logging
import requests
import re
from .models.music_info import MusicInfo, MusicSource
_LOGGER = logging.getLogger(__name__)


def get_last_part(path):
    last_slash_index = path.rfind('/')
    if last_slash_index != -1:
        return path[last_slash_index + 1:]
    return path


def get_music(keyword):
    # https://www.gequbao.com
    api = 'https://www.fangpi.net'
    session = requests.Session()
    api_path= f'{api}/s/{keyword}'
    try:
        headers = {
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
                
                  }
        response = session.get(api_path,headers=headers)
        soup = BeautifulSoup(response.text.encode(response.encoding), 'lxml')
        items = soup.select('.card-text .row')
        
        if len(items) > 1:
            row = items[1]
            song = row.select('.music-title')[0].get_text().strip()
            singer = row.select('.text-jade')[0].get_text().strip()

            a = row.select('.music-link')
            href = a[0].attrs['href']

            _LOGGER.warning(f'row{row}  ---- href:{href}')
            b = f"{api}{href}"
            headers = {
                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
                   "Referer": b  # 替换为实际的URL
                    }

             # 创建一个 RequestsCookieJar 对象并从字符串加载 Cookie
            cookies = {
                     "8cabbc389fa8e900d894a3a7125ab4a0" : "6f8b1b06cbd5f540d05d4cfccdd6a651",
                     "fp_referer": b
            }
            _LOGGER.warning(f'cookies:{cookies}')
            
            
            response = session.get(b,headers=headers,)


            html = response.text
            html1 = response

            soup = BeautifulSoup(html, 'lxml')
            cover = soup.select('head meta[property="og:image"]')
          
            pic = 'https://p2.music.126.net/tGHU62DTszbFQ37W9qPHcg==/2002210674180197.jpg'
            # 封面
            if len(cover) > 0:
                pic = cover[0].attrs['content']

            #songId = get_last_part(href)
            album = ''
           #audio_url = f'https://www.fangpi.net/api/play_url?id={songId}'
            pattern = r"window.play_id = '(.*?)';"
            _LOGGER.warning(f'html:{html}')
            _LOGGER.warning(f'html1:{html1}')
            match = re.search(pattern, html)
            
            _LOGGER.warning(f'match:{match}')
            if match:
                songId = match.group(1)
                response = session.post(f'{api}/api/play-url', data={'id': songId})
                data = response.json()
                if data.get('code') == 1:
                    audio_url = data['data']['url']
                    audio_url = get_final_url(audio_url)
                    return MusicInfo(songId, song, singer, album, 0, audio_url, pic, MusicSource.URL.value)
            else :
                _LOGGER.warning(keyword)
            
                songId = search_kuwo_song(keyword)
                _LOGGER.warning(f'search_tencent_song: {songId}')
                if songId:
                    #songId = songId[0]
                    audio_url = get_kuwo_song(songId)
                    if audio_url is not None:
                       audio_url = get_final_url(audio_url)
                       return MusicInfo(songId, song, singer, album, 0, audio_url, pic, MusicSource.URL.value)

            
    except Exception as ex:
        _LOGGER.error(ex)

def get_final_url(url):
    try:
        response = requests.get(url, allow_redirects=True)
        final_url = response.url.replace("https", "http")
        return final_url
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def search_kuwo_song(name):
        try:
            res = requests.get('https://music-api.gdstudio.xyz/api.php', params={
             'types': 'search',
             'source': 'kuwo',
             'name': name,
             "count": 1,
             "pages": 1
            })
            data = res.json()[0]
            return data.get('id')
            #return data.get('url').replace("https", "http")
        except Exception as ex:
            pass
def get_kuwo_song(id):
        try:
            res = requests.get('https://music-api.gdstudio.xyz/api.php', params={
             'types': 'url',
             'source': 'kuwo',
             'id': id,
             'br': ['999', '128'][1]
            })
            data = res.json()
            return data.get('url').replace("https", "http")
        except Exception as ex:
            pass
def getVipMusic_gdstudio(id):
        try:
            res = requests.get('https://music-api.gdstudio.xyz/api.php', params={
             'types': 'url',
             'source': 'netease',
             'id': id,
             'br': ['999', '320'][1]
            })
            data = res.json()
            return data.get('url').replace("https", "http")
        except Exception as ex:
            pass