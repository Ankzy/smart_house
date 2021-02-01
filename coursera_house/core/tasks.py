from __future__ import absolute_import, unicode_literals
from celery import task
from django.http import HttpResponse
from .models import Setting
from coursera_house.settings import SMART_HOME_API_URL, SMART_HOME_ACCESS_TOKEN
import requests
import json

@task()
def smart_home_manager():
    states = CleverSystem.get_controller_state()
    new_states = {}
    if not EventReactions.is_leak_detector(states, new_states):
        if not states['cold_water']:
            EventReactions.is_cold_water_closed(states, new_states)
    if not EventReactions.is_smoke_detector(states, new_states):
        EventReactions.is_boiler_needed(states, new_states)
        EventReactions.is_conditioner_needed(states, new_states)
    if states['curtains'] != 'slightly_open':
        EventReactions.put_curtains_state(states, new_states)

    if new_states:
        CleverSystem.put_controller_state(new_states)

#-----------------------------------------------------------------------------------------------------------------------

class CleverSystem():
    url = SMART_HOME_API_URL
    token = 'Bearer {}'.format(SMART_HOME_ACCESS_TOKEN)
    headers = {'Authorization': token}
    resp_get_code = 0

    # get states of all controllers from API
    @classmethod
    def get_controller_state(cls):
        detectors = {}
        response = requests.get(cls.url, headers=cls.headers)
        cls.resp_get_code = response.status_code
        if cls.resp_get_code == 200:
            data = response.json()
            for detector in data['data']:
                detectors[detector['name']] = detector['value']
            return detectors
        return HttpResponse(status=502)

    # set new states of controllers
    @classmethod
    def put_controller_state(cls, new_states):
        controllers = []
        for name, value in new_states.items():
            controllers.append({'name': name, 'value': value})
        response = requests.post(cls.url, headers=cls.headers, data=json.dumps({'controllers': controllers}))


#-----------------------------------------------------------------------------------------------------------------------


class DBSettings:
    @staticmethod
    def get_value(name):
        if Setting.objects.filter(controller_name=name):
            return Setting.objects.get(controller_name=name).value
        else:
            if name=='bedroom_target_temperature':
                stng = Setting(controller_name=name, value=21)
            elif name=='hot_water_target_temperature':
                stng = Setting(controller_name=name, value=80)
            stng.save()
            return stng.value

    @staticmethod
    def set_value(name, value):
        stng = Setting.objects.get(controller_name=name)
        stng.value = value
        stng.save()


#-----------------------------------------------------------------------------------------------------------------------


class EventReactions:
    @staticmethod
    def is_leak_detector(states, new_states):
        if states['leak_detector']:
            if states['cold_water']:
                new_states['cold_water'] = False
            if states['hot_water']:
                new_states['hot_water'] = False
            if states['boiler']:
                new_states['boiler'] = False
            if states['washing_machine']=='on' or states['washing_machine']=='broken':
                new_states['washing_machine'] = 'off'
            return True
        return False

    @staticmethod
    def is_cold_water_closed(states, new_states):
        if states['boiler']:
            new_states['boiler'] = False
        if states['washing_machine']=='on' or states['washing_machine']=='broken':
            new_states['washing_machine'] = 'off'

    @staticmethod
    def is_boiler_needed(states, new_states):
        if not states['boiler'] and states['boiler_temperature'] is not None and \
                states['boiler_temperature'] < (DBSettings.get_value('hot_water_target_temperature') * 0.9):
            if not states['cold_water']:
                new_states['cold_water'] = True
            new_states['boiler'] = True
        if states['boiler'] and states['boiler_temperature'] is not None and \
                states['boiler_temperature'] >= (DBSettings.get_value('hot_water_target_temperature') * 1.1):
            new_states['boiler'] = False

    @staticmethod
    def is_smoke_detector(states, new_states):
        if states['smoke_detector']:
            if states['air_conditioner']:
                new_states['air_conditioner'] = False
            if states['bedroom_light']:
                new_states['bedroom_light'] = False
            if states['bathroom_light']:
                new_states['bathroom_light'] = False
            if states['boiler']:
                new_states['boiler'] = False
            if states['washing_machine']=='on' or states['washing_machine']=='broken':
                new_states['washing_machine'] = False
            return True
        return False

    @staticmethod
    def put_curtains_state(states, new_states):
        if states['outdoor_light'] < 50 and not states['bedroom_light']:
            if states['curtains'] == 'close':
                new_states['curtains'] = 'open'
        else:
            if states['curtains'] == 'open':
                new_states['curtains'] = 'close'

    @staticmethod
    def is_conditioner_needed(states, new_states):
        if not states['air_conditioner'] and \
                states['bedroom_temperature'] > DBSettings.get_value('bedroom_target_temperature') * 1.1:
            new_states['air_conditioner'] = True
        if states['air_conditioner'] and \
                states['bedroom_temperature'] < DBSettings.get_value('bedroom_target_temperature') * 0.9:
            new_states['air_conditioner'] = False


