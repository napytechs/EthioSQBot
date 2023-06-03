import os
from flask import Flask, request
from telebot import apihelper, TeleBot, types
import re
from typing import Union
from telebot.apihelper import ApiTelegramException
from telebot.custom_filters import StateFilter, ChatFilter
from utils import filters
from utils.filters import Deeplink, LanguageFilter
from utils.text import Text
from button.keyboard import *
from utils.model import User, Role, Answer, Question, Permission, QuestionSetting, session

apihelper.ENABLE_MIDDLEWARE = True
TOKEN = os.getenv("TOKEN")
bot = TeleBot(TOKEN, parse_mode='html')
app = Flask(__name__)

DEEPLINK = 'http://t.me/{0}?start='.format(bot.get_me().username)
MAINTAIN = False
PENDING = False
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
OWNER_ID = int(os.getenv('ADMIN_ID'))
markups = {}
WEBHOOK = os.getenv("WEBHOOK")


@bot.middleware_handler(update_types=['message'])
def get_updates(bot_instance, update: Union[types.Update, types.Message]):
    user_id = update.from_user.id

    if update.chat.type == 'private':
        user = session.query(User).filter_by(id=user_id).first()
        if user is not None and user.role.permission == 0:
            update.content_type = 'banned'
        elif MAINTAIN:
            update.content_type = 'maintain'
        elif user is not None and not check_join(user_id) and user.language is not None:
            update.content_type = 'not_join'


def check_join(user_id: int):
    try:
        user = bot.get_chat_member(CHANNEL_ID, user_id)
        return user.status in ['creator', 'administrator', 'member']
    except ApiTelegramException as err:
        if 'chat not found' in err.description:
            return True
        return False


@bot.message_handler(content_types=['not_join'])
def not_joined(message: types.Message):
    user = message.from_user
    username = bot.get_chat(CHANNEL_ID).username
    btn = InlineKeyboardMarkup([[InlineKeyboardButton('ይ🀄️ላ🀄️ሉ', f't.me/{username}')]])
    bot.send_message(user.id, f'''<b>ውድ {user.first_name}</b>
• ይህን ቦት በቋሚነት ለመጠቀም አባኮ ብቅድሚያ ማሰራጭያችንን ይቀላቀሉ 😊።''', reply_markup=btn)


@bot.message_handler(content_types=['banned'])
def banned(message):
    user_id = message.from_user.id
    bot.send_message(user_id, '<b>ይቅርታ ይሄን ቦት ከመጠቀም ታግደዋል፤ እባኮን ዋና አስተዳዳሪውን ያግኙ።</b>')


@bot.message_handler(content_types=["maintain"])
def maintain(message: types.Message):
    bot.send_message(message.from_user.id,
                     "📌 እናንተን በተሻለ መልኩ ለማገልገል ቦቱ በጥገና ላይ ነው፤ እባኮን ተንሽ ቆይተው እንደገና ይሞክሩ።\n\nእናመሰግናለን!!")


@bot.message_handler(commands=['start'], chat_types=['private'], is_deeplink=False)
def start_message(message: types.Message):
    user_id = message.chat.id
    _user = session.query(User).filter_by(id=user_id).first()
    if _user is None:
        new_user = User(id=user_id)
        session.add(new_user)
        session.commit()
        return bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button(True))

    user: User = session.query(User).filter_by(id=user_id).first()
    _text = Text(user)

    if user.language is None:
        text = "<i>Select your langauge / ቋንቋ ይምረጡ</i>"
        btn = lang_button()
    else:
        text = _text.welcome
        btn = main_button(user)
    bot.send_message(user_id, text, reply_markup=btn)
    bot.delete_state(user_id)


def mention(user: User):
    return "<a href='%s'>%s</a> %s" % (DEEPLINK + user.hash_link, user.name, user.gender)


@bot.message_handler(commands=['start'], is_deeplink=True, chat_types=['private'])
def __start(message: types.Message):
    user_id = message.chat.id
    text = message.text.split()[-1]
    question: Question = session.query(Question).filter_by(browse_link=text).first()
    answer: Answer = session.query(Question).filter_by(hash_link=text).first()
    user: User = session.query(User).filter_by(hash_link=text).first()
    current_user: User = session.query(User).filter_by(id=user_id).first()
    bot.delete_state(user_id)

    if current_user is None:
        return start_message(message)

    elif current_user.language is None:
        return start_message(message)

    if user is not None:
        text = Text(user)
        if user.id == user_id:
            if user.language == 'english':
                message.text = "👤 Profile"
                return en_button(message)
            else:
                message.text = "👤 መግለጫ"
                return am_button(message)
        else:
            
            bot.send_message(user_id, text.profile, reply_markup=on_user_profile(user, current_user))

    elif question is not None:
        btn = InlineKeyboardMarkup([[
                                    InlineKeyboardButton("መልስ", callback_data=f'answer:{question.id}')]])

        text = f"#{question.subject}\n\n<b>{question.body}</b>\n\nበ {mention(question.asker)} የተጠየቀ"
        bot.send_message(user_id, text, reply_markup=btn)
        show_answers(user_id, question.id)

    elif answer is not None:
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"ዝርዝር({len(answer.answers)})",
                                                          callback_data=f'browse_answer:{answer.id}')
                                     ]])

        text = f"#{answer.subject}\n\n<b>{answer.body}</b>\n\nበ {mention(answer.asker)} የተጠየቀ"
        bot.send_message(user_id, text, reply_markup=btn)
        text = Text(current_user)
        bot.send_message(user_id, text.answer, reply_markup=cancel(current_user) if answer.status != 'closed' else None)
        if answer.status == 'closed': return
        bot.set_state(user_id, "get_answer")
        with bot.retrieve_data(user_id) as data:
            data['question_id'] = answer.id
    else:
        start_message(message)


def parse_text_to_user(text: str, user):
    txt = {'{name}': user.name, '{mention}': user.mention, '{user_id}': user.user_id, '{date}': user.date,
           '{balance}': user.balance}

    for old, new in txt.items():
        text = text.replace(old, new)

    return text


