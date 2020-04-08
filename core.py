import settings
import sqlite3
import os
import datetime
import json
import requests
import re

class User:

    def __init__(self, chat):
        self.id = chat.id
        self.chat = chat

    def get_id(self):
        return self.id

    def get_full_name(self):

        query = "SELECT name FROM users WHERE t_id=?"

        result = DBManager.execute_query(query, (self.id,))

        if type(result) == bool:
            return False

        # TODO add return error code if there are problems getting the group
        # something like - if type(result) == bool: return -1

        self.update_user_metadata()

        return result[0][0]

    def update_name(self, name):

        log(self.chat, 'Has changed name to {}'.format(name))

        query = "UPDATE users SET name=? WHERE t_id=?"
        return DBManager.execute_query(query, (name, self.id))

    def registration(self, name):

        log(self.chat, 'Has been registered ({})'.format(name))

        query = "INSERT INTO users (t_id, username, first_name, last_name, name, register_date) " \
                "VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))"
        return DBManager.execute_query(query,
                                       (self.id, self.chat.username, self.chat.first_name,
                                        self.chat.last_name, name))
    
    def update_user_metadata(self):

        query = "UPDATE users SET requests_count=requests_count+1, last_use_date=datetime('now', 'localtime')," \
                "first_name=?, last_name=?, username=? WHERE t_id=?"
        return DBManager.execute_query(query, (self.chat.first_name, self.chat.last_name, self.chat.username, self.id,))

    @classmethod
    def create_user_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS users(
                      t_id TEXT PRIMARY KEY NOT NULL,
                      username TEXT,
                      first_name TEXT,
                      last_name TEXT,
                      name TEXT,
                      register_date TEXT DEFAULT (datetime('now', 'localtime')),
                      last_use_date DEFAULT (datetime('now', 'localtime')),
                      requests_count INTEGER DEFAULT 0) WITHOUT ROWID"""

        return DBManager.execute_query(query)

    @classmethod
    def get_userinfo_by_id(cls, t_id):

        query = "SELECT * FROM users WHERE t_id=?"

        result = DBManager.execute_query(query, (t_id,))

        if type(result) == bool:
            return False

        return result[0]

    @classmethod
    def delete_user(cls, t_id):

        query = "DELETE FROM users WHERE t_id=?"

        return DBManager.execute_query(query, (t_id,))


class DBManager:

    @classmethod
    def execute_query(cls, query, *args):  # returns result or true if success, or false when something go wrong

        try:
            connection = sqlite3.connect(os.path.join(settings.BASE_DIR, settings.DATABASE), check_same_thread=False)

            cursor = connection.cursor()
            cursor.execute(query, *args)
            connection.commit()
            query_result = cursor.fetchall()
            cursor.close()
            connection.close()

            if query_result:
                return query_result
            return False

        except sqlite3.Error as ex:

            log(m='Query error: {}'.format(str(ex)))
            return -1


def log(chat=None, m=''):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'a', encoding="utf-8") as log_file:
        if chat:
            log_file.write('[{}]: ({} {}) {}\n'.format(now_time, chat.first_name, chat.last_name, m))
        else:
            log_file.write('[{}]: (Server) {}\n'.format(now_time, m))


class Cache:

    @classmethod
    def create_cache_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS cache(
                          key TEXT PRIMARY KEY NOT NULL,
                          data TEXT DEFAULT CURRENT_TIMESTAMP,
                          create_time TEXT,
                          requests INTEGER DEFAULT 0)
                          WITHOUT ROWID"""

        return DBManager.execute_query(query)

    @classmethod
    def get_from_cache(cls, key):

        query = "SELECT * FROM cache WHERE key=?"

        r = DBManager.execute_query(query, (key,))
        if r:
            cls.recount_requests_to_cache(key)

        return r

    @classmethod
    def recount_requests_to_cache(cls, key):

        query = "UPDATE cache SET requests=requests+1 WHERE key=?"
        return DBManager.execute_query(query, (key,))

    @classmethod
    def put_in_cache(cls, key, data):

        query = "INSERT or IGNORE INTO cache (key, data, create_time) VALUES (?, ?, CURRENT_TIMESTAMP)"
        return DBManager.execute_query(query, (key, data))

    @classmethod
    def get_keys(cls):

        query = "SELECT key FROM cache"
        return DBManager.execute_query(query, )

    @classmethod
    def clear_cache(cls):

        query = "DELETE FROM cache"
        return DBManager.execute_query(query, )


