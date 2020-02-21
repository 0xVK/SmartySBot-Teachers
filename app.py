#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import telebot
import datetime
import os
import settings
import core
import sys
import re
import json
import copy
import random
from WeatherManager import WeatherManager
from settings import KEYBOARD
from flask import Flask, request, render_template, jsonify

app = Flask(__name__, template_folder='site', static_folder='site/static', static_url_path='/fl1/static')
bot = telebot.TeleBot(settings.BOT_TOKEN, threaded=True)

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.row(KEYBOARD['TODAY'], KEYBOARD['TOMORROW'], KEYBOARD['FOR_A_WEEK'])
keyboard.row(KEYBOARD['FOR_A_TEACHER'], KEYBOARD['FOR_A_GROUP'])
keyboard.row(KEYBOARD['IN_AUDIENCE'], KEYBOARD['FOR_A_AUDIENCE'], KEYBOARD['HELP'])

emoji_numbers = ['0⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣']


def get_timetable(faculty='', teacher='', group='', sdate='', edate='', user_id=None):

    http_headers = {
            'User-Agent': settings.HTTP_USER_AGENT,
            'Accept': 'text/html',
    }

    try:
        post_data = {
            'faculty': faculty,
            'teacher': teacher.encode('windows-1251'),
            'group': group.encode('windows-1251'),
            'sdate': sdate,
            'edate': edate,
            'n': 700,
        }
    except Exception as ex:
        core.log(m='Помилка кодування параметрів запиту до сайту деканату: {}'.format(str(ex)))
        bot.send_message(user_id, 'Помилка надсилання запиту, вкажіть коректні параметри.', reply_markup=keyboard)
        return False

    if settings.USE_CACHE:
        request_key = 'G:{}|T:{}|SD:{}|ED:{}'.format(group.lower(), teacher, sdate, edate)
        cached_timetable = core.Cache.get_from_cache(request_key)

        if cached_timetable:
            return json.loads(cached_timetable[0][1])

    try:
        page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=15)
    except Exception as ex:
        core.log(m='Помилка з\'єднання із сайтом деканату: {}'.format(str(ex)))
        if user_id:
            bot.send_message(user_id, 'Помилка з\'єднання із сайтом Деканату. Спробуйте пізніше.', reply_markup=keyboard)
        return False

    parsed_page = BeautifulSoup(page.content, 'html5lib')
    all_days_list = parsed_page.find_all('div', class_='col-md-6')[1:]
    all_days_lessons = []

    for one_day_table in all_days_list:
        all_days_lessons.append({
            'day': one_day_table.find('h4').find('small').text,
            'date': one_day_table.find('h4').text[:5],
            'lessons': [' '.join(lesson.text.split()) for lesson in one_day_table.find_all('td')[2::3]]
        })

    if all_days_lessons and settings.USE_CACHE:  # if timetable exists, put it to cache
        cached_all_days_lessons = copy.deepcopy(all_days_lessons)
        cached_all_days_lessons[0]['day'] += '*'
        _json = json.dumps(cached_all_days_lessons, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2)
        core.Cache.put_in_cache(request_key, _json)

    return all_days_lessons


def render_day_timetable(day_data):

    day_timetable = '.....::::: <b>\U0001F4CB {}</b> - <i>{}</i> :::::.....\n\n'.format(day_data['day'], day_data['date'])

    lessons = day_data['lessons']

    start_index = 0
    end_index = len(lessons) - 1

    for i in range(8):
        if lessons[i]:
            start_index = i
            break

    for i in range(end_index, -1, -1):
        if lessons[i]:
            end_index = i
            break

    timetable = ['9:00 - 10:20', '10:30 - 11:50', '12:10 - 13:30', '13:40 - 15:00',
                 '15:20 - 16:40 ', '16:50 - 18:10', '18:20 - 19:40', '-']
    for i in range(start_index, end_index + 1):
        if lessons[i]:
            day_timetable += '{} <i>{}</i> \n{}\n\n'.format(emoji_numbers[i+1], timetable[i], lessons[i])
        else:
            day_timetable += '{} <i>{}</i>\nВікно \U0001F483\U0001F57A\n\n'.format(emoji_numbers[i+1], timetable[i])

    return day_timetable