@bot.callback_query_handler(lambda call: call.data.startswith('lang'))
def update_lang(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "በመጫን ላይ....")
    user_id = call.message.chat.id
    code = call.data.split(":")[-1]
    user = session.query(User).filter_by(id=user_id).first()

    if code.endswith('f'):
        code = code.replace('f', '')
        _code = 'amharic' if code == 'am' else 'english'
        user.language = _code
        session.add(user)
        session.commit()
        text = Text(user)
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, text.welcome, reply_markup=main_button(user))
    else:
        _code = 'amharic' if code == 'am' else 'english'
        user.language = _code
        session.add(user)
        session.commit()
        bot.delete_message(user_id, call.message.message_id)

        send_menu(user_id)


@bot.callback_query_handler(lambda call: call.data == "ask_question")
def ask_question(call: types.CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user = session.query(User).get(call.message.chat.id)
    if user.language == "english":
        call.message.text = "📝 Ask Question"
        en_button(call.message)
    else:
        call.message.text = "📝 ጠይቅ"
        am_button(call.message)


@bot.message_handler(func=lambda msg: msg.text == "❌ Cancel", language="english",
                     chat_types=['private'], state="*")
def en_cancel(message: types.Message):
    user_id = message.chat.id
    state = bot.get_state(user_id)
    user = session.query(User).filter_by(id=user_id).first()
    text = Text(user)
    if state in ["edit_question", "edit_subject"]:
        with bot.retrieve_data(user_id) as data:
            question_id = data["question_id"]
            send_question(user_id, question_id)

    elif state in ["edit_name", "edit_bio", "edit_username"]:
        bot.send_message(user_id, text.profile, reply_markup=user_button(user))

    elif state == 'edit_answer':
        with bot.retrieve_data(user_id) as data:
            answer_id = data['answer_id']
            msg_id = data['message_id']
        answer = session.query(Answer).filter_by(id=answer_id).first()
        text = f"<b>{answer.body}</b>\n\nበ {mention(user)} የተመለሰ"
        bot.send_message(user_id, text, reply_markup=on_answer_button(answer_id, msg_id))

    bot.delete_state(user_id)
    send_menu(user_id)


@bot.message_handler(func=lambda msg: msg.text == "❌ ሰርዝ", language="amharic", chat_types=['private'],
                     state="*")
def am_cancel(message: types.Message):
    user_id = message.from_user.id
    state = bot.get_state(user_id)
    user = session.query(User).filter_by(id=user_id).first()
    if state in ["edit_question", "edit_subject"]:
        with bot.retrieve_data(user_id) as data:
            question_id = data["question_id"]
            send_question(user_id, question_id)

    elif state in ["edit_name", "edit_bio", "edit_username"]:
        text = Text(user)
        bot.send_message(user_id, text.profile, reply_markup=user_button(user))

    elif state == 'edit_answer':
        with bot.retrieve_data(user_id) as data:
            answer_id = data['answer_id']
            msg_id = data['message_id']
        send_answer(user_id, answer_id, msg_id)

    bot.delete_state(user_id)
    return send_menu(user_id)


@bot.message_handler(state='message', content_types=util.content_type_media, chat_types=['private'])
def got_message(message: types.Message):
    user_id = message.chat.id
    msg_id = message.message_id
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(
        types.InlineKeyboardButton("➕ ጨምር", callback_data=f'sm:add'),
        types.InlineKeyboardButton("☑ አልቋል", callback_data=f'sm:done'),
        types.InlineKeyboardButton("🗑 አጥፋ", callback_data='sm:del')
    )
    bot.delete_state(user_id)
    bot.copy_message(user_id, user_id, msg_id, reply_markup=btn)
    send_menu(user_id)


@bot.callback_query_handler(func=lambda call: re.match('^sm', call.data))
def on_got_message(call: types.CallbackQuery):

    bot.answer_callback_query(call.id)
    data = call.data.split(':')[-1]
    user_id = call.message.chat.id
    user = session.query(User).filter_by(id=user_id)
    if data == 'add':
        bot.send_message(call.message.chat.id,
                         "የአዝራርህን ጽሁፍና ማያያዢያውን ክሰር ባለው መልኩ ይላኩ:\n\n<code>ሙከራ -> www.text.com</code>",
                         reply_markup=cancel(user.language))
        bot.set_state(user_id, 'add_btn')
        with bot.retrieve_data(user_id) as data:
            data["msg_id"] = call.message.message_id

    elif data == 'del':
        bot.answer_callback_query(call.id, "መላዕክቱ ጠፍቷል!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_menu(user_id)
        bot.delete_state(user_id)
    else:
        bot.answer_callback_query(call.id, "በመላክ ላይ.......", show_alert=True)
        bot.delete_state(user_id)
        bot.edit_message_reply_markup(user_id, call.message.message_id)
        send_menu(user_id)
        send_to_users(call.message)


@bot.message_handler(state='add_btn')
def on_send_btn(msg: types.Message):
    text = msg.text
    match = re.findall(r".+\s*->\s*.+", text)
    with bot.retrieve_data(msg.chat.id) as data:
        msg_id = data['msg_id']
    if match:
        btns = {k.split('->')[0]: k.split('->')[1] for k in match}
        for k, v in btns.items():
            markups[k] = {'url': v.lstrip()}
        try:
            del markups["➕ ጨምር"], markups["☑ አልቋል"], markups['🗑 አጥፋ']
        except (IndexError, KeyError):
            pass

        try:
            markups["➕ ጨምር"] = {'callback_data': f'sm:add'}
            markups["☑ አልቋል"] = {'callback_data': f'sm:done'}
            markups["🗑 አጥፋ"] = {'callback_data': 'sm:del'}
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
        except ApiTelegramException:
            for bt in btns:
                del markups[bt]
            bot.reply_to(msg, "❌ ከአገልግሎት ውጪ የሆነ ማያያዢያ ...")
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    else:
        markups["➕ ጨምር"] = {'callback_data': f'sm:add'}
        markups["☑ አልቋል"] = {'callback_data': f'sm:done'}
        markups["🗑 አጥፋ"] = {'callback_data': 'sm:del'}
        bot.reply_to(msg, "❌ የተሳሳት ጽሁፍ...")
        bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    bot.delete_state(msg.chat.id)
    send_menu(msg.chat.id)


def send_to_users(message: types.Message):
    try:
        del markups["➕ ጨምር"], markups["☑ አልቋል"], markups['🗑 አጥፋ']
    except (IndexError, KeyError):
        pass

    users = session.query(User.id).all()
    for user_id in users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id, reply_markup=util.quick_markup(markups))
        except:
            continue
    markups.clear()


def send_menu(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    if user.language == 'english':
        bot.send_message(user_id, "🏠 Main menu", reply_markup=main_button(user))

    elif user.language == "amharic":
        bot.send_message(user_id, "🏠 ዋና ገጽ", reply_markup=main_button(user))
    else:
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())


@bot.callback_query_handler(func=lambda call: call.data.startswith('pagin'))
def on_pagination(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    page = call.data.split("=")[-1]
    page = int(page)
    users = session.query(User).order_by(User.since_member.desc())
    btn = pagination_button(page, users.count())
    text = ''
    count = page * 10 - 10
    for user in users.limit(10):
        count += 1
        text += "<i>#%d.</i> %s\n\n" % (count, mention(user))
    text += "\nየታየ - %d ፤ አጠቃላይ - %d" % (count, users.count())
    bot.edit_message_text(text, inline_message_id=call.inline_message_id, reply_markup=btn)


class UserState:
    get_question = 'get_question'
    get_subject = 'get_subject'


@bot.message_handler(state=UserState.get_question, content_types=util.content_type_media)
def get_question(message: types.Message):
    user_id = message.chat.id
    user = session.query(User).filter_by(id=user_id).first()
    if not message.text:
        bot.send_message(user_id, Text(user).question)
    else:
        bot.send_message(user_id, "<code>ለጥያቄዎ ርዕስ ይምረጡ....\n\nየትኛዉን መምረጥ እንዳለቦት ግራከገቦት፣ `ጠቅላላ እውቀት` ሚለውን ይጫኑ</code>", reply_markup=subject_button())
    bot.set_state(user_id, UserState.get_subject)
    body = util.escape(message.text)
    with bot.retrieve_data(user_id) as data:
        data['question'] = body


@bot.message_handler(state=UserState.get_subject)
def get_subject(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = session.query(User).filter_by(id=user_id).first()

    if text not in subject_text:
        bot.send_message(user_id, "<code>ለጥያቄዎ ርዕስ ይምረጡ....\n\nየትኛዉን መምረጥ እንዳለቦት ግራከገቦት፣ `ጠቅላላ እውቀት` ሚለውን ይጫኑ</code>",
                         reply_markup=subject_button())
    else:
        subject = filters.smart_subject(text)
        with bot.retrieve_data(user_id) as data:
            body = data['question']

        question = Question(body=body, subject=subject, asker=user)
        session.add(question)
        session.commit()
        send_question(user_id, question.id)
        send_menu(user_id)
        return bot.delete_state(user_id)


@bot.callback_query_handler(lambda call: re.search(r'edit:(subject|question|enable|disable)', call.data))
def __edit_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    msg_id = call.message.message_id
    question_id = int(call.data.split(":")[-1])
    content = call.data.split(':')[-2]
    question = session.query(Question).filter_by(id=question_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    text = Text(user)

    bot.edit_message_reply_markup(user_id, msg_id)
    if question.status is None:
        return bot.send_message(user_id, "ይህ ጥያቄ የለም።")

    elif question.status != 'previewing':
        bot.delete_message(user_id, msg_id)
        return bot.answer_callback_query(call.id, "ይህ ጥያቄ አርትዕ መደረግ አይችልም", show_alert=True)

    if content == 'question':
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, text.question, reply_markup=cancel(user.language))
        state = 'edit_question'

    elif content == 'subject':
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "<code>ለጥያቄዎ ርዕስ ይምረጡ...\n\nየትኛዉን መምረጥ እንዳለቦት ግራከገቦት፣ `ጠቅላላ እውቀት` ሚለውን ይጫኑ</code>", reply_markup=subject_button())
        state = 'edit_subject'

    elif content == 'enable':
        bot.answer_callback_query(call.id, "መመለስ ይቻላል።\n\nሁሉም ሰው ለርሶ ጥያቄ ለተመለሱት መልሶች ምላሽ መስጥት ይችላል።", show_alert=True)
        question.setting = QuestionSetting(reply=True)
        session.add(question)
        session.commit()
        bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_question_button(user, question_id, True))
        return

    else:
        question.setting.reply = False
        session.add(question)
        session.commit()
        bot.answer_callback_query(call.id, "መመለስ አይቻልም\n\nከርሶ ውጪ፤ ማንም ሰው ለርሶ ጥያቄ ለተመለሱት መልሶች ምላሽ መስጥት አልም።",
                                  show_alert=True)
        bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_question_button(user, question_id, False))
        return

    bot.set_state(user_id, state)
    with bot.retrieve_data(user_id) as data:
        data['question_id'] = question_id


