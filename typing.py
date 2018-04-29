import sys
import urllib
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen
import json
import websocket
import uuid
from functools import partialmethod

class SlackWeb():
    def __init__(self, token):
        self.token = token

    def slack_request(self, *, path, data = None):
        auth_data = {
            'token': self.token
        }
        if data is None:
            data = {}

        data = { **auth_data, **data }

        print(data)

        url = 'https://slack.com/api/{}'.format(path)
        req = Request(url, data = urlencode(data).encode())
        resp = urlopen(req)
        body = resp.read()
        print(path, ' => ', body)
        parsed = json.loads(body)
        if parsed.get('ok') != True:
            raise Exception(body)
        return parsed

    def get_channel_info(self, id):
        return self.slack_request(path ='groups.info', data = { 'channel': id })

    def get_dnd_info(self):
        return self.slack_request(path = 'dnd.info')

    def set_dnd_snooze(self, minutes):
        return self.slack_request(path = 'dnd.setSnooze', data = { 'num_minutes': minutes })

    def rtm_connect(self):
        return self.slack_request(path='rtm.connect')

class SlackRTM():

    def __init__(self, url, on_message, on_error, on_close):
        self.ws = websocket.WebSocketApp(url,
                                    on_message = on_message,
                                    on_error = on_error,
                                    on_close = on_close)

def on_message(ws, message):
    parsed = json.loads(message)
    print('WS message: ', message)

    if not 'channel' in parsed or not is_direct_message(parsed['channel']):
        return

    if   parsed['type'] == 'message':
        return deal_with_annoyance(ws, parsed)
    elif parsed['type'] == 'user_typing':
        return deal_with_annoyance(ws, parsed)

def on_error(ws, error):
    print('WS error: ', error)

def on_close(ws):
    print('WS closed')

def deal_with_annoyance(ws, message):
    dnd = slack_web.get_dnd_info()
    if 'snooze_enabled' in dnd and dnd['snooze_enabled']:
        return

    remaining = 10

    print('Annoying message received, snoozing for ' + str(remaining) + ' minutes')

    ws.send(json.dumps({
        'id': uuid.uuid4().hex,
        'type': 'typing',
        'channel': message['channel']
    }))
    slack_web.set_dnd_snooze(str(remaining))

def is_direct_message(id):
    return id.startswith('D')

def is_channel(id):
    return id.startswith('C') or id.startsWith('G')

slack_web = None

def main():
    global slack_web

    slack_web = SlackWeb(os.environ['SLACK_TOKEN'])
    rtmResponse = slack_web.rtm_connect()

    print('Connected', rtmResponse)

    rtm = SlackRTM(rtmResponse['url'], on_message, on_error, on_close)

    print('Listening...')


    rtm.ws.run_forever()

main()