@bot.message_handler(commands=['ci'])
def cache_info(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    cache_items_count = len(core.Cache.get_keys() or '')

    bot.send_message(user.get_id(), 'In cache: {} units'.format(cache_items_count))


@bot.message_handler(commands=['cc'])
def clear_cache(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    core.Cache.clear_cache()

    bot.send_message(user.get_id(), 'Кеш пар був очищений.')


@bot.message_handler(commands=['ca'])
def clear_cache_audiences(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    core.clear_cache_audiences()

    bot.send_message(user.get_id(), 'Кеш розкладу по аудиторіям був очищений.')


@bot.message_handler(commands=['log'])
def get_logs(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        bot.send_message(user.get_id(), 'Немає доступу :(')
        return

    if len(message.text.split()) == 2:
        count = int(message.text.split()[1])
    else:
        count = 65

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'r', encoding="utf-8") as log_file:
        log_lines = log_file.readlines()

    logs = ''

    for line in log_lines[-count:]:
        logs += line

    bot.send_message(user.get_id(), logs, reply_markup=keyboard)


@bot.message_handler(commands=['start'])
def start_handler(message):
    sent = bot.send_message(message.chat.id, 'Вітаю, {} 😊. Я постараюсь допомогти Вам із розкладом. З моєю допомогою '
                                             'Ви зможете швидко та зручно переглядати свій розклад. Тож для початку '
                                             'роботи вкажіть своє прізвище '
                                             '(і тільки прізвище)'.format(message.chat.first_name))
    bot.register_next_step_handler(sent, set_name)


@bot.callback_query_handler(func=lambda call_back: call_back.data in ('Поточний', 'Наступний'))
def week_schedule_handler(call_back):

    user = core.User(call_back.message.chat)
    user_name = user.get_full_name()
    req = call_back.data

    today = datetime.date.today()
    current_week_day_number = today.isoweekday()
    diff_between_saturday_and_today = 6 - current_week_day_number
    last_week_day = today + datetime.timedelta(days=diff_between_saturday_and_today)

    next_week_first_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 2)
    next_week_last_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 7)

    if req == 'Поточний':
        timetable_data = get_timetable(teacher=user_name, sdate=today.strftime('%d.%m.%Y'),
                                       edate=last_week_day.strftime('%d.%m.%Y'), user_id=user.get_id())
    if req == 'Наступний':
        timetable_data = get_timetable(teacher=user_name, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                       edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

    timetable_for_week = ''

    if timetable_data:
        for timetable_day in timetable_data:
            timetable_for_week += render_day_timetable(timetable_day)

        bot.delete_message(chat_id=user.get_id(), message_id=call_back.message.message_id)

    elif isinstance(timetable_data, list) and not len(timetable_data):
        bot.delete_message(chat_id=user.get_id(), message_id=call_back.message.message_id)
        timetable_for_week = "На тиждень пар не знайдено."

    else:
        return

    bot.send_message(text=timetable_for_week[:4090], chat_id=user.get_id(),
                     parse_mode="HTML", reply_markup=keyboard)


def select_teacher_from_list_reg(message):

    user = core.User(message.chat)

    msg = 'Добре 👍, буду показувати розклад для {}.'.format(message.text)
    user.update_name(message.text) if user.get_full_name() else user.registration(message.text)
    bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')
    return


def set_name(message):

    user = core.User(message.chat)
    name = message.text

    if name == 'Відміна':
        current_user_group = user.get_full_name()
        bot.send_message(message.chat.id, 'Добре, залишимо налаштування для {}.'.format(current_user_group),
                         reply_markup=keyboard)
        return

    teachers_list = []

    try:
        with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'r', encoding="utf-8") as file:
            all_teachers = json.loads(file.read())
    except Exception as ex:
        bot.send_message('204560928', 'Помилка в роботі бота. Можливо відсутній файл із викладачами.')
        bot.send_message(message.chat.id, 'Під час роботи виникла помилка. Розробник отримав сповіщення.',
                         reply_markup=keyboard)
        core.log(m='Помилка завантаження файлу із викладачами: {}'.format(str(ex)))
        return

    for teacher in all_teachers:
        if teacher.split()[0].upper() == message.text.upper():
            teachers_list.append(teacher)

    if not teachers_list:

        sent = bot.send_message(message.chat.id, 'Не можу знайти викладача з таким прізвищем. Спробуйте ще раз.')
        bot.register_next_step_handler(sent, set_name)
        return

    if len(teachers_list) == 1:
        msg = 'Добро 👍, буду показувати розклад для {}.'.format(teachers_list[0])
        user.update_name(teachers_list[0]) if user.get_full_name() else user.registration(teachers_list[0])
        bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')
        return

    if len(teachers_list) > 1:
        teachers_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for teacher in teachers_list:
            teachers_keyboard.row(teacher)

        sent = bot.send_message(message.chat.id, 'Виберіть із списку:', reply_markup=teachers_keyboard)
        bot.register_next_step_handler(sent, select_teacher_from_list_reg)


def show_teachers(chat_id, name):

    in_week = datetime.date.today() + datetime.timedelta(days=7)

    in_week_day = in_week.strftime('%d.%m.%Y')
    today = datetime.date.today().strftime('%d.%m.%Y')

    rozklad_data = get_timetable(teacher=name, sdate=today, edate=in_week_day, user_id=chat_id)

    if rozklad_data:
        rozklad_for_week = 'Розклад на тиждень у <b>{}</b>:\n\n'.format(name)
        for rozklad_day in rozklad_data:
            rozklad_for_week += render_day_timetable(rozklad_day)
    else:
        rozklad_for_week = 'На тиждень пар у викладача <b>{}</b> не знайдено.'.format(name)

    bot.send_message(chat_id, rozklad_for_week, reply_markup=keyboard, parse_mode='HTML')


def select_teacher_from_request(message):  # ф-я викликається коли є 2 і більше викладачі з таким прізвищем

    if message.text == 'Назад':
        bot.send_message(message.chat.id, 'Окей)', reply_markup=keyboard)
        return

    show_teachers(message.chat.id, message.text)


def select_teachers(message):

    core.log(message.chat, '> (по викладачу) {}'.format(message.text))
    tchrs = []

    try:
        with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'r', encoding="utf-8") as file:
            all_teachers = json.loads(file.read())
    except Exception as ex:
        bot.send_message(message.chat.id, 'Даний функціонал тимчасово не працює.', reply_markup=keyboard)
        core.log(m='Error loading teachers file: {}'.format(str(ex)))
        return

    for teacher in all_teachers:
        if teacher.split()[0].upper() == message.text.upper():
            tchrs.append(teacher)

    if not tchrs:
        bot.send_message(message.chat.id, 'Не можу знайти викладача з таким прізвищем. Щоб спробувати ще раз знову'
                                          ' виберіть потрібний пункт меню на введіть прізвище.', reply_markup=keyboard)
        return

    if len(tchrs) == 1:
        show_teachers(message.chat.id, tchrs[0])
        return

    if len(tchrs) > 1:

        teachers_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for teacher in tchrs:
            teachers_keyboard.row(teacher)

        teachers_keyboard.row('Назад')
        sent = bot.send_message(message.chat.id, 'Вибери викладача:', reply_markup=teachers_keyboard)
        bot.register_next_step_handler(sent, select_teacher_from_request)
        return