@bot.message_handler(state='edit_question', content_types=util.content_type_media)
def edit_question(message: types.Message):
    user_id = message.chat.id
    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']

    if not message.text:
        bot.send_message(user_id, "እባኮ ጥያቄዎን በጽሁፍ መልክ ይላኩ።")

    question = session.query(Question).filter_by(id=question_id).first()
    question.body = util.escape(message.text)
    session.add(question)
    session.commit()
    send_question(user_id, question_id)
    send_menu(user_id)
    return bot.delete_state(user_id)


@bot.message_handler(state='edit_subject')
def edit_subject(message: types.Message):
    user_id = message.chat.id
    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']

    text = message.text
    if text not in subject_text:
        bot.send_message(user_id, "<code>ለጥያቄዎ ርዕስ ይምረጡ...\n\nየትኛዉን መምረጥ እንዳለቦት ግራከገቦት፣ `ጠቅላላ እውቀት` ሚለውን ይጫኑ</code>", reply_markup=subject_button())

    else:
        subject = text[2:].strip().replace(" ", "_").lower()
        if subject == "አማርኛ":
            subject = 'amharic'

        question = session.query(Question).filter_by(id=question_id).first()
        question.subject = subject
        session.add(question)
        session.commit()
        send_question(user_id, question_id)
        send_menu(user_id)
        return bot.delete_state(user_id)


