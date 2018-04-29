import json
import urllib.request
from datetime import datetime, timedelta


def describe_device_address(api_host, device_id, access_token):
    headers = {"Authorization": "Bearer " + access_token}
    endpoint = api_host + "/v1/devices/" + device_id + "/settings/address"
    req = urllib.request.Request(endpoint, headers=headers)
    response = urllib.request.urlopen(req)
    if response.getcode() == 200:
        return json.loads(response.read())
    else:
        print(response.getcode())
        raise Exception(response.msg)


def create_week_dictionary():
    keys = []
    values = []
    for i in range(7):
        keys.append((datetime.now()+timedelta(i)).weekday())
        values.append((datetime.now()+timedelta(i)).strftime("%Y%m%d"))
    return dict(zip(keys, values))


def lambda_handler(event, context):
    print(event)
    api_host = event["context"]["System"]["apiEndpoint"]
    device_id = event["context"]["System"]["device"]["deviceId"]
    token = event["context"]["System"]["user"]["permissions"]["consentToken"]

    address = describe_device_address(api_host, device_id, token)

    print(address)

    today = datetime.now().strftime("%Y%m%d")
    tommorow = (datetime.now()+timedelta(1)).strftime("%Y%m%d")
    week = create_week_dictionary()
    intent = event['request']['intent']
    print(intent)
    when = intent['slots']['When']['value']

    garbage = ""
    if when == '今日':
        garbage = '燃えるゴミの日です。'
    elif when == '明日':
        garbage = '燃えないゴミの日は水曜日です。'

    response = {
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': garbage
            }
        }
    }
    return response