def show_other_group(message):

    group = message.text
    core.log(message.chat, '> (по групі) {}'.format(group))
    bot.send_chat_action(message.chat.id, "typing")

    if group == KEYBOARD['MAIN_MENU']:
        bot.send_message(message.chat.id, 'Окей', reply_markup=keyboard, parse_mode='HTML')
        return

    if not core.is_group_valid(group):

        possible_groups = core.get_possible_groups(group)
        msg = 'Групи <b>{}</b> немає в базі розкладу.\n'.format(group)

        if possible_groups:

            msg += '<b>Можливі варіанти:</b>\n'
            groups_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

            groups_kb.row(KEYBOARD['MAIN_MENU'])

            for group in possible_groups:
                msg += '{}\n'.format(group.get('group'))
                groups_kb.row(group.get('group'))

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=groups_kb)
            bot.register_next_step_handler(sent, show_other_group)
            return

        bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')
        return

    in_week = datetime.date.today() + datetime.timedelta(days=7)
    in_week_day = in_week.strftime('%d.%m.%Y')
    today = datetime.date.today().strftime('%d.%m.%Y')

    timetable_data = get_timetable(group=group, sdate=today, edate=in_week_day, user_id=message.chat.id)
    timetable_for_week = '<b>Розклад на тиждень для групи {}:</b>\n\n'.format(message.text)

    if timetable_data:
        for timetable_day in timetable_data:
            timetable_for_week += render_day_timetable(timetable_day)
    elif isinstance(timetable_data, list) and not len(timetable_data):
        timetable_for_week = 'На тиждень пар для групи {} не знайдено.'.format(group)
    else:
        return

    bot.send_message(message.chat.id, timetable_for_week[:4090], parse_mode='HTML', reply_markup=keyboard)


