import boto3
import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_all_response(response):
    return {
        'version': '1.0',
        'response': response
    }


def create_response(output_text, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output_text
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def create_week_dictionary():
    day_week = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    keys = []
    values = []
    for i in range(7):
        keys.append(day_week[(datetime.now() + timedelta(i)).weekday()])
        values.append((datetime.now() + timedelta(i)).strftime("%Y/%m/%d"))

    return dict(zip(keys, values))


def find_target_date(when_id, when_name):
    if when_id == "today":
        target_date = datetime.now().strftime('%Y/%m/%d')
    elif when_id == "tomorrow":
        target_date = (datetime.now() + timedelta(1)).strftime('%Y/%m/%d')
    elif when_id.split("-")[0] == "dayofweek":
        week = create_week_dictionary()
        target_date = week[when_name]

    return target_date


def fetch_garbage_type(district_num, target_date):
    bucket_name = os.environ['BUCKET_NAME']
    year_month = target_date[0:8]
    day = target_date[8:10]
    key_name = "garbage_calender/district{}/{}garbage_calender.csv".format(
        str(district_num), year_month)
    s3_client = boto3.client('s3')
    res = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    garbage_calender = res['Body'].read().decode('utf-8')
    for line in garbage_calender.split("\n"):
        if day == line.split(",")[0]:
            garbage_type = line.split(",")[1]

    return garbage_type


def find_district_number(zip_code):
    # TODO: zipcloud_urlを環境変数化する
    zipcloud_url = "http://zipcloud.ibsnet.co.jp/api/search"
    params = {'zipcode': zip_code}
    req = urllib.request.Request(
        zipcloud_url + "?" + urllib.parse.urlencode(params))
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())
    address3 = addr_data['results'][0]['address3']

    if address3 in {"仙川町", "入間町", "若葉町", "緑ケ丘", "国領町"}:
        district_num = 1
    elif address3 \
            in {"西つつじケ丘", "菊野台", "飛田給", "上石原", "東つつじケ丘", "富士見町", "野水", "西町"}:
        district_num = 2
    elif address3 in {"深大寺東町", "深大寺元町", "布田", "深大寺北町", "深大寺南町", "染地"}:
        district_num = 3
    elif address3 in {"調布ケ丘", "柴崎", "多摩川", "下石原", "八雲台", "佐須町", "小島町"}:
        district_num = 4
    else:
        # 調布市じゃない場合は第一地区とする
        district_num = 1

    return district_num


def fetch_zip_code(api_host, device_id, access_token):
    url = "{}/v1/devices/{}/settings/address/countryAndPostalCode".format(
        api_host, device_id)
    headers = {"Authorization": "Bearer {}".format(access_token)}
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    addr_data = json.loads(res.read())

    return addr_data['postalCode'].replace('-', '')


def get_welcome_response():
    return create_all_response(create_response(
        "ようこそ、調布市のゴミの日スキルへ。知りたい調布市のゴミの日はいつですか？", "知りたい調布市のゴミの日はいつですか？", False))


def on_launch(launch_request):
    logger.info("on_launch got request{}".format(launch_request))
    return get_welcome_response()


def on_session_ended(sessionended_request):
    logger.info("on_session_ended got request{}".format(sessionended_request))
    return create_all_response(create_response("終わります。", None, True))


def is_allowed_location_api(context_system):
    if context_system.get('apiEndpoint') \
            and context_system['device'].get('deviceId') \
            and context_system['user'].get('permissions'):
        return True
    else:
        return False


def on_intent(context_system, intent_request):
    logger.info("on_launch got request{}".format(intent_request))

    if is_allowed_location_api(context_system):
        zip_code = fetch_zip_code(
            context_system['apiEndpoint'],
            context_system['device']['deviceId'],
            context_system['user']['permissions']['consentToken'])
        district_num = find_district_number(zip_code)
    else:
        # TODO: ロケーションAPIを有効するようにメッセージを返さなければならない
        #       現状はスキルに端末の国と郵便番号の権限を許可していない場合は第一地区としている
        district_num = 1

    # TODO: ユーザによる終了のケース、AMAZON.StopIntentまたはSessionEndedRequestの場合の処理を追加
    intent_name = intent_request['intent']['name']
    if intent_name == "GetChofuCityGabageIntent":
        logger.info("got When{}".format(intent_request[
                    'intent']['slots']['When']))
        when_value = intent_request['intent']['slots']['When']['value']
        try:
            when_resol_value = intent_request['intent']['slots']['When'][
                'resolutions']['resolutionsPerAuthority'][0][
                'values'][0]['value']
            when_resol_name = when_resol_value['name']
            when_resol_id = when_resol_value['id']
        except KeyError:
            return create_all_response(create_response(
                "いつのごみが知りたいかが分かりませんでした。\
                もう一度、いつのごみが知りたいかを教えてください。", None, False))

        target_date = find_target_date(when_resol_id, when_resol_name)
        garbage_type = fetch_garbage_type(district_num, target_date)

        return create_all_response(
            create_response("{}の第{}地区のごみ出しは{}です。".format(
                when_value, str(district_num), garbage_type), None, True))
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    else:
        raise ValueError("Invalid intent")


def lambda_handler(event, context):
    logger.info("handler got event{}".format(event))

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(
            event['context']['System'], event['request'])
    elif event['request']['type'] == "SessionEndedRequest":
        # 明示的にセッションを終了させてはいないが、セッションが終了してしまった場合、
        # スキルからはレスポンスを返さない
        return on_session_ended(event['request'])
