# -*- coding: utf-8 -*-
import os

# Bot version
VERSION = '1.0'

# Database name
DATABASE = 'SmartyST_DB.sqlite'

# Telegram Bot token
BOT_TOKEN = '<TOKEN>'

# OpenWeatherMap.org token
OPEN_WEATHER_MAP_TOKEN = '<TOKEN>'

# Interval to polling telegram servers (Uses if USE_WEBHOOK sets False)
POLLING_INTERVAL = 1

# Use cache
USE_CACHE = False

# Use webhook instead polling
USE_WEBHOOK = 0

# Address bot running. For example https://mydomain.com
WEBHOOK_URL = '<URL>'

# Path that telegram sends updates
WEBHOOK_PATH = '/fl1/'

# Timetable URL
TIMETABLE_URL = 'https://dekanat.zu.edu.ua/cgi-bin/timetable.cgi'

# Http user agent sends to requests
HTTP_USER_AGENT = 'Telegram-SmartyTSBot'

# If it True, bot would send errors to admins in list below
SEND_ERRORS_TO_ADMIN = True

# Admins IDS
ADMINS_ID = ['204560928', '203448442']

# Base folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Keyboard buttons
KEYBOARD = {
    'TODAY': '\U0001F4D8 Сьогодні',
    'TOMORROW': '\U0001F4D9 Завтра',
    'FOR_A_WEEK': '\U0001F4DA Тиждень',
    'FOR_A_TEACHER': '\U0001F464 По викладачу',
    'TIMETABLE': '\U0001F552 Час пар',
    'FOR_A_GROUP': '\U0001F465 По групі',
    'WEATHER': '\U0001F30D Погода',
    'HELP': '\U0001F4AC Довідка',

    'CHANGE_NAME': '\U00002699 Зм. прізвище',
    'MAIN_MENU': '\U0001F519 Меню',
}