def show_in_audience(message):

    if message.text == KEYBOARD['MAIN_MENU']:
        bot.send_message(message.chat.id, 'Ok', reply_markup=keyboard)
        return

    audience_numbers_list = []
    day_timetable = ''

    if message.text == 'Всі':
        audience_numbers_list = ['113', '319', '320', '321', '323', '324', '325', '326', '327', '328']
    else:
        audience_numbers_list.append(message.text)

    for audience_number in audience_numbers_list:

        lessons = core.get_lesson_in_audience(audience_number)

        if not lessons:
            continue

        day_timetable += '.....::::: \U0001F4CB Пари для <b>{}</b> ауд. :::::.....\n\n'.format(audience_number)

        timetable = ['9:00 - 10:20', '10:30 - 11:50', '12:10 - 13:30', '13:40 - 15:00',
                     '15:20 - 16:40 ', '16:50 - 18:10', '18:20 - 19:40', '-']

        for lesson in lessons:
            n = int(lesson['lesson_number'])
            if lessons:
                day_timetable += '{} {}\n<b>{}</b> ({}) > {} ({})\n\n'.format(emoji_numbers[n], timetable[n-1],
                                                                              lesson['group'],
                                                                              lesson['teacher'],
                                                                              lesson['title'],
                                                                              lesson['type'])

    bot.send_message(chat_id=message.chat.id, text=day_timetable, parse_mode='HTML', reply_markup=keyboard)


@app.route('/fl1/metrics')
def admin_metrics():

    all_users_count = core.MetricsManager.get_all_users_count()
    users_registered_week = core.MetricsManager.get_number_of_users_registered_during_the_week()
    active_today_users_count = core.MetricsManager.get_active_today_users_count()
    active_yesterday_users_count = core.MetricsManager.get_active_yesterday_users_count()
    active_week_users_count = core.MetricsManager.get_active_week_users_count()

    try:
        forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'groups.txt'))
        groups_update_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%d.%m.%Y %H:%M')
    except Exception:
        groups_update_time = '-'

    try:
        forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'teachers.txt'))
        teachers_update_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%d.%m.%Y %H:%M')
    except Exception:
        teachers_update_time = '-'

    metrics_values = {
        'all_users_count': all_users_count,
        'users_registered_week': users_registered_week,
        'active_today_users_count': active_today_users_count,
        'active_yesterday_users_count': active_yesterday_users_count,
        'active_week_users_count': active_week_users_count,

        'groups_update_time': groups_update_time,
        'teachers_update_time': teachers_update_time,
    }

    return render_template('metrics.html', data=metrics_values)


