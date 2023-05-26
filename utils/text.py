from .filters import parse_time


class Text:
    def __init__(self, user):
        self.user = user

    @property
    def welcome(self):
        if self.user.language == 'amharic':
            return '''🏠 <b>እንኳን በደህና መጡ!!</b>\n
✳ ይህ ቦት ለኢትዮጵያውያን ተማሪዎች የተዘጋጀ፤ የጥያቄና መልስ መድረክ ነው።\n
✅ ይጠይቁ ፣ ይሳተፉ።
'''
        else:
            return '''🏠 <b>Welcome!</b>\n
✳ This bot is question and answer platform made for Ethiopian students.\n
✅ Ask and participate.
'''

    @property
    def profile(self):
        import timeago
        name = self.user.name + self.user.gender
        if self.user.language == 'english':
            return '<b>%s</b>\n<b>Asked questions: </b>%s\n' \
                   '<b>Answered questions</b> %s\n\n<b>%s</b>\n<i>Joined: %s</i>' % (name,
                                                                                     self.user.questions.count(),
                                                                                     self.user.answers.count(),
                                                                                     self.user.bio,
                                                                                     timeago.format(self.user.since_member))
        else:
            return '<b>%s</b>\n<b>የጠየቁት ጥያቄ </b>%s\n' \
                   '<b>የመለሱት ጥያቄ %s</b>\n\n<b>%s</b>\n<i>የተቅላቀሉት %s</i>' % (name,
                                                                                self.user.questions.count(),
                                                                                self.user.answers.count(),
                                                                                self.user.bio,
                                                                                parse_time(self.user.since_member))

    @property
    def question(self):
        if self.user.language == 'english':
            return "<code>Send the question you want to ask through text</code>"
        else:
            return "<code>መጠየቅ ሚፈልጉትን ጥያቄ በጽሁፍ መልክ ይላኩ</code>"

    @property
    def answer(self):
        if self.user.language == 'english':
            return "<code>Send your answer through text</code>"
        else:
            return "<code>እባኮን ምላሾን በጽሁፍ መልክ ይላኩ</code>"

    def user_profile(self, this):
        import timeago
        name = self.user.name + self.user.gender

        if this.language == 'amharic':
            return '<b>%s</b> |%d <b>ተከታይ</b> |%d <b>ተከታታይ</b>\n<b>የጠየቁት ጥያቄ </b>%s\n' \
                   '<b>የመለሱት ጥያቄ <b>%s</b>\n\n<b>%s</b>\n<i>የተቅላቀሉት %s</i>' % (name,
                                                                                self.user.followers.count(),
                                                                                self.user.following.count(),
                                                                                self.user.questions.count(),
                                                                                self.user.answers.count(),
                                                                                self.user.bio,
                                                                                parse_time(self.user.since_member))
        else:
            return '<b>%s</b>|%d <b>Followers</b> |%d <b>Following</b>\n<b>Asked questions: </b>%s\n' \
                   '<b>Answered questions</b> %s\n\n<b>%s</b>\n<i>Joined: %s</i>' % (name,
                                                                                     self.user.followers.count(),
                                                                                     self.user.following.count(),
                                                                                     self.user.questions.count(),
                                                                                     self.user.answers.count(),
                                                                                     self.user.bio,
                                                                                     timeago.format(
                                                                                         self.user.since_member))
