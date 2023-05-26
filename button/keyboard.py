from telebot import util
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from utils.model import Permission


def lang_button(first=False):
    lang = InlineKeyboardMarkup([[InlineKeyboardButton('🇬🇧 English', callback_data='lang:en' if not first else 'lang:enf'),
                                  InlineKeyboardButton("🇪🇹 Amharic", callback_data='lang:am' if not first else 'lang:amf')
                                ]])
    return lang


main_text_en = ['📝 Ask Question', '🔅 My Questions', '👤 Profile', '🌐 Language', '💭 Feedback', '📃 Rules',
                '🎈 Contact']

main_text_am = ['📝 ጠይቅ', '🔅 የኔ ጥያቄዎች', '👤 መግለጫ', '🌐 ቋንቋ', '💭 አስታየት', '📃 ህግጋት', '🎈 አግኝ']


def main_button(user):
    if user.language == 'english':
        k = main_text_en
    else:
        k = main_text_am
    btn = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    ad = []
    if user.can(Permission.SEND):
        ad.append(KeyboardButton("📝 ምልዕክት ላክ"))
    if user.can(Permission.SEE):
        ad.append("📊 ቆጠራ")
    btn.add(*ad, row_width=3)

    btn.add(*[KeyboardButton(i) for i in k])

    return btn


def cancel(lang):
    btn = ReplyKeyboardMarkup(resize_keyboard=True)
    btn.add(KeyboardButton("❌ Cancel" if lang == 'english' else "❌ ሰርዝ"))
    return btn


subject_text = ["🇬🇧 English", "🇪🇹 አማርኛ", "🇪🇹 Afaan Oromoo", "🧪 Chemistry", "🧮 Math", "🔭 Physics", "⚽ HPE", "🔬 Biology",
                "💻 ICT", "🌏 History", "🧭 Geography", "⚖ Civics", "💶 Economics", '💰 Business']


def subject_button():
    btn = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn.add(*subject_text)
    btn.add(KeyboardButton("❌ Cancel"))
    return btn


def pagination_button(current_row, max_users):
    btn = InlineKeyboardMarkup(row_width=5)
    btn_list = []
    if max_users > 10:
        row = max_users // 10
        left = max_users - row * 10
        row = row + 1 if left != 0 else row
        if current_row == 1:
            btn_list.append(InlineKeyboardButton("1", callback_data="pagin=1"))
        else:
            txt = "◀️ 1" if current_row <= 5 else '⏪ 1'
            btn_list.append(InlineKeyboardButton(txt, callback_data="pagin=1"))
        if current_row - 1 > 1:
            btn_list.append(InlineKeyboardButton(f"◀️ {current_row - 1}", callback_data=f"pagin={current_row - 1}"))
        if current_row != row and current_row > 1:
            btn_list.append(InlineKeyboardButton(f"{current_row}", callback_data=f"pagin={current_row}"))

        if current_row + 1 < row:
            btn_list.append(InlineKeyboardButton(f"▶️ {current_row + 1}", callback_data=f"pagin={current_row + 1}"))

        if current_row == row:
            btn_list.append(InlineKeyboardButton(f"{current_row}", callback_data=f"pagin={current_row}"))
        else:
            txt = f"▶️ {row}" if current_row + 5 >= row else f"⏩ {row}"
            btn_list.append(InlineKeyboardButton(txt, callback_data=f"pagin={row}"))

    btn.add(*btn_list)
    return btn


def on_question_button(user, question_id, reply=True):
    if not reply:
        if user.language == 'english':
            enb = "Enable Reply"
        else:
            enb = ""
    else:
        if user.language == 'english':
            enb = "Disable Reply"
        else:
            enb = ""
    edit = {
        "📝 Edit question" if user.language == 'english' else "📝 አርትዕ ጥያቄ": {'callback_data': f'edit:question:{question_id}'},
        '📖 Edit Subject' if user.language == 'english' else "📖 አርትዕ ትምህርት": {'callback_data': f'edit:subject:{question_id}'},
         enb: {'callback_data': f'edit:enable:{question_id}' if not reply else f'edit:disable:{question_id}'},
        "❌ Cancel" if user.language == 'english' else "❌ ሰርዝ": {'callback_data': f'cancel_question:{question_id}'},
        '✅ post' if user.language == 'english' else "✅ ለጥፍ": {'callback_data': f'post:{question_id}'}
    }
    return util.quick_markup(edit)


def user_button(user):
    edit = {
        "Edit Name" if user.language == 'english' else "አርትዕ ስም": {'callback_data': 'edit_user:name'},
        "Edit bio" if user.language == 'english' else "አርትዕ ስለራስ": {'callback_data': 'edit_user:bio'},
        "Edit gender" if user.language == 'english' else "አርትዕ ጾታ": {'callback_data': 'edit_user:gender'}
    }
    return util.quick_markup(edit)


def user_gender_button(user):
    if user.language == 'english':
        male = "Male" if user.gender != "👨" else "✅ Male"
        female = "Female" if user.gender != "👩" else "✅ Female"
        undefined = "Undefined" if user.gender is not None else "✅ Undefined"
    else:
        male = "ወንድ" if user.gender != "👨" else "✅ ወንድ"
        female = "ሴት" if user.gender != "👩" else "✅ ሴት"
        undefined = "ያልተገለጸ" if user.gender is not None else "✅ ያልተገለጸ"
    gender = {
        male: {'callback_data': 'gender:👨'},
        female: {'callback_data': 'gender:👩'},
        undefined: {'callback_data': 'gender:undefined'}
    }
    return util.quick_markup(gender)


def on_user_profile(the_user, user):
    btn = InlineKeyboardMarkup()

    if the_user.id != user.id:
        btn.add(InlineKeyboardButton("📝 መልዕክት ላክ", callback_data=f'user:chat:{the_user.user_id}'))

    if the_user.role.name == "admin":
        return btn

    ban = InlineKeyboardButton("✅ አታግድ" if the_user.status == 'banned' else "🚷 አግድ",
                               callback_data=f'user:{"unban" if the_user.role.name == "banned" else "ban"}:{the_user.id}')
    show = InlineKeyboardButton("👤 መግለጫ አሳይ", callback_data=f'user:show:{the_user.id}')
    if user.can(Permission.BAN):
        btn.add(ban)
    if user.can(Permission.MANAGE):
        btn.add(show, InlineKeyboardButton("🛂 እንደ አስተዳዳሪ ምልዕክት ላክ", callback_data=f'user:send:{the_user.id}'))
    return btn


def on_answer_button(answer_id, message_id=0):
    btn = InlineKeyboardMarkup()
    btn.add(*[InlineKeyboardButton("📝 አርትዕ መልስ", callback_data=f'edit:answer:{answer_id}:{message_id}'),
              InlineKeyboardButton('✅ ላክ', callback_data=f'submit:{answer_id}:{message_id}'),
              ])
    return btn
