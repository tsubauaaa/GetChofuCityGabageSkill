from datetime import datetime, timedelta
import json
import urllib2


def describe_device_address(api_host, device_id, access_token):
    req = urllib2.Request("{}/v1/devices/{}/settings/address".format(api_host, device_id))
    req.add_header("Authorization", "Bearer {}".format(access_token))
    response = urllib2.urlopen(req)
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
