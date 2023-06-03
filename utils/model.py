from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime, BigInteger, Boolean, Text
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.orm import Session, relationship
from datetime import datetime
import os

engine = create_engine(os.getenv("DATABASE"))
session = Session(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=False)
    name = Column(String(50), nullable=False, default='ተማሪ')
    since_member = Column(DateTime(), default=datetime.utcnow)
    language = Column(String(10))
    bio = Column(String(100))
    gender = Column(String(6), default='')
    questions = relationship("Question", backref='asker')
    answers = relationship("Answer", backref='from_user')
    hash_link = Column(String(20))
    role_id = Column(Integer, ForeignKey('roles.id'))

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.gender is None:
            self.gender = ''
        if self.role is None:
            if self.id == os.getenv("ADMIN_ID"):
                self.role = session.query(Role).filter_by(name='admin').first()
            else:
                self.role = session.query(Role).filter_by(name='user').first()

        if self.hash_link is None:
            self.hash_link = self.generate_link

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.ADMIN)

    @property
    def generate_link(self):
        import hashlib
        return hashlib.sha1(str(self.id).encode()).hexdigest()

    def __repr__(self):
        return "<User %s>" % self.name


class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, nullable=False)
    asker_id = Column(BigInteger, ForeignKey('users.id'))
    body = Column(Text, nullable=False)
    hash_link = Column(String(20), nullable=False, unique=True)
    subject = Column(String(20), nullable=False)
    timestamp = Column(DateTime(), default=datetime.utcnow)
    status = Column(String(20), default='preview')
    browse_link = Column(String(20), nullable=False, unique=True)
    message_id = Column(Integer)
    setting_id = Column(Integer, ForeignKey('on_question.id'))
    answers = relationship("Answer", backref='question')

    def __init__(self, **kwargs):
        super(Question, self).__init__(**kwargs)
        if self.hash_link is None:
            self.hash_link = self.generate_link
        if self.browse_link is None:
            self.browse_link = self.generate_browse_link
        if self.setting is None:
            self.setting = QuestionSetting()

    @property
    def generate_link(self):
        import hashlib
        max_id = session.query(Question).count()
        return hashlib.sha224(str(max_id + 1).encode()).hexdigest()

    @property
    def generate_browse_link(self):
        import hashlib
        max_id = session.query(Question).count()
        return hashlib.md5(str(~(max_id + 1)).encode()).hexdigest()

    def __repr__(self):
        return "<Question by %s>" % self.asker


class QuestionSetting(Base):
    __tablename__ = 'on_question'
    id = Column(Integer, primary_key=True)
    question = relationship('Question', backref='setting')
    reply = Column(Boolean, default=True)


class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True, nullable=False)
    from_user_id = Column(BigInteger, ForeignKey('users.id'))
    question_id = Column(Integer, ForeignKey('questions.id'))
    body = Column(Text, nullable=False)
    hash_link = Column(String(128), nullable=False, unique=True)
    reply = Column(Integer)
    timestamp = Column(DateTime(), default=datetime.utcnow)
    message_id = Column(Integer)
    status = Column(String(20), default='preview')

    def __init__(self, *args, **kwargs):
        super(Answer, self).__init__(**kwargs)
        if self.hash_link is None:
            self.hash_link = self.generate_link

    @property
    def generate_link(self):
        import hashlib
        max_id = session.query(Answer).count()
        return hashlib.sha512(str(~(max_id + 1)).encode()).hexdigest()


class Permission:
    ASK = 1
    ANSWER = 2
    SEND = 4
    SEE = 8
    MODERATE = 32
    BAN = 64
    MANAGE = 128
    ADMIN = 256


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False, unique=True)
    permission = Column(Integer, nullable=False)
    user = relationship("User", backref='role')

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
            role = session.query(Role).filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            session.add(role)
        session.commit()


Base.metadata.create_all(engine)
Role.insert_roles()