def send_question(user_id, question_id):
    new_question = session.query(Question).filter_by(id=question_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    text = f"#{new_question.subject}\n\n<b>{new_question.body}</b>\n\nበ {mention(user)} የተጠይቀ\n\n"
    bot.send_message(user_id, text, reply_markup=on_question_button(user, question_id, new_question.setting.reply))
    bot.send_message(user_id, "ጥያቄዎትን ተመልክተዉ እንደጨርሱ ለጥፍ የሚለዉን አዝራር ይጫኑ፤ ይህም በቀጥታ ማሰራጪያችን ላይ እንዲለጠፍ ይሆናል።",
                     reply_markup=main_button(user))


@bot.callback_query_handler(lambda call: re.search(r'cancel_question', call.data))
def cancel_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    question_id = int(call.data.split(":")[-1])
    question = session.query(Question).filter_by(id=question_id).first()

    if question.status == 'previewing':
        question.status = 'cancelled'
        session.add(question)
        session.commit()
        bot.answer_callback_query(call.id, "ተሰርዟል...")
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("☑ እንደገና ለጥፍ", callback_data=f'post:{question_id}')]])
        bot.edit_message_reply_markup(inline_message_id=call.inline_message_id, reply_markup=btn)
    else:
        bot.edit_message_reply_markup(user_id, message_id)
        bot.answer_callback_query(call.id, "ይቅርታ፤ ይህ ጥያቄ መሰረዝ አይችልም።", show_alert=True)


@bot.callback_query_handler(lambda call: call.data.startswith('post'))
def post_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    question_id = int(call.data.split(":")[-1])
    question = session.query(Question).filter_by(id=question_id).first()
    msg_id = call.message.message_id
    btns = InlineKeyboardMarkup(row_width=2)
    btns.add(
        InlineKeyboardButton("ምላሽ", url=DEEPLINK + question.hash_link),
        InlineKeyboardButton("ዝርዝር (%d)" % len(question.answers), url=DEEPLINK + question.browse_link),
        InlineKeyboardButton("⚠️ ይጠቁሙ", callback_data='-report:%d' % question.id)
    )

    message = bot.copy_message(CHANNEL_ID, user_id, msg_id, reply_markup=btns)
    bot.answer_callback_query(call.id, "ጥያቄዎት ተለጥፏል።")
    question.status = 'posted'
    question.message_id = message.message_id
    session.add(question)
    session.commit()
    channel = bot.get_chat(CHANNEL_ID)
    bot.edit_message_text("<a href='https://t.me/%s/%d'>ጥያቄዎት ተለጥፏል!!</a>" % (channel.username, message.message_id),
                          user_id, msg_id, disable_web_page_preview=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('-report'))
def report_question(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "ጥቆማው ለአስተዳዳሪዎች ተልኳል!!")
    question_id = int(call.data.split(":")[-1])
    msg = bot.send_message(OWNER_ID, "አንድ ጥያቄ ተጠቁሟል።")
    btn = InlineKeyboardMarkup([[InlineKeyboardButton("🗑 አጥፋ", callback_data=f'del-question:{question_id}')]])
    bot.copy_message(OWNER_ID, call.message.chat.id, call.message.message_id, reply_to_message_id=msg.message_id,
                     reply_markup=btn)


@bot.callback_query_handler(lambda call: call.data.startswith('del-question'))
def del_question(call: types.CallbackQuery):
    question_id = int(call.data.split(":")[-1])
    question = session.query(Question).filter_by(id=question_id).first()
    closed = session.query(Question).filter_by(status='closed').count()
    bot.delete_message(CHANNEL_ID, question.message_id)
    if closed >= 3:
        bot.send_photo(question.asker_id, open("images/ታግደዋል.png", 'b'),
                       caption="<b>በተደጋጋሚ በለጠፉትና፤ ህግጋቶቻችንን በጣሱ ጥያቄዎቾ ምክኒያት እስከመጨረሻው ከዚህ ቦት ታግደዋል።</b>")
        question.asker.role = session.query(Role).filter_by(name='banned').first()
    else:
        bot.send_message(question.asker_id, "<b>‼️ ማስጠንቀቂያ</b>\n\n<a href='%s'>የርሶ ጥያቄ፤</a> በደረሰን ጥቆማ መሰረት ህግጋቶቻችንን "
                                        "ሰለጣሰ ከማሰራጫችን ላይ ጠፍቷል። እባኮን እንደዚህ አይነት ጥያቄ በድጋሚ አይለጥፉ።\n\nበተደጋጋሚ ይህን አድርገዉ "
                                        "ከተገኙ፤ ከቦቱ እስከ መጨረሺያዉ <b>ይታገዳሉ።</b>" % (DEEPLINK+question.hash_link))

    question.status = 'closed'
    session.add(question)
    session.commit()
    bot.edit_message_reply_markup(OWNER_ID, call.message.message_id)


