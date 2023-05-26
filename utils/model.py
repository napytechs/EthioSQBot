from app_setup import db
from datetime import datetime
import os


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, default='ተማሪ')
    since_member = db.Column(db.DateTime(), default=datetime.utcnow)
    language = db.Column(db.String(10))
    bio = db.Column(db.String(100))
    gender = db.Column(db.String(6), default='')
    questions = db.relationship("Question", backref='asker', lazy='dynamic')
    answers = db.relationship("Answer", backref='from_user', lazy='dynamic')
    joined = db.Column(db.Boolean, default=False)
    hash_link = db.Column(db.String(64))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.gender is None:
            self.gender = ''
        if self.role is None:
            if self.id == int(os.getenv('FLASK_ADMIN_ID')):
                self.role = Role.query.filter_by(name='admin').first()
            if self.role is None:
                self.role = Role.query.filter_by(name='user').first()
    
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.ADMIN)

    def generate_link(self):
        import hashlib
        max_id = self.query.count()
        self.hash_link = hashlib.sha256(str(max_id + 1).encode()).hexdigest()

    def __repr__(self):
        return "<User %s>" % self.name


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    asker_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    body = db.Column(db.String(4000), nullable=False)
    hash_link = db.Column(db.String(128), nullable=False, unique=True)
    subject = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    status = db.Column(db.String(20), default='previewing')
    setting = db.relationship("QuestionSetting", backref='onquestion', lazy='dynamic')
    browse_link = db.Column(db.String(64), nullable=False, unique=True)
    message_id = db.Column(db.Integer)

    def __init__(self, *args, **kwargs):
        if self.setting is None:
            self.setting = QuestionSetting(reply=True)

    def generate_link(self):
        import hashlib
        max_id = self.query.count()
        self.hash_link = hashlib.sha512(str(max_id+1).encode()).hexdigest()

    def generate_browse_link(self):
        import hashlib
        max_id = self.query.count()
        self.browse_link = hashlib.sha256(str(~(max_id+1)).encode()).hexdigest()

    def __repr__(self):
        return "<Question by %s>" % self.asker


class QuestionSetting(db.Model):        
    __tablename__ = 'questionSetting'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    reply = db.Column(db.Boolean, default=True)


class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    from_user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    body = db.Column(db.String(4000), nullable=False)
    hash_link = db.Column(db.String(128), nullable=False, unique=True)
    reply = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    message_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default='preview')

    def generate_link(self):
        import hashlib
        max_id = self.query.count()
        self.hash_link = hashlib.sha512(str(~(max_id+1)).encode()).hexdigest()


class Permission:
    ASK = 1
    ANSWER = 2
    SEND = 4
    SEE = 8
    MODERATE = 32
    BAN = 64
    MANAGE = 128
    ADMIN = 256


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    name = db.Column(db.String(10), nullable=False)
    permission = db.Column(db.Integer, nullable=False)
    user = db.relationship("User",  backref='role', lazy='dynamic')

    def __repr__(self):
        return "<Role %s>" % self.name

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)

        if self.permission is None:
            self.permission = 0

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permission += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permission -= perm

    def reset_permissions(self):
        self.permission = 0

    def has_permission(self, perm):
        return self.permission & perm == perm

    def return_permission(self):
        self.add_permission(Permission.ASK)
        self.add_permission(Permission.ANSWER)

    @staticmethod
    def insert_roles():
        roles = {
            'banned': [0],
            'user': [Permission.ASK, Permission.ANSWER],
            'moderator': [Permission.ANSWER, Permission.ASK, Permission.MODERATE, Permission.SEE, Permission.SEND],
            'admin': [Permission.ASK, Permission.ANSWER, Permission.MODERATE, Permission.ADMIN,
                      Permission.BAN, Permission.MANAGE, Permission.SEE, Permission.SEND]
        }
        
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            db.session.add(role)
        db.session.commit()
