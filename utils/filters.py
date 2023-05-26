import os

from telebot.custom_filters import SimpleCustomFilter
from .model import User


class LanguageFilter(SimpleCustomFilter):
    key = 'language'
    app = None

    def __init__(self, app):
        self.app = app

    @classmethod
    def check(self, message):
        from app_setup import create_app
        app = create_app(os.getenv("CONFIG"))
        app.app_context().push()
        user = User.query.filter_by(id=message.chat.id).first()
        if user:
            return user.language
        else:
            return None


class Deeplink(SimpleCustomFilter):
    key = 'is_deeplink'

    def check(self, message):
        return len(message.text.split()) > 1 and message.text.startswith('/start')


def parse_time(time_):
    import timeago
    _time = timeago.format(time_)
    new = _time.replace("days", "ቀናት").replace("weeks", "ሳምንታት").replace("months", "ወራት").replace("years", "አመታት")\
                  .replace("minutes", "ደቂቃዎች").replace("hours", "ሰዓታት").replace("seconds", "ሰከንድ").replace("few seconds", "ጥቂት ሰከንዶች")\
                  .replace("hour", "ሰዓት").replace("minute", "ደቂቃ").replace("day", "ቀን").replace("week", "ሳምንት")\
                  .replace("month", "ወር").replace("year", "አመት").replace("minute", "ደቂቃዎች").replace("ago", "በፊት").replace("just now", "አሁን")
    if new != "አሁን":
        new = "ከ" + new
    return new