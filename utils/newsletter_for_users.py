import requests
import time
import sqlite3


TOKEN = ''
connection = sqlite3.connect('users_db.sqlite', check_same_thread=False)

cursor = connection.cursor()
cursor.execute("""SELECT t_id FROM users""")
connection.commit()
rez = cursor.fetchall()
cursor.close()


msg = 'Some message'

i = 1

for _id in rez:
    r = requests.get('https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}'.format(TOKEN, _id[0], msg))
    print(i, _id[0], r.status_code)
    i = i + 1
    time.sleep(0.3)