class MetricsManager:

    @classmethod
    def create_metrics_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS metrics(
                      request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id TEXT,
                      request_type TEXT,
                      name TEXT,
                      request_datetime DEFAULT (datetime('now', 'localtime')))"""

        return DBManager.execute_query(query)

    @classmethod
    def track(cls, telegram_id='0', request_type=0, user_name=''):

        query = """INSERT INTO metrics (
        telegram_id, 
        request_type, 
        name) VALUES (?, ?, ?)"""

        return DBManager.execute_query(query, (telegram_id, request_type, user_name))

    @classmethod
    def get_all_users_count(cls):

        query = "SELECT COUNT(*) FROM users"

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_today_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id) 
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime', 'start of day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_yesterday_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id) 
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime','start of day', '-1 day') 
        and request_datetime < datetime('now', 'localtime', 'start of day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_week_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id)
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime', 'start of day', '-7 day') 
        and request_datetime < datetime('now', 'localtime', 'start of day', '+1 day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_number_of_users_registered_during_the_week(cls):

        query = """SELECT COUNT(*)
        FROM users 
        WHERE register_date > datetime('now','localtime', 'start of day', '-7 day') 
        and register_date < datetime('now', 'localtime', 'start of day', '+1 day')
        """

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_statistics_by_types_during_the_week(cls):

        query = """SELECT request_type, count(request_id) as 'count' FROM metrics 
        WHERE request_datetime > datetime('now','localtime', 'start of day', '-7 day')
        and request_datetime < datetime('now', 'localtime', 'start of day', '+1 day')
        GROUP BY request_type"""

        result = DBManager.execute_query(query)

        if result:
            return dict(result)

        return {}

    @classmethod
    def get_last_days_statistics(cls):

        statistic = {}
        today = datetime.date.today()

        for i in range(15):
            previous_day = today - datetime.timedelta(days=i)
            previous_day_str = previous_day.strftime('%Y-%m-%d')

            query = """SELECT COUNT(*)
            FROM metrics
            WHERE request_datetime > datetime('{}')
            and request_datetime < datetime('{}', '+1 days')""".format(previous_day_str,
                                                                       previous_day_str)

            statistic[previous_day.strftime('%d.%m')] = DBManager.execute_query(query)[0][0]

        return statistic

    @classmethod
    def get_users(cls):

        query = """SELECT * From users"""

        users_selection = DBManager.execute_query(query)

        users = []

        if not users_selection:
            return users

        for user in users_selection:
            users.append({
                'telegram_id': user[0],
                'username': user[1] or '-',
                'first_name': user[2],
                'last_name': user[3] or '-',
                'name': user[4],
                'register_date': user[5],
                'last_use_date': user[6],
                'requests_count': user[7],
            })

        return users

    @classmethod
    def get_stats_by_user_id(cls, user_id):

        query = """SELECT * From metrics WHERE telegram_id = ?"""

        user_actions_raw = DBManager.execute_query(query, (user_id, ))
        user_actions = []

        if not user_actions_raw:
            return user_actions.append({
                'action_id': '-',
                'action_type': '-',
                'action_name': '-',
                'action_date': '-',
            })

        for action in user_actions_raw:
            user_actions.append({
                'action_id': action[0],
                'action_type': settings.KEYBOARD.get(action[2], '-'),
                'action_name': action[3],
                'action_date': action[4],
            })

        return user_actions


def update_all_groups():

    params = {
        'n': '701',
        'lev': '142',
        'faculty': '0',
        'query': '',
    }

    response = requests.get(settings.TIMETABLE_URL, params).json()

    if isinstance(response, dict):
        tmp_groups = response.get('suggestions', [])
    else:
        tmp_groups = []

    groups = []

    [groups.append(g.lower()) for g in tmp_groups]

    with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'w', encoding="utf-8") as file:
        file.write(json.dumps(groups, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2))

    with open(os.path.join(settings.BASE_DIR, 'valid_case_groups.txt'), 'w', encoding="utf-8") as file:
        file.write(json.dumps(tmp_groups, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2))

    return groups


def is_group_valid(user_group=''):

    user_group = user_group.lower().strip()

    try:
        with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'r', encoding="utf-8") as file:
            all_groups = json.loads(file.read())

        return user_group in all_groups

    except Exception as ex:
        log(m='Validation group error: {}'.format(str(ex)))
        return True


def get_possible_groups(user_group='', variants=4):

    def get_tanimoto_koef(s1, s2):
        a, b, c = len(s1), len(s2), 0.0

        for sym in s1:
            if sym in s2:
                c += 1

        return c / (a + b - c)

    possible_groups = []

    with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'r', encoding="utf-8") as file:
        all_groups = json.loads(file.read())

    for group in all_groups:
        tanimoto_koef = get_tanimoto_koef(user_group, group)
        if tanimoto_koef > 0.5:
            possible_groups.append({
                'k': tanimoto_koef,
                'group': group
            })

    sorted_groups = sorted(possible_groups, key=lambda d: d['k'], reverse=True)

    return sorted_groups[:variants]


def update_all_teachers():

    params = {
        'n': '701',
        'lev': '141',
        'faculty': '0',
        'query': '',
    }

    response = requests.get(settings.TIMETABLE_URL, params).json()

    if isinstance(response, dict):
        teachers = response.get('suggestions', [])
    else:
        teachers = []

    with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'w', encoding="utf-8") as file:
        file.write(json.dumps(teachers, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2))

    return teachers


def create_audience_db_if_not_exists():

    query = """CREATE TABLE IF NOT EXISTS timetable(
                  t_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  t_lesson_number TEXT,
                  t_group TEXT,
                  t_lesson TEXT,
                  t_audience TEXT)"""

    return DBManager.execute_query(query)


def add_lesson(number=None, group='', lesson='', audience=None):

    query = """INSERT INTO timetable(
                                     t_lesson_number, 
                                     t_group,
                                     t_lesson,
                                     t_audience
                                     ) VALUES (?, ?, ?, ?)"""

    return DBManager.execute_query(query, (number, group, lesson, audience))


def check_lesson(lsn):

    lessons_list = []

    if lsn.count('/№') == 1:

        if lsn[5] == '1':
            lessons_list.append({
                'lesson_audience': lsn.split('/')[0],
                'lesson_name': lsn[7:],
            })

    elif lsn.count('/№') == 2:
        positions = [m.start() for m in re.finditer('/№', lsn)]

        if lsn[5] == '1':
            lessons_list.append({
                'lesson_audience': lsn.split('/')[0],
                'lesson_name': lsn[7:positions[1]-4],
            })

        if lsn[positions[1]+2] == '1':
            sec_group = lsn[positions[1]-3:]

            lessons_list.append({
                'lesson_audience': sec_group.split('/')[0],
                'lesson_name': sec_group[7:positions[1]-2],
            })

    return lessons_list


def get_lesson_in_audience(audience_number=0, lesson_number=0):

    audience_number = int(audience_number)

    rooms = {
        113: 23,
        319: 35,
        320: 36,
        321: 37,
        323: 38,
        324: 39,
        325: 40,
        326: 41,
        327: 42,
        328: 43,
    }

    today = datetime.date.today().strftime('%d.%m.%Y')
    # today = '20.2.2020'

    try:
        data = {
            'req_type': 'rozklad',
            'req_mode': 'room',
            'OBJ_ID': rooms.get(audience_number, 0),
            'OBJ_name': '',
            'dep_name': '',
            'ros_text': 'separated',
            # 'show_empty': 'no',
            'begin_date': today,
            'end_date': today,
            'req_format': 'json',
            'coding_mode': 'UTF8',
            'bs': 'ok',
        }

        # try:
        r = requests.get('https://dekanat.zu.edu.ua/cgi-bin/timetable_export.cgi', params=data)

        day_lessons = r.json().get('psrozklad_export', {}).get('roz_items', [])

        for lesson in day_lessons:
            if lesson_number:
                if lesson['lesson_number'] == str(lesson_number):
                    return lesson
            else:
                return day_lessons
        else:
            return []

    except Exception as ex:

        log(m='Помилка під час перегляду розкладу по аудиторіям.\n{}'.format(str(ex)))
        return []


def clear_audience_timetables():

    query = "DELETE FROM timetable"
    DBManager.execute_query(query, )


def clear_cache_audiences():

    query = "DELETE FROM timetable"
    return DBManager.execute_query(query, )
