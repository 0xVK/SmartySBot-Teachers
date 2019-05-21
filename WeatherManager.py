# -*- coding: utf-8 -*-
import requests
import datetime
import settings
import os
import core


class WeatherManager:

    API_LINK_FORECAST = 'http://api.openweathermap.org/data/2.5/forecast'

    def getEmoji(self, weather_id):

        # Openweathermap Weather codes and corressponding emojis
        thunderstorm = u'\U0001F4A8'  # Code: 200's, 900, 901, 902, 905
        drizzle = u'\U0001F4A7'  # Code: 300's
        rain = u'\U00002614'  # Code: 500's
        snowflake = u'\U00002744'  # Code: 600's snowflake
        snowman = u'\U000026C4'  # Code: 600's snowman, 903, 906
        atmosphere = u'\U0001F301'  # Code: 700's foogy
        clear_sky = u'\U00002600'  # Code: 800 clear sky
        few_clouds = u'\U000026C5'  # Code: 801 sun behind clouds
        clouds = u'\U00002601'  # Code: 802-803-804 clouds general
        hot = u'\U0001F525'  # Code: 904
        default_emoji = u'\U0001F300'  # default emojis

        if weather_id:
            if str(weather_id)[0] == '2' or weather_id in (900, 901, 902, 905):
                return thunderstorm
            elif str(weather_id)[0] == '3':
                return drizzle
            elif str(weather_id)[0] == '5':
                return rain
            elif str(weather_id)[0] == '6' or weather_id in (903, 906):
                return snowflake + ' ' + snowman
            elif str(weather_id)[0] == '7':
                return atmosphere
            elif weather_id == 800:
                return clear_sky
            elif weather_id == 801:
                return few_clouds
            elif weather_id == 802 or weather_id == 803 or weather_id == 803:
                return clouds
            elif weather_id == 904:
                return hot
            else:
                return default_emoji

        else:
            return default_emoji

    def render_forecast(self, date, temp, weather_emoji, desc):

        clocks_emoji = {
            9: '\U0001F558',
            12: '\U0001F55B',
            15: '\U0001F552',
            18: '\U0001F555',
            21: '\U0001F558',
        }

        r = ''
        r += '{} {} - \U0001F321{}\U000000B0 {} <i>{}</i>\n'. \
            format(clocks_emoji.get(date.hour, '-'), date.strftime('%H:%M'), int(temp), weather_emoji, desc)

        return r

    def update_forecast(self):

        request_params = {
            'APPID': settings.OPEN_WEATHER_MAP_TOKEN,
            'id': '686967',  # Zhytomyr ID
            'units': 'metric',
            'lang': 'uk'
        }

        r = requests.get(self.API_LINK_FORECAST, params=request_params)
        five_days_weather_forecast = r.json()

        try:
            zdu_temperature = requests.get('https://zu.edu.ua/t.asp', timeout=2).text[:-1].strip()

        except Exception as ex:
            zdu_temperature = ''
            core.log(m='Error with getting ZDU temperature: {}'.format(str(ex)))

        today_day = datetime.datetime.now().day
        tomorrow_date = datetime.datetime.now() + datetime.timedelta(days=1)
        tomorrow_day = tomorrow_date.day

        hidden_hours = [0, 3, 2, 5, 6]

        result = ''

        if zdu_temperature:
            result += 'Біля університету: %s°\n\n' % zdu_temperature

        result += ':::::: \U0001F30E <b>Сьогодні:</b> ::::::\n'
        for hour_forecast in five_days_weather_forecast['list']:

            forecast_time = datetime.datetime.fromtimestamp(hour_forecast['dt'])
            if forecast_time.day == today_day:
                if forecast_time.hour not in hidden_hours:
                    result += self.render_forecast(forecast_time,
                                                   hour_forecast['main']['temp'],
                                                   self.getEmoji(hour_forecast['weather'][0]['id']),
                                                   hour_forecast['weather'][0]['description'])

        result += '\n:::::: \U0001F30E <b>Завтра:</b> ::::::\n'
        for hour_forecast in five_days_weather_forecast['list']:

            forecast_time = datetime.datetime.fromtimestamp(hour_forecast['dt'])
            if forecast_time.day == tomorrow_day:
                if forecast_time.hour not in hidden_hours:
                    result += self.render_forecast(forecast_time,
                                                   hour_forecast['main']['temp'],
                                                   self.getEmoji(hour_forecast['weather'][0]['id']),
                                                   hour_forecast['weather'][0]['description'])

        with open(os.path.join(settings.BASE_DIR, 'forecast.txt'), 'w', encoding="utf-8") as f_file:
            f_file.write(result)

    def check_if_forecast_need_update(self):

        # TODO Fix it

        return True

        file_name = os.path.join(settings.BASE_DIR, 'forecast.txt')
        if not os.path.isfile(file_name):
            return True

        forecast_update_date = os.path.getmtime(file_name)
        mod_time = datetime.date.fromtimestamp(forecast_update_date)

        return datetime.date.today() != mod_time

    def process_weather(self):

        if self.check_if_forecast_need_update():
            self.update_forecast()
            #core.log(m='Оновлення погоди')
