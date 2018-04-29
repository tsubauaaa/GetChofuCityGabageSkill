import boto3
import json
import os
import urllib.request
from datetime import datetime, timedelta


def fetch_garbage_type(district_num, target_date):
    bucket_name = os.environ['BUCKET_NAME']
    year_month = target_date[0:8]
    day = target_date[8:10]
    key_name = "garbage_calender/district" + \
        str(district_num) + "/" + year_month + "garbage_calender.csv"
    s3_client = boto3.client('s3')
    res = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    garbage_calender = res['Body'].read().decode('utf-8')
    garbage_type = "不明"
    for line in garbage_calender.split('\n'):
        if day == line.split(',')[0]:
            garbage_type = line.split(',')[1]

    return garbage_type


def find_district_number(zip_code):
    zipcloud_url = "http://zipcloud.ibsnet.co.jp/api/search"
    params = {'zipcode': zip_code}
    req = urllib.request.Request(
        zipcloud_url + "?" + urllib.parse.urlencode(params))
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())
    address3 = addr_data['results'][0]['address3']

    if address3 in {"仙川町", "入間町", "若葉町", "緑ケ丘", "国領町"}:
        district_num = 1
    elif address3 in {"西つつじケ丘", "菊野台", "飛田給", "上石原", "東つつじケ丘", "富士見町", "野水", "西町"}:
        district_num = 2
    elif address3 in {"深大寺東町", "深大寺元町", "布田", "深大寺北町", "深大寺南町", "染地"}:
        district_num = 3
    elif address3 in {"調布ケ丘", "柴崎", "多摩川", "下石原", "八雲台", "佐須町", "小島町"}:
        district_num = 4
    else:
        district_num = 1
    return district_num


def fetch_zip_code(api_host, device_id, access_token):
    endpoint_url = api_host + "/v1/devices/" + \
        device_id + "/settings/address/countryAndPostalCode"
    headers = {"Authorization": "Bearer " + access_token}
    req = urllib.request.Request(endpoint_url, headers=headers)
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())
    return addr_data['postalCode'].replace('-', '')


def create_week_dictionary():
    keys = []
    values = []
    for i in range(7):
        keys.append((datetime.now() + timedelta(i)).weekday())
        values.append((datetime.now() + timedelta(i)).strftime("%Y/%m/%d"))
    return dict(zip(keys, values))


def lambda_handler(event, context):
    print(event)
    try:
        api_endpoint = event['context']['System']['apiEndpoint']
        device_id = event['context']['System']['device']['deviceId']
        token = event['context']['System']['user']['permissions']['consentToken']
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

    intent = event['request']['intent']
    when = intent['slots']['When']['value']
    week = create_week_dictionary()

    if when == "今日":
        target_date = datetime.now().strftime('%Y/%m/%d')
    elif when == "明日":
        target_date = (datetime.now() + timedelta(1)).strftime('%Y/%m/%d')
    elif when == "月曜日":
        target_date = week[0]
    elif when == "火曜日":
        target_date = week[1]
    elif when == "水曜日":
        target_date = week[2]
    elif when == "木曜日":
        target_date = week[3]
    elif when == "金曜日":
        target_date = week[4]
    elif when == "土曜日":
        target_date = week[5]
    elif when == "日曜日":
        target_date = week[6]

    garbage_type = fetch_garbage_type(district_num, target_date)

    text = when + "の第" + str(district_num) + "地区のごみ出しは" + garbage_type + "です。"
    response = {
        'version': '1.0',
        'response': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': text
            }
        }
    }
    return response
