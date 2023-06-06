import os
from datetime import datetime

import pymongo

db = pymongo.MongoClient(os.getenv("DATABASE"))['EthioSQBot']


class Query:
    __result = {}
    __args = {}
    __clas = None

    def __init__(self, clas):
        self.__coll = db[clas.__document__]
        self.__clas = clas
        self.__result = self.__coll.find()

    def filter_by(self, **kwargs):
        self.__result = self.__coll.find(kwargs)
        return self

    def limit(self, num: int):
        self.__result = self.__result.limit(num)
        return self

    def all(self) -> ['__clas']:
        return [self.__clas.de_json(res) for res in self.__result]

    def first(self) -> '__clas':
        try:
            result = self.__result.limit(1).next()
        except:
            result = {}

        return self.__clas.de_json(result)

    def count(self) -> int:
        return len([*self.__result])

    def insert_or_update(self, **kwargs):
        try:
            del kwargs['hash_link']
        except KeyError:
            pass
        exist = self.__coll.find_one({"_id": self.__clas.hash_link})

        if exist:
            return self.update(**kwargs)

        return self.__coll.insert_one(kwargs)

    def update(self, **kwargs):
        return self.__coll.update_one({'_id': self.__clas.hash_link}, {"$set": kwargs})

    def drop(self):
        self.__coll.drop()

    def delete(self):
        return self.__coll.delete_one({"_id": self.__clas.hash_link})


class Session:
    def add(self, cls):
        return self.query(cls).insert_or_update(**cls.get_dict())

    def delete(self, cls):
        return self.query(cls).delete()

    def __init__(self):
        self.query = Query


session = Session()


class Permission:
    ASK = 1
    ANSWER = 2
    SEND = 4
    SEE = 8
    MODERATE = 32
    BAN = 64
    MANAGE = 128
    ADMIN = 256


class Role:
    __document__ = 'roles'

    @classmethod
    def de_json(cls, json):
        if not json:
            return
        elif isinstance(json, list):
            return [cls(**j) for j in json]
        else:
            return cls(**json)

    def __repr__(self):
        return "<Role %s>" % self.name

    def __init__(self, name, permission=None, id=None, _id=None):

        self.id = id or session.query(self).count() + 1
        self.name = name
        self.permission = permission or 0
        self.hash_link = _id

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
            else:
                continue
            for perm in roles[r]:
                role.add_permission(perm)
            session.add(role)

    def get_dict(self):
        return self.__dict__


class Answer:
    __document__ = 'answers'

    @classmethod
    def de_json(cls, json):
        if json is None:
            return
        elif isinstance(json, list):
            return [cls(**j) for j in json]
        else:
            return cls(**json)

    def __init__(self, from_user_id, body, question_id, id=None, _id=None, status='preview', timestamp=datetime.utcnow(),
                 reply=0, message_id=None):
        self.id = id or session.query(self).count() + 1
        self.from_user_id = from_user_id
        self.question_id = question_id
        self.body = body
        self.hash_link = _id
        self.reply = reply
        self.timestamp = timestamp
        self.message_id = message_id
        self.status = status

    @property
    def from_user(self) -> "User":
        return session.query(User).filter_by(id=self.from_user_id).first()

    @property
    def question(self) -> "Question":
        return session.query(User).filter_by(id=self.from_user_id).first()

    def get_dict(self):
        new_dict = self.__dict__
        new_dict.pop("question")
        return new_dict


class QuestionSetting:
    @classmethod
    def de_json(cls, json):
        if json is None:
            return
        elif isinstance(json, list):
            return [cls(**j) for j in json]
        else:
            return cls(**json)

    def __init__(self, reply=True):
        self.reply = reply

    def get_dict(self):
        return self.__dict__


class BrowseAnswerLink:
    __document__ = 'b_a_links'

    @classmethod
    def de_json(cls, json):
        if not json:
            return
        else:
            return cls(**json)

    def __init__(self, question_id, _id=None):
        self.hash_link = _id
        self.question_id = question_id

    @property
    def question(self) -> "Question":
        return session.query(Question).filter_by(id=self.question_id).first()

    def get_dict(self):
        return self.__dict__


class Question:
    __document__ = 'questions'

    @classmethod
    def de_json(cls, json):

        if isinstance(json, list):
            return [cls(**j) for j in json]
        elif not json:
            return
        else:
            return cls(**json)

    def __init__(self, asker_id, body, subject, id=None, timestamp=datetime.utcnow(), status='preview', _id=None,
                 message_id=None, setting=QuestionSetting(reply=True)):
        self.id = id or session.query(self).count() + 1
        self.asker_id = asker_id
        self.body = body
        self.hash_link = _id
        self.subject = subject
        self.timestamp = timestamp
        self.status = status
        self.message_id = message_id
        self.setting = setting

    @property
    def asker(self) -> "User":
        return session.query(User).filter_by(id=self.asker_id).first()

    @property
    def answers(self) -> [Answer]:
        return session.query(Answer).filter_by(question_id=self.id).all()

    @property
    def browse_link(self) -> str:
        return session.query(BrowseAnswerLink).filter_by(question_id=self.id).first().hash_link

    def get_dict(self):
        new_dict = {}
        for k, v in self.__dict__.items():
            if k in ['hash_link']:
                continue
            new_dict[k] = v

        new_dict['setting'] = self.setting.get_dict()
        return new_dict

    def __repr__(self):
        return "<Question %d>" % self.id


class User:
    __document__ = "users"

    @classmethod
    def de_json(cls, json):
        if not json:
            return
        else:
            return cls(**json)

    def __init__(self, id, name="ተማሪ", since_member=datetime.utcnow(), language=None,
                 bio='', gender='', role_id=None, _id=None):
        self.id = id
        self.name = name
        self.since_member = since_member
        self.language = language
        self.bio = bio
        self.gender = gender
        self.hash_link = _id
        if role_id is None:
            if self.id == int(os.getenv("ADMIN_ID")):
                self.role_id = 3#session.query(Role).filter_by(name='admin').first().id
            else:
                self.role_id = 2#session.query(Role).filter_by(name='user').first().id
        else:
            self.role_id = role_id

    @property
    def role(self) -> Role:
        return session.query(Role).filter_by(id=self.role_id).first()

    @property
    def questions(self) -> [Question]:
        return session.query(Question).filter_by(asker_id=self.id).all()

    @property
    def answers(self) -> [Answer]:
        return session.query(Answer).filter_by(from_user_id=self.id).all()

    def can(self, perm) -> bool:
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self) -> bool:
        return self.can(Permission.ADMIN)
    
    def get_dict(self):
        new_dict = self.__dict__
        return new_dict

    def __repr__(self):
        return "<User %s>" % self.name
