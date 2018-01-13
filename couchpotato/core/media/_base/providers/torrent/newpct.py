
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
        'search': 'http://www.newpct.com/index.php?l=%s&q="%s"&category_=%s&idioma_=%s&bus_de_=%s',
        'postSearch': 'http://www.newpct.com/buscar'
    }

    search_params = {
        'l': 'doSearch',
        'q': '',
        'category_': 'All',
        'idioma_': 1,
        'bus_de_': 'All'
    }

    post_search_params = {
        'pg': '',
        'categoryIDR': 1027,
        'categoryID': '',
        'idioma': 1,
        'calidad': '',
        'ordenar': 'Fecha',
        'inon': 'Descendente',
        'q': ''
    }

    search_cat_ids = [757, 778, 1027, 1599, 1921, 3049]

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

        daysFromReleased = self.daysFromReleased(media['info'])

        for search_cat_id in self.search_cat_ids:

            self.post_search_params['q'] = getTitle(media)
            self.post_search_params['categoryIDR'] = search_cat_id
            data = self.getHTMLData(self.urls['postSearch'], data=self.post_search_params)
            log.debug('search Url = %s', self.urls['search'] % (self.search_params['l'], getTitle(media), self.search_params['category_'], self.search_params['idioma_'], self.search_params['bus_de_']))

            if data:

                table_order = ['age', 'name', 'size']

                try:
                    html = BeautifulSoup(unicode(data, "latin-1"))
                    result_list = html.find('ul', 'buscar-list')
                    try:
                        for temp in result_list.find_all('div', 'info'):
                            new = {}

                            try:
                                new['detail_url'] = temp.find('a')['href']
                                new['url'] = new['detail_url']
                                new['name'] = self._processTitle(temp.find('h2').text, new['detail_url'])
                                new['id'] = new['name']

                                spans = temp.find_all('span')
                                new['age'] = self.ageToDays(spans[1].text)
                                new['size'] = self.parseSize(spans[2].text)

                            except:
                                log.error('Failed parsing result: %s', td)
                                continue

                            # Only store verified torrents
                            if self.conf('only_verified') and not new['verified']:
                                continue

                            if daysFromReleased and (daysFromReleased < new['age']):
                                continue

                            results.append(new)
                    except:
                        log.error('Failed parsing Newpct: %s', traceback.format_exc())

                except AttributeError:
                    log.debug('No search results found.')

    def daysFromReleased(self, info):
        try:
            return self.ageToDays(info['released'], "%Y-%m-%d")
        except:
            return False

    def ageToDays(self, age_str, pattern="%d-%m-%Y"):
        upload_date = datetime.strptime(age_str, pattern)
        today = date.today()
        age = today - upload_date.date()
        return age.days

    def get_url(self, url):

        url = url.replace('newpct.com', 'tumejortorrent.com')
        data = self.getHTMLData(url)
        url = re.search(r'http://tumejortorrent.com/descargar-torrent/\d+_[^\"]+', data, re.DOTALL).group()

        return url

    def download(self, url = '', nzb_id = ''):
        try:
            url = self.get_url(url)
        except:
            log.error('Error getting torrent from details page: %s', url)
        return super(Base, self).download(url,nzb_id)

    @staticmethod
    def _processTitle(title, url):
        title = re.sub(r'\]\[', '] [', title, flags=re.I)
        # Quality - Use re module to avoid case sensitive problems with replace
        title = re.sub(r'\[HDTV 1080p?[^\[]*]', '1080p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[HDTV 720p?[^\[]*]', '720p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[ALTA DEFINICION 720p?[^\[]*]', '720p HDTV x264', title, flags=re.I)
        title = re.sub(r'\[HDTV]', 'HDTV x264', title, flags=re.I)
        title = re.sub(r'\[DVD[^\[]*]', 'DVDrip x264', title, flags=re.I)
        title = re.sub(r'\[BluRay 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay Rip 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay 720p?[^\[]*]', '720p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay Rip 720p?[^\[]*]', '720p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay MicroHD[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[MicroHD 1080p?[^\[]*]', '1080p BluRay x264', title, flags=re.I)
        title = re.sub(r'\[BluRay[^\[]*]', '720p BluRay x264', title, flags=re.I)
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
        title = re.sub(ur'\[AC3 5\.1 Castellano[^\[]*]', 'SPANISH AUDIO', title, flags=re.I)

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