@bot.callback_query_handler(lambda call: call.data.startswith('edit_user'))
def edit_user(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    content = call.data.split(":")[-1]
    user = session.query(User).filter_by(id=user_id).first()

    if content == 'name':
        bot.edit_message_reply_markup(user_id, message_id)
        bot.send_message(user_id, "ስሞትን ያስገቡ\n\n<code>ስሞት ሊያካትት የሚችልው፦ ሀ-ፐ ወይም A-Z ያሉትን ፊደላት በቻ ነው።</code>",
                         reply_markup=cancel(user.language))
        bot.set_state(user_id, 'edit_name')

    elif content == 'bio':
        bot.edit_message_reply_markup(user_id, message_id)
        bot.send_message(user_id, "ሰለራሶ ጥቂትን ነገር ይጻፉ።", reply_markup=cancel(user.language))
        bot.set_state(user_id, 'edit_bio')

    elif content == 'gender':
        bot.edit_message_text("ጾታ ይምረጡ", user_id, message_id, reply_markup=user_gender_button(user))

    bot.answer_callback_query(call.id)


@bot.message_handler(state='edit_name')
def edit_name(message: types.Message):
    user_id = message.chat.id
    text = message.text
    regex = re.fullmatch(r"[a-zA-Zሀ-ፐ]+", text)
    user = session.query(User).filter_by(id=user_id).first()
    if regex:
        name = regex.group()
        user.name = name
        session.add(user)
        session.commit()
        if user.language == 'english':
            message.text = "👤 Profile"
            en_button(message)
        else:
            message.text = '👤 መግለጫ'
            am_button(message)
        send_menu(user_id)
        bot.delete_state(user_id)

    else:
        bot.send_message(user_id, "ስሞትን ያስገቡ\n\n<code>ስሞት ሊያካትት የሚችልው፦ ሀ-ፐ፣ A-Z ያሉ ፊደላትን በቻ ነው።</code>",
                         reply_markup=cancel(user.language))


@bot.message_handler(state='edit_bio')
def edit_bio(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = session.query(User).filter_by(id=user_id).first()

    if len(text) < 100:
        bio = util.escape(text)
        user.bio = bio
        session.add(user)
        session.commit()
        if user.language == 'english':
            message.text = "👤 Profile"
            en_button(message)
        else:
            message.text = '👤 መግለጫ'
            am_button(message)

        send_menu(user_id)
        bot.delete_state(user_id)

    else:
        bot.send_message(user_id, "ሰለራሶ ጥቂትን ነገር ይጻፉ።", reply_markup=cancel(user.language))


@bot.callback_query_handler(lambda call: call.data.startswith("gender"))
def edit_gender(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id
    user = session.query(User).filter_by(id=user_id).first()
    try:
        content = call.data.split(":")[-1]
        if content == 'back':
            bot.edit_message_text(Text(user).profile, reply_markup=user_button(user))

        else:
            if content == 'undefined':
                user.gender = ''
            else:
                user.gender = content
            session.add(user)
            session.commit()
            bot.edit_message_reply_markup(user_id, message_id, reply_markup=user_gender_button(user))

    except ApiTelegramException:
        pass


@bot.callback_query_handler(lambda call: call.data.startswith('report'))
def report_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, '')
    user_id = call.from_user.id
    ans_id = call.data.split(":")[-1]
    ans = session.query(Answer).filter_by(id=ans_id).first()

    user = session.query(User).filter_by(id=user_id).first()
    bot.send_message(OWNER_ID, f"<a href='{DEEPLINK + ans.hash_link}'>አንድ ጥያቄ ተጠቁሟል</a>\nበ: {mention(user)}")


@bot.callback_query_handler(lambda call: re.search(r"my_(all|more)_question", call.data))
def show_more_user_question(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "ጥያቄዎችህን በመጫን ላይ....")
    user_id = call.message.chat.id
    message_id = call.message.message_id
    index = int(call.data.split(":")[-1])

    bot.edit_message_text("🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨", user_id, message_id)

    if call.data.startswith("my_all"):
        show_user_questions(user_id, index, True)

    else:
        show_user_questions(user_id, index)


@bot.callback_query_handler(lambda call: re.search(r"all_answer|more_answer", call.data))
def show_more_answers(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "መልሶችን በመጫን ላይ....")
    user_id = call.message.chat.id
    message_id = call.message.message_id
    index = int(call.data.split(":")[-1])
    question_id = int(call.data.split(":")[1])
    bot.edit_message_text("🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨", user_id, message_id)

    if call.data.startswith("all_answer"):
        show_answers(user_id, question_id, index, True)

    else:
        show_answers(user_id, question_id, index)


def show_user_questions(user_id, index=0, show_all=False):
    showed = False
    user = session.query(User).filter_by(id=user_id).first()
    count = 0
    for question in session.query(Question).filter_by(asker_id=user.id).all()[index:]:
        try:
            if not show_all and count == 10:
                break
            status = question.status

            if status == 'previewing':
                btn = on_question_button(user, question.id, question.setting.reply)

            elif status == 'cancelled':
                btn = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("☑ አንደገና ለጥፍ", callback_data=f'post:{question.id}')]])

            elif status == 'posted':
                btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"ዝርዝር ({len(question.answers)})",
                                                                  callback_data=f'browse_answer:{question.id}'),
                                             InlineKeyboardButton("መልስ", callback_data=f"answer:{question.id}")]])

            else:
                btn = None

            text = f"#{question.subject}\n\n<b>{question.body}</b>\n\nበ {mention(user)} የተጠየቀ"
            bot.send_message(user_id, text, reply_markup=btn)

            count += 1
            showed = True

        except:
            continue
    index += count

    if not showed:
        ask_q = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Ask" if user.language == 'en' else 'ጠይቅ', callback_data='ask_question')
        ask_q.add(btn)

        if user.language == 'english':
            bot.send_message(user_id, "Sorry you don't have any asked question yet.", reply_markup=ask_q)

        else:
            bot.send_message(user_id, "ይቅርታ እስካሁን ምንም የጠየቁት ጥያቄ የለም ።", reply_markup=ask_q)

    else:
        text = f'Showed - {index}, Total - {len(user.questions)}' if user.language == 'en' else f"የታየ - {index} ፣ አጠቃላይ - {len(user.questions)}"
        if len(user.questions) > index:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Show more" if user.language == 'en' else "ተጨማሪ አሳይ",
                                                              callback_data=f'my_more_question:{index}'),
                                         InlineKeyboardButton("Show all" if user.language == 'en' else "ሁሉንም አሳይ",
                                                              callback_data=f'my_all_question:{index}')]], row_width=1)
        else:
            btn = None
        bot.send_message(user_id, text, reply_markup=btn)


answers_json = {}


