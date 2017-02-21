# coding=utf-8
import re
import traceback

from requests.compat import urljoin
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from datetime import datetime, date


log = CPLog(__name__)


class Base(TorrentProvider):

    url = 'http://www.newpct.com'

    urls = {
        'search': 'http://www.newpct.com/index.php?l=%s&q="%s"&category_=%s&idioma_=%s&bus_de_=%s'
    }

    search_params = {
        'l': 'doSearch',
        'q': '',
        'category_': 'All',
        'idioma_': 1,
        'bus_de_': 'All'
    }

    cat_ids = [
        (['cam'], ['cam']),
        (['telesync'], ['ts', 'tc']),
        (['screener', 'tvrip'], ['screener']),
        (['x264', '720p', '1080p', 'blu-ray', 'hdrip'], ['bd50', '1080p', '720p', 'brrip']),
        (['dvdrip'], ['dvdrip']),
        (['dvd'], ['dvdr']),
    ]

    http_time_between_calls = 1  # Seconds
    cat_backup_id = None

    def _search(self, media, quality, results):

        data = self.getHTMLData(self.urls['search'] % (self.search_params['l'], getTitle(media), self.search_params['category_'], self.search_params['idioma_'], self.search_params['bus_de_']))
        log.debug('search Url = %s', self.urls['search'] % (self.search_params['l'], getTitle(media), self.search_params['category_'], self.search_params['idioma_'], self.search_params['bus_de_']))

        if data:

            table_order = ['age', 'name', 'size']

            try:
                html = BeautifulSoup(data)
                resultbody = html.find('table', attrs = {'id': 'categoryTable'}).find('tbody', recursive = False)
                try:
                    for temp in resultbody.find_all('tr'):
                        new = {}

                        nr = 0
                        tds = temp.find_all('td')
                        if len(tds) == 1:
                            continue
                        for td in tds:
                            column_name = table_order[nr]
                            if column_name:

                                if column_name == 'name':
                                    link = td.find('a')
                                    new['detail_url'] = td.find('a')['href']
                                    new['name'] = self._processTitle(link.get('title'), new['detail_url'])
                                    try:
                                        new['url'] = self.get_url(new['detail_url'])
                                    except:
                                        log.error('Failed getting url: %s', new['detail_url'])
                                        continue
                                    new['id'] = new['url']
                                    new['score'] = 100
                                elif column_name is 'size':
                                    new['size'] = self.parseSize(td.text)
                                elif column_name is 'age':
                                    new['age'] = self.ageToDays(td.text)
                                elif column_name is 'seeds':
                                    new['seeders'] = tryInt(td.text)
                                elif column_name is 'leechers':
                                    new['leechers'] = tryInt(td.text)

                            nr += 1

                        # Only store verified torrents
                        if self.conf('only_verified') and not new['verified']:
                            continue

                        results.append(new)
                except:
                    log.error('Failed parsing Newpct: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')

    def ageToDays(self, age_str):
        upload_date = datetime.strptime(age_str, "%d-%m-%y")
        today = date.today()
        age = today - upload_date.date()
        return age.days

    def get_url(self, url):
        data = self.getHTMLData(url)
        url = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

        return url

    @staticmethod
    def _processTitle(title, url):
        # Remove 'Mas informacion sobre ' literal from title
        title = title[22:]
        title = re.sub(r'[ ]{2,}', ' ', title, flags=re.I)

        # Quality - Use re module to avoid case sensitive problems with replace
        title = re.sub(r'\[HDTV 1080p?[^\[]*]', '1080p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[HDTV 720p?[^\[]*]', '720p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[ALTA DEFINICION 720p?[^\[]*]', '720p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[HDTV]', 'HDTV x264', title, flags=re.I)
        title = re.sub(r'\[DVD[^\[]*]', 'DVDrip x264', title, flags=re.I)
        title = re.sub(r'\[BluRay 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay Rip 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay Rip 720p?[^\[]*]', '720p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay MicroHD[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[MicroHD 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BLuRay[^\[]*]', '720p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BRrip[^\[]*]', '720p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BDrip[^\[]*]', '720p BluRay x264', title, flags=re.I)

        # detect hdtv/bluray by url
        # hdtv 1080p example url: http://www.newpct.com/descargar-seriehd/foo/capitulo-610/hdtv-1080p-ac3-5-1/
        # hdtv 720p example url: http://www.newpct.com/descargar-seriehd/foo/capitulo-26/hdtv-720p-ac3-5-1/
        # hdtv example url: http://www.newpct.com/descargar-serie/foo/capitulo-214/hdtv/
        # bluray compilation example url: http://www.newpct.com/descargar-seriehd/foo/capitulo-11/bluray-1080p/
        title_hdtv = re.search(r'HDTV', title, flags=re.I)
        title_720p = re.search(r'720p', title, flags=re.I)
        title_1080p = re.search(r'1080p', title, flags=re.I)
        title_x264 = re.search(r'x264', title, flags=re.I)
        title_bluray = re.search(r'bluray', title, flags=re.I)
        title_serie_hd = re.search(r'descargar\-seriehd', title, flags=re.I)
        url_hdtv = re.search(r'HDTV', url, flags=re.I)
        url_720p = re.search(r'720p', url, flags=re.I)
        url_1080p = re.search(r'1080p', url, flags=re.I)
        url_bluray = re.search(r'bluray', url, flags=re.I)

        if not title_hdtv and url_hdtv:
            title += ' HDTV'
            if not title_x264:
                title += ' x264'
        if not title_bluray and url_bluray:
            title += ' BluRay'
            if not title_x264:
                title += ' x264'
        if not title_1080p and url_1080p:
            title += ' 1080p'
            title_1080p = True
        if not title_720p and url_720p:
            title += ' 720p'
            title_720p = True
        if not (title_720p or title_1080p) and title_serie_hd:
            title += ' 720p'

        # Language
        title = re.sub(r'\[Spanish[^\[]*]', 'SPANISH AUDIO', title, flags=re.I)
        title = re.sub(r'\[Castellano[^\[]*]', 'SPANISH AUDIO', title, flags=re.I)
        title = re.sub(ur'\[Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.I)
        title = re.sub(ur'\[AC3 5\.1 Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.I)

        if re.search(r'\[V.O.[^\[]*]', title, flags=re.I):
            title += '-NEWPCTVO'
        else:
            title += '-NEWPCT'

        return title.strip()

config = [{
    'name': 'newpct',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Newpct',
            'description': 'Newpct is a free, fast and powerful search engine. <a href="http://www.newpct.com/" target="_blank">Newpct</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAQklEQVQ4y2NgAALjtJn/ycEMlGiGG0IVAxiwAKzOxaKGARcgxgC8YNSAwWoAzuRMjgsIugqfAUR5CZcBRIcHsWEAADSA96Ig020yAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True
                },
                {
                    'name': 'minimal_seeds',
                    'type': 'int',
                    'default': 1,
                    'advanced': True,
                    'description': 'Only return releases with minimal X seeds',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]