@app.route('/fl1/del_user', methods=['POST'])
def admin_del_user():

    data = {}

    if request.method == 'POST' and request.form.get('PWD') == request.form.get('ID') + ' 3':

        telegram_id = request.form.get('ID')

        u = core.User.get_username(telegram_id)
        core.User.delete_user(telegram_id)

        if u:
            data['message'] = 'Користувач <b>{} {}</b> був успішно видалений. <br> ' \
                              '<b>група:</b> {}, <b>реєстрація:</b> {}, ' \
                              '<b>остання активність:</b> {}'.format(u[2], u[3] or '', u[4], u[5], u[6])
        else:
            data['message'] = 'Такого користувача не знайдено.'
    else:

        data['message'] = 'Неправильний пароль'

    users = core.MetricsManager.get_users()
    data['users'] = users

    return render_template('users.html', data=data)


@app.route('/fl1/users')
def admin_users():

    data = {
        'users': core.MetricsManager.get_users()
    }

    return render_template('users.html', data=data)


@app.route('/fl1/send_message', methods=['POST'])
def admin_send_message():

    data = {}

    if request.method == 'POST' and request.form.get('pass') == request.form.get('id') + ' 2':

        telegram_id = request.form.get('id')

        data = {
            'chat_id': telegram_id,
            'parse_mode': 'HTML',
            'text': '\U0001f916 <b>Бот</b>:\n\n' + str(request.form.get('text')).strip()
        }

        r = requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data).json()

        if r.get('ok'):
            data['message'] = 'Відправлено'
        else:
            data['message'] = 'Помилка {}: {}'.format(r.get('error_code'), r.get('description'))

    users = core.MetricsManager.get_users()
    data['users'] = users

    return render_template('users.html', data=data)


@app.route('/fl1/statistics_by_types_during_the_week')
def statistics_by_types_during_the_week():

    stats = core.MetricsManager.get_statistics_by_types_during_the_week()

    return jsonify(data=stats)


@app.route('/fl1/last_days_statistics')
def last_days_statistics():

    days_statistics = core.MetricsManager.get_last_days_statistics()

    stats = {'labels': [], 'data': []}

    def sort_by_date(input_str):
        return datetime.datetime.strptime(input_str + '.' + str(datetime.date.today().year), '%d.%m.%Y')

    # Sorting by dates
    for day_stat in sorted(days_statistics, key=sort_by_date):

        stats['labels'].append(day_stat)
        stats['data'].append(days_statistics[day_stat])

    return jsonify(data=stats)


@app.route('/fl1/update_groups')
def admin_update_groups():

    updated = core.update_all_groups()

    if updated:
        msg = 'Список груп оновлено. Завантажено {} груп.<br>'.format(len(updated))
        msg += str(updated)
        return msg
    return 'Помилка при оновленні'


@app.route('/fl1/update_teachers')
def admin_update_teachers():

    updated = core.update_all_teachers()

    if updated:
        msg = 'Список викладачів оновлено. Завантажено {} імен.<br>'.format(len(updated))
        msg += str(updated)
        return msg
    return 'Помилка при оновленні'


@app.route('/fl1/user/<user_id>')
def admin_user_statistics(user_id):

    data = {
        'user': core.User.get_userinfo_by_id(user_id),
        'actions': core.MetricsManager.get_stats_by_user_id(user_id),
    }

    return render_template('user_stat.html', data=data)


@app.route('/fl1/run')
def index():
    core.User.create_user_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()
    core.create_audience_db_if_not_exists()
    bot.delete_webhook()
    bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
    bot.send_message('204560928', 'Running...')
    core.log(m='Webhook is setting: {} by run url'.format(bot.get_webhook_info().url))
    return 'ok'