def show_answers(user_id, question_id, index=0, show_all=False):
    global answers_json
    count = 0
    showed = False
    question = session.query(Question).filter_by(id=question_id, status='posted').first()
    me = session.query(User).filter_by(id=user_id).first()
    for answer in question.answers[index:]:
        try:
            if answer.status != 'posted':
                bot.send_message(user_id, "******** እየተገመገመ ያለ መልስ ******")
            if not show_all and count == 10:
                break

            asker = "#ጠያቂ" if answer.from_user_id == question.asker_id else ""
            btn = InlineKeyboardMarkup()
            ls = []

            if question.setting.reply or user_id == question.asker_id:
                ls.append(InlineKeyboardButton("↪ መልስ", callback_data=f'reply_answer:{answer.id}'))

            ls.append(InlineKeyboardButton("⚠ ጠቁም", callback_data=f'report_answer:{answer.id}'))
            btn.add(*ls)

            text = f"{asker}\n\n<b>{answer.body}</b>\n\nበ: {mention(answer.from_user)} የተመለሰ" \
                   f"\n{filters.parse_time(answer.timestamp)}"
            msg = bot.send_message(user_id, text.strip(), reply_markup=btn,
                                   reply_to_message_id=answers_json.get(user_id, {}).get(answer.reply))

            count += 1
            showed = True
            js = answers_json.get(user_id, {})
            js[answer.id] = msg.message_id
            answers_json[user_id] = js

        except:
            continue

    index += count

    if showed:
        text = f'Showed - {index}, Total - {question.browse}' if me.language == 'english' \
            else f"የታየ - {index} ፣ አጠቃላይ - {len(question.answers)}"
        if len(question.answers) > index:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Show more" if me.language == 'english' else "ተጨማሪ አሳይ",
                                                              callback_data=f'more_answer:{question_id}:{index}'),
                                         InlineKeyboardButton("Show all" if me.language == 'english' else "ሁሉንም አሳይ",
                                                              callback_data=f'all_answer:{question_id}:{index}')]],
                                       row_width=1)
        else:
            btn = None

        bot.send_message(user_id, text, reply_markup=btn)

    else:
        bot.send_message(user_id, "የመጀመሪያዉ መላሽ ይሁኑ።")


@bot.message_handler(state='get_answer', content_types=util.content_type_media)
def get_answer(message: types.Message):
    user_id = message.chat.id
    user = session.query(User).filter_by(id=user_id).first()

    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']
        reply_to = data.get('reply_to', 0)
        msg_id = data.get('message_id', 0)

    if not message.text:
        bot.send_message(user_id, Text(user).answer, reply_markup=cancel(user.language))

    answer = Answer(from_user=user, body=message.text, question_id=question_id, reply=reply_to)
    session.add(answer)
    session.commit()
    send_answer(user_id, answer.id, msg_id)
    bot.delete_state(user_id)
    send_menu(user_id)


@bot.callback_query_handler(lambda call: re.search(r'edit:answer', call.data))
def edit_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id
    answer_id, msg_id = call.data.split(':')[2:]
    answer = session.query(Answer).filter_by(id=answer_id).first()
    bot.edit_message_reply_markup(user_id, message_id)
    user = session.query(User).filter_by(id=user_id).first()

    if answer.status != 'preview':
        return bot.send_message(user_id, "This answer cannot be edited!")

    else:
        bot.send_message(user_id, Text(user).answer, reply_markup=cancel(user.language))
        bot.set_state(user_id, 'edit_answer')

        with bot.retrieve_data(user_id) as data:
            data['answer_id'] = answer_id
            data['message_id'] = msg_id


@bot.message_handler(state='edit_answer', content_types=util.content_type_media)
def __edit_answer(message: types.Message):
    user_id = message.chat.id
    user = session.query(User).filter_by(id=user_id).first()

    with bot.retrieve_data(user_id) as data:
        answer_id = data['answer_id']
        message_id = data.get('message_id', 0)

    answer = session.query(Answer).filter_by(id=answer_id).first()
    if not message.text:
        bot.send_message(user_id, Text(user).answer, reply_markup=cancel(user.language))

    answer.body = message.text
    session.add(answer)
    session.commit()
    send_answer(user_id, answer_id, message_id)
    bot.delete_state(user_id)
    send_menu(user_id)


def send_answer(user_id, answer_id, message_id=0):
    answer = session.query(Answer).filter_by(id=answer_id).first()
    reply_to = answer.reply
    user = session.query(User).filter_by(id=user_id).first()
    if reply_to:
        the_answer = session.query(Answer).filter_by(id=reply_to).first()
        reply_text = f"↪ <b>In reply to</b>\n<i>\"{the_answer.body}\"</i>\n\n"
    else:
        reply_text = ''
    bot.send_message(user_id, f"<b>{reply_text + answer.body}</b>\n\nበ {mention(user)} የተመለሰ",
                     reply_markup=on_answer_button(answer_id, message_id))


