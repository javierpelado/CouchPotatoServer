from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.newpct import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Newpct'


class Newpct(MovieProvider, Base):
    pass
