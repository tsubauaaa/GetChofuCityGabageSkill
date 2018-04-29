import json
import urllib.request
from datetime import datetime, timedelta


def find_district_number(zip_code):
    zipcloud_url = "http://zipcloud.ibsnet.co.jp/api/search"
    params = {'zipcode': zip_code}
    req = urllib.request.Request(
        zipcloud_url + "?" + urllib.parse.urlencode(params))
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())
    address3 = addr_data['results'][0]['address3']

    return 1


def fetch_zip_code(api_host, device_id, access_token):
    endpoint_url = api_host + "/v1/devices/" + \
        device_id + "/settings/address/countryAndPostalCode"
    headers = {"Authorization": "Bearer " + access_token}
    req = urllib.request.Request(endpoint_url, headers=headers)
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())
    return addr_data['postalCode'].replace("-", "")


def create_week_dictionary():
    keys = []
    values = []
    for i in range(7):
        keys.append((datetime.now() + timedelta(i)).weekday())
        values.append((datetime.now() + timedelta(i)).strftime("%Y%m%d"))
    return dict(zip(keys, values))


def lambda_handler(event, context):
    try:
        api_endpoint = event["context"]["System"]["apiEndpoint"]
        device_id = event["context"]["System"]["device"]["deviceId"]
        token = event["context"]["System"]["user"]["permissions"]["consentToken"]
    except KeyError:
        api_endpoint = None
        device_id = None
        token = None

    zip_code = None
    if api_endpoint and device_id and token:
        zip_code = fetch_zip_code(api_endpoint, device_id, token)

    district_num = 1
    if zip_code:
        district_num = find_district_number(zip_code)

    print("地区は" + str(district_num) + "です")

    today = datetime.now().strftime("%Y%m%d")
    tommorow = (datetime.now() + timedelta(1)).strftime("%Y%m%d")
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