@bot.callback_query_handler(lambda call: call.data.startswith('submit'))
def submit_answer(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    answer_id, msg_id = call.data.split(':')[1:]
    answer = session.query(Answer).filter_by(id=answer_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    question = session.query(Question).filter_by(id=answer.question_id).first()

    if answer.status != 'preview':
        bot.edit_message_reply_markup(user_id, message_id)
        return bot.send_message(user_id, "ይህ መልስ ሊላክ አይችልም!")

    else:
        bot.answer_callback_query(call.id, "ምላሾ ተልኳል!")
        bot.delete_message(user_id, message_id)
        to_user = question.asker.id if not answer.reply else session.query(Answer.from_user_id).filter_by(id=answer.reply).first()[0]
        reply_msg_id = None if not answer.reply else session.query(Answer.message_id).filter_by(id=answer.reply).first()[0]
        asker = "#ጠያቂ" if answer.from_user_id == question.asker.id else ""
        btn = InlineKeyboardMarkup()
        ls = []

        if question.setting.reply or user_id == question.asker:
            ls.append(InlineKeyboardButton("↪ Reply", callback_data=f'reply_answer:{answer.id}'))
        ls.append(InlineKeyboardButton("⚠ ይጠቁሙ", callback_data=f'report_answer:{answer.id}'))
        btn.add(*ls)
        answer.status = 'posted'

        text = f"{asker}\n\n<b>{answer.body}</b>\n\nበ: {mention(answer.from_user)} የተመለሰ" \
               f"\n{filters.parse_time(answer.timestamp)}"
        msg = bot.send_message(user_id, text.strip(), reply_markup=btn, reply_to_message_id=msg_id)
        answer.message_id = msg.message_id
        if user_id == to_user:
            return
        try:
            if to_user == question.asker and not answer.reply_to:
                url = f't.me/{bot.get_chat(CHANNEL_ID).username}/{question.message_id}'
                bot.send_message(to_user, f"{mention(user)} <a href='{url}'>ለጥያቄዎ</a> ምልስ ሰጥቷል።",
                                 disable_web_page_preview=True)
            bot.send_message(to_user, text.strip(), reply_markup=btn, reply_to_message_id=reply_msg_id)

        except:
            raise

        session.add(answer)
        session.commit()
        btns = InlineKeyboardMarkup(row_width=2)
        btns.add(
            InlineKeyboardButton("ምላሽ", url=DEEPLINK + question.hash_link),
            InlineKeyboardButton("ዝርዝር (%d)" % len(question.answers), url=DEEPLINK + question.browse_link),
            InlineKeyboardButton("⚠️ ይጠቁሙ ", callback_data=DEEPLINK + "-report:" + question.id)
        )
        bot.edit_message_reply_markup(CHANNEL_ID, question.message_id, reply_markup=btns)


@bot.callback_query_handler(lambda call: call.data.startswith('browse_answer'))
def browse_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "በመጫን ላይ....")
    user_id = call.message.chat.id
    question_id = call.data.split(":")[-1]
    show_answers(user_id, question_id)


@bot.callback_query_handler(lambda call: call.data.startswith('answer'))
def answer_to_question(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    question_id = int(call.data.split(':')[-1])
    user = session.query(User).filter_by(id=user_id).first()
    bot.send_message(user_id, Text(user).answer, reply_markup=cancel(user.language))
    bot.set_state(user_id, 'get_answer')

    with bot.retrieve_data(user_id) as data:
        data['question_id'] = question_id


@bot.callback_query_handler(lambda call: call.data.startswith('reply_answer'))
def reply_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    user = session.query(User).filter_by(id=user_id).first()
    answer_id = call.data.split(":")[-1]
    answer = session.query(Answer).filter_by(id=answer_id).first()

    bot.send_message(user_id, Text(user).answer, reply_markup=cancel(user.language))
    bot.set_state(user_id, 'get_answer')

    with bot.retrieve_data(user_id) as data:
        data['question_id'] = answer.question.id
        data['reply_to'] = answer.id
        data['message_id'] = call.message.message_id


@bot.callback_query_handler(lambda call: call.data.startswith("user"))
def get_user(call: types.CallbackQuery):
    user_id = call.message.chat.id
    current_user = session.query(User).filter_by(id=user_id).first()
    content, usr_id = call.data.split(':')[1:]
    msg_id = call.message.message_id
    user = session.query(User).filter_by(id=usr_id).first()

    if content == "chat":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "<code>መልዕክቶን ይጻፉ....</code>", reply_markup=cancel(user.language))
        bot.set_state(user_id, 'chat')
        with bot.retrieve_data(user_id) as data:
            data['to_user'] = usr_id
        return

    if current_user.role.name == 'moderator' and user.role.name == 'moderator':
        bot.answer_callback_query(call.id, 'This user is admin!')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(user, current_user))

    elif user.status == 'admin':
        bot.answer_callback_query(call.id, 'He is owner')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(user, current_user))

    else:
        if content == 'ban':
            if current_user.can(Permission.BAN):
                bot.answer_callback_query(call.id, 'Banned!')
                user.role = session.query(Role).filter_by(name='banned').first()
                session.add(user)
                bot.ban_chat_member(CHANNEL_ID, usr_id)

            else:
                bot.answer_callback_query(call.id, 'This user is already banned!')

        elif content == 'unban':
            if current_user.can(Permission.BAN):
                if content == 'unban' and user.role.name == 'banned':
                    bot.answer_callback_query(call.id, 'Unbanned!')
                    user.role.return_permission()
                    session.add(user)
                    bot.unban_chat_member(CHANNEL_ID, usr_id)
                else:
                    bot.answer_callback_query(call.id, f'This user is already')

        elif content == 'send':
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, '<code>መልዕክቶን ይጻፉ....</code>', reply_markup=cancel(user.language))
            bot.set_state(user_id, 'admin_message')
            with bot.retrieve_data(user_id) as data:
                data['to_user'] = usr_id
            return

        else:
            bot.answer_callback_query(call.id, 'መረጃዎችን በመሰብሰብ ላይ.....')
            _mention = f"<a href='tg://user?id={int(user.id)}'>{int(user.id)}</a>"
            bot.send_message(user_id, f'<b>ስም:</b> {user.name}\n<b>ID:</b> {user.id}\n\n{_mention}')
        session.commit()
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(user, current_user))


@bot.message_handler(state='chat', content_types=util.content_type_media)
def chat(message: types):
    user_id = message.from_user.id
    _from = session.query(User).filter_by(id=user_id).first()
    with bot.retrieve_data(user_id) as data:
        to_user = data['to_user']
    _to = session.query(User).filter_by(id=to_user).first()
    if not message.text:
        bot.send_message(user_id, 'Text is required!')
    else:
        try:
            bot.send_message(to_user, f'<b>{util.escape(message.text)}</b>\n\n{mention(_from)}',
                             reply_markup=on_user_profile(_from, _to))
        except ApiTelegramException:
            pass
        bot.reply_to(message, f'መልዕክቱ ለ {mention(_to)} ተልኳል።')
        send_menu(user_id)
        bot.delete_state(user_id)