@app.route(settings.WEBHOOK_PATH, methods=['POST', 'GET'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(content_types=["text"])
def main_menu(message):

    bot.send_chat_action(message.chat.id, "typing")

    user = core.User(message.chat)
    user_name = user.get_full_name()
    request = message.text

    core.log(message.chat, '> {}'.format(message.text))

    if user_name:

        def is_date_request_or_other():

            if re.search(r'^(\d{1,2})\.(\d{1,2})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})-(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

                return 'FOR_A_DATE'

            return 'OTHER'

        # Reversed keys and values in dictionary
        request_code = {v: k for k, v in KEYBOARD.items()}.get(request, is_date_request_or_other())
        core.MetricsManager.track(user.get_id(), request_code, user_name)

        if request == KEYBOARD['TODAY']:

            timetable_data = get_timetable(teacher=user_name, user_id=user.get_id())

            if timetable_data:
                timetable_for_today = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_today = "На сьогодні пар не знайдено."
            else:
                return

            bot.send_message(user.get_id(), timetable_for_today, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['TOMORROW']:  # Tomorrow

            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            tom_day = tomorrow.strftime('%d.%m.%Y')

            timetable_data = get_timetable(teacher=user_name, sdate=tom_day, edate=tom_day, user_id=user.get_id())

            if timetable_data:
                timetable_for_tomorrow = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_tomorrow = "На завтра пар не знайдено."
            else:
                return

            bot.send_message(user.get_id(), timetable_for_tomorrow, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['FOR_A_WEEK']:  # For a week

            if datetime.date.today().isoweekday() in (5, 6, 7):  # пт, сб, нд

                timetable_for_week = ''
                today = datetime.date.today()
                current_week_day_number = today.isoweekday()
                diff_between_saturday_and_today = 6 - current_week_day_number
                next_week_first_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 2)
                next_week_last_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 7)

                timetable_data = get_timetable(teacher=user_name, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                               edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

                if timetable_data:
                    for timetable_day in timetable_data:
                        timetable_for_week += render_day_timetable(timetable_day)

                elif isinstance(timetable_data, list) and not len(timetable_data):
                    timetable_for_week = "На тиждень, з {} по {} пар не знайдено.".format(
                        next_week_first_day.strftime('%d.%m'), next_week_last_day.strftime('%d.%m'))

                bot.send_message(text=timetable_for_week[:4090], chat_id=user.get_id(),
                                 reply_markup=keyboard, parse_mode="HTML")

                return

            week_type_keyboard = telebot.types.InlineKeyboardMarkup()
            week_type_keyboard.row(
                *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
                  name in ["Поточний", "Наступний"]]
            )

            bot.send_message(user.get_id(), 'На який тиждень?', reply_markup=week_type_keyboard)

        elif request == KEYBOARD['TIMETABLE']:

            t = ''
            t += '{} - 9:00 - 10:20\n'.format(emoji_numbers[1])
            t += '{} - 10:30 - 11:50\n'.format(emoji_numbers[2])
            t += '{} - 12:10 - 13:30\n'.format(emoji_numbers[3])
            t += '{} - 13:40 - 15:00\n'.format(emoji_numbers[4])
            t += '{} - 15:20 - 16:40 \n'.format(emoji_numbers[5])
            t += '{} - 16:50 - 18:10 \n'.format(emoji_numbers[6])
            t += '{} - 18:20 - 19:40 \n'.format(emoji_numbers[7])

            bot.send_message(user.get_id(), t, reply_markup=keyboard)

        elif request == KEYBOARD['CHANGE_NAME']:

            user_group = user.get_full_name()

            cancel_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            cancel_kb.row('Відміна')

            msg = 'Збережене ім\'я: {}\nЩоб змінити, введіть нове прізвище'.format(user_group)

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=cancel_kb)
            bot.register_next_step_handler(sent, set_name)

        elif request == KEYBOARD['HELP']:

            msg = "Для пошуку по датам : <b>15.05</b>, <b>15.05-22.05</b>, <b>1.1.18-10.1.18</b>\n\n" \
                  "<b>Ім`я:</b> <code> {}</code>\n\n" \
                  "<b>Канал:</b> @zdu_news\n" \
                  "<b>Новини університету:</b> @zueduua\n" \
                  "<b>Розробник:</b> @Koocherov\n"

            kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.row(KEYBOARD['MAIN_MENU'])
            kb.row(KEYBOARD['CHANGE_NAME'])

            bot.send_message(message.chat.id, msg.format(user.get_full_name()),
                             reply_markup=kb, parse_mode='HTML')

        elif request == KEYBOARD['FOR_A_GROUP']:
            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад будь якої групи на тиждень введіть її назву')
            bot.register_next_step_handler(sent, show_other_group)

        elif request == KEYBOARD['IN_AUDIENCE']:

            now_time = datetime.datetime.now().time()

            lessons_time = ({
                    'start_time': (9, 0),
                    'end_time': (10, 20)
                },
                {
                    'start_time': (10, 30),
                    'end_time': (11, 50)
                },
                {
                    'start_time': (12, 10),
                    'end_time': (13, 30)
                },
                {
                    'start_time': (13, 40),
                    'end_time': (15, 0)
                },
                {
                    'start_time': (15, 20),
                    'end_time': (16, 40)
                },
                {
                    'start_time': (16, 50),
                    'end_time': (18, 10)
                },
                {
                    'start_time': (18, 20),
                    'end_time': (19, 40)
                },
            )

            breaks_time = ({
                   'start_time': (8, 0),
                   'end_time': (9, 0)
               },
                {
                   'start_time': (10, 20),
                   'end_time': (10, 30)
               },
               {
                   'start_time': (11, 50),
                   'end_time': (12, 10)
               },
               {
                   'start_time': (13, 30),
                   'end_time': (13, 40)
               },
               {
                   'start_time': (15, 00),
                   'end_time': (15, 20)
               },
               {
                   'start_time': (16, 40),
                   'end_time': (16, 50)
               },
               {
                   'start_time': (18, 10),
                   'end_time': (18, 20)
               },
            )

            current_lesson = 0
            current_break = -1

            for i, lesson in enumerate(lessons_time):
                if datetime.time(*lesson['start_time']) <= now_time <= datetime.time(*lesson['end_time']):
                    current_lesson = i + 1
                    break

            else:
                for i, _break in enumerate(breaks_time):
                    if datetime.time(*_break['start_time']) <= now_time <= datetime.time(*_break['end_time']):
                        current_break = i
                        break
                else:
                    bot.send_message(message.chat.id, 'Час відпочивати.', parse_mode='HTML', reply_markup=keyboard)
                    return

            msg = ''
            show_for_lesson = 0

            if current_lesson:
                msg = '\U0001F550 Зараз {} пара.'.format(current_lesson)
                show_for_lesson = current_lesson
            elif current_break >= 0:
                msg = '\U0001F6B6 Зараз перерва, далі {} пара'.format(current_break + 1)
                show_for_lesson = current_break + 1

            msg += '\n\n'

            for audience in (319, 320, 321, 323, 324, 325, 326, 327, 328):
                lesson = core.get_lesson_in_audience(audience, show_for_lesson)

                if lesson:
                    msg += '\U0001F4BB <b>{}</b>\n'.format(audience)
                    msg += '<b>{}</b> ({}) > {} ({})\n\n'.format(lesson['group'], lesson['teacher'], lesson['title'], lesson['type'])

            bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['FOR_A_TEACHER']:

            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад викладача на поточний тиждень - '
                                    'введіть його прізвище.')
            bot.register_next_step_handler(sent, select_teachers)

        elif request == KEYBOARD['FOR_A_AUDIENCE']:

            msg = 'Для того щоб подивитись розклад у аудиторії - виберіть потрібну із списку:'

            kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

            kb.row(KEYBOARD['MAIN_MENU'], '113', 'Всі')
            kb.row('319', '320', '321')
            kb.row('323', '324', '325')
            kb.row('326', '327', '328')

            sent = bot.send_message(message.chat.id, msg, reply_markup=kb)
            bot.register_next_step_handler(sent, show_in_audience)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})$', request):

            date = request + '.' + str(datetime.date.today().year)
            timetable_data = get_timetable(teacher=user_name, edate=date, sdate=date, user_id=user.get_id())

            if timetable_data:
                timetable_for_date = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введіть дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не обов\'язково</b> ' \

                timetable_for_date = 'На <b>{}</b>, для <b>{}</b> пар не знайдено.\n\n{}'.format(date, user_name, msg)
            else:
                return

            bot.send_message(message.chat.id, timetable_for_date, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})$', request):

            s_date = message.text.split('-')[0] + '.' + str(datetime.date.today().year)
            e_date = message.text.split('-')[1] + '.' + str(datetime.date.today().year)
            timetable_for_days = ''
            timetable_data = get_timetable(teacher=user_name, sdate=s_date, edate=e_date, user_id=user.get_id())

            if timetable_data:
                for timetable_day in timetable_data:
                    timetable_for_days += render_day_timetable(timetable_day)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введіть дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не обов\'язково</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                      e_date,
                                                                                                      user_name,
                                                                                                      msg)
            else:
                return

            bot.send_message(user.get_id(), timetable_for_days[:4090], parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            date = request
            timetable_data = get_timetable(teacher=user_name, edate=date, sdate=date, user_id=user.get_id())

            if timetable_data:
                timetable_for_date = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введіть дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не обо\'язково</b> ' \

                timetable_for_date = 'На <b>{}</b>, для <b>{}</b> пар не знайдено.\n\n{}'.format(date,
                                                                                                 user_name,
                                                                                                 msg)
            else:
                return

            bot.send_message(message.chat.id, timetable_for_date, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})-(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            s_date = request.split('-')[0]
            e_date = request.split('-')[1]
            timetable_for_days = ''
            timetable_data = get_timetable(teacher=user_name, sdate=s_date, edate=e_date, user_id=user.get_id())

            if timetable_data:
                for timetable_day in timetable_data:
                    timetable_for_days += render_day_timetable(timetable_day)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введіть дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не обов`язково</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                      e_date,
                                                                                                      user_name,
                                                                                                      msg)
            else:
                return

            bot.send_message(user.get_id(), timetable_for_days, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['MAIN_MENU']:
            bot.send_message(user.get_id(), 'Ок', reply_markup=keyboard)

        else:
            answers = ['м?', 'хм.. \U0001F914', 'не розумію(', 'виберіть потрібне в меню']
            bot.send_message(user.get_id(), random.choice(answers), reply_markup=keyboard)

    else:
        bot.send_message(user.get_id(), 'Для початку роботи введіть /start')


def main():

    core.User.create_user_table_if_not_exists()
    core.Cache.create_cache_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()
    core.create_audience_db_if_not_exists()

    bot.delete_webhook()

    if settings.USE_WEBHOOK:
        try:
            bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
            core.log(m='Вебхук встановлено: {}'.format(bot.get_webhook_info().url))

        except Exception as ex:
            core.log(m='Помилка при устіновці веб хука: {}'.format(str(ex)))

    try:
        core.log(m='Running..')
        bot.polling(none_stop=True, interval=settings.POLLING_INTERVAL)

    except Exception as ex:

        core.log(m='Помилка під час роботи: {}\n'.format(str(ex)))
        bot.stop_polling()

        if settings.SEND_ERRORS_TO_ADMIN:
            for admin in settings.ADMINS_ID:
                data = {
                    'chat_id': admin,
                    'text': 'Щось пішло не так.\n {}'.format(str(ex))
                }

                requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)


if __name__ == "__main__":
    app.run(debug=True) if len(sys.argv) > 1 else main()