@bot.message_handler(state='admin_message', content_types=['text'])
def admin_message(message: types.Message):
    user_id = message.from_user.id
    with bot.retrieve_data(user_id) as data:
        to_user = data['to_user']

    _to = session.query(User.name).filter_by(id=to_user)
    try:
        bot.send_message(to_user, "#አስተዳዳሪ\n\n%s" % message.text)
    except ApiTelegramException:
        pass
    bot.reply_to(message, f'መልዕክቱ ለ {mention(_to)} ተልኳል።')
    send_menu(user_id)
    bot.delete_state(user_id)


@bot.message_handler(state='feedback', content_types=util.content_type_media)
def get_user_feedback(message: types.Message):
    user_id = message.from_user.id
    user = session.query(User).filter_by(id=user_id).first()
    if not message.text:
        bot.send_message(user_id, 'Text is required!')
    else:
        bot.send_message(OWNER_ID, f"#አስታየት\n<b>{util.escape(message.text)}</b>\n\nከ {mention(user)}",
                         reply_markup=on_user_profile(user, session.query(User).filter_by(id=OWNER_ID).first()))
        if user.language == 'english':
            bot.send_message(user_id, 'Thank you for your feedback!')
        else:
            bot.send_message(user_id, 'እናመሰግናለን!')
        send_menu(user_id)
        bot.delete_state(user_id)


@bot.message_handler(commands=['get'], chat_id=[OWNER_ID])
def get(message: types.Message):
    text = message.text.split()
    user = session.query(User).filter_by(id=text[-1]).first()
    if user is not None:
        message.text = "/start {}".format(user.link)
        __start(message)
    else:
        bot.reply_to(message, 'This user not a member of this bot')


@bot.message_handler(commands=['off', 'on'], chat_id=[OWNER_ID])
def off(message):
    global PENDING
    if message.text == '/on':
        PENDING = True
    else:
        PENDING = False
    bot.reply_to(message, 'Done!')


@bot.message_handler(func=lambda message: message.text in ["📝 መልዕክት ላክ", "📊 ቆጠራ"], chat_types=['private'])
def admin_buttons(message: types.Message):
    user_id = message.chat.id
    user = session.query(User).filter_by(id=user_id).first()

    if user.role.name == 'user':
        return

    if message.text == "📝 መልዕክት ላክ":
        if user_id == OWNER_ID or user.can(Permission.SEND):
            bot.send_message(user_id, "✳️አዲስ መልዕክት ይጻፉ.\n\nአንዲሁም ከለሎች ማሰራጫ ወይም ማውጊያ ወደዚህ ሊልኩ ይችላሉ።",
                             reply_markup=cancel(user.language))
            bot.set_state(user_id, 'message')
            markups.clear()

    else:
        if user.can(Permission.SEE):
            users = session.query(User).order_by(User.since_member.desc())
            btn = pagination_button(1, users.count())
            text = ''
            count = 0
            for user in users.limit(10):
                count += 1
                text += "<code>#%d.</code> %s\n\n" % (count, mention(user))
            text += "\nየታየ - %d ፤ አጠቃላይ - %d" % (count,  users.count())
            bot.send_message(user_id, text, reply_markup=btn)


@bot.message_handler(func=lambda message: message.text in main_text_en, language='english', chat_types=['private'])
def en_button(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = session.query(User).filter_by(id=user_id).first()
    _text = Text(user)
    if text == "📝 Ask Question":
        bot.send_message(user_id, _text.question, reply_markup=cancel('english'))
        bot.set_state(user_id, UserState.get_question)

    elif text == "🔅 My Questions":
        show_user_questions(user_id)

    elif text == "👤 Profile":
        bot.send_message(user_id, _text.profile, reply_markup=user_button(user))

    elif text == "🌐 Language":
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())

    elif text == "💭 Feedback":
        bot.send_message(user_id, "Send us your feedback with text", reply_markup=cancel("english"))
        bot.set_state(user_id, 'feedback')

    elif text == "📃 Rules":
        rules = open("rules/enrules.txt")
        bot.send_message(user_id, rules.read())
        rules.close()

    elif text == '🎈 Contact':
        bot.send_message(user_id, "<b>✔ Contact the developer\n\n👨‍💻 @Natiprado</b>")


@bot.message_handler(func=lambda message: message.text in main_text_am, language='amharic', chat_types=['private'])
def am_button(message: types.Message):
    """
    ይህ ተግባር፤ ሁሉንም የአማርኛ አዝራሮች ለመሰብሰብና ምላሽ ለመስጠት ይረዳል።
    """

    user_id = message.chat.id
    text = message.text
    user = session.query(User).filter_by(id=user_id).first()
    _text = Text(user)

    if text == "📝 ጠይቅ":
        bot.send_message(user_id, _text.question, reply_markup=cancel('amharic'))
        bot.set_state(user_id, UserState.get_question)

    elif text == "🔅 የኔ ጥያቄዎች":
        show_user_questions(user_id)

    elif text == "👤 መግለጫ":
        bot.send_message(user_id, _text.profile, reply_markup=user_button(user))

    elif text == "🌐 ቋንቋ":
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())

    elif text == "💭 አስታየት":
        bot.send_message(user_id, "ያሎትን አስታየት በጽሑፍ ያድርሱን።", reply_markup=cancel("amharic"))
        bot.set_state(user_id, 'feedback')

    elif text == "📃 ህግጋት":
        rules = open("rules/amrules.txt", 'r', encoding='utf-8')
        bot.send_message(user_id, rules.read())
        rules.close()

    elif text == "🎈 አግኝ":
        bot.send_message(user_id, "<b>✔ የቦቱን መስራች ያግኙ\n\n👨‍💻 @Natiprado</b>")


@app.route("/")
def index():
    bot.set_webhook(WEBHOOK+'/'+TOKEN)
    return "Added webhook <b>%s</b>" % WEBHOOK


@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "One update processed"


bot.add_custom_filter(LanguageFilter())
bot.add_custom_filter(Deeplink())
bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(ChatFilter())


if __name__ == "__main__":
    print("Bot started polling")
    bot.infinity_polling()


