import boto3
import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# TODO: 関数の並び順を最適化する
# TODO: 関数の説明コメントを追加する


def create_all_response(response):
    return {
        'version': '1.0',
        'response': response
    }


def create_response(output_text, needs_card, reprompt_text,
                    should_end_session):
    output_speech = {
        'type': 'PlainText',
        'text': output_text
    }
    reprompt = {
        'outputSpeech': {
            'type': 'PlainText',
            'text': reprompt_text
        }
    }
    if not needs_card:
        return {
            'outputSpeech': output_speech,
            'reprompt': reprompt,
            'shouldEndSession': should_end_session
        }
    else:
        return create_response_containing_card(output_speech, reprompt,
                                               should_end_session)


def create_response_containing_card(output_speech, reprompt,
                                    should_end_session):
    return {
        'outputSpeech': output_speech,
        'cards': {
            'type': 'AskForPermissionsConsent',
            'permissions': [
                    'read::alexa:device:all:address:country_and_postal_code'
            ]
        },
        'reprompt': reprompt,
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
    zipcloud_url = os.environ['ZIPCLOUD_URL']
    params = {'zipcode': zip_code}
    req = urllib.request.Request(
        zipcloud_url + "?" + urllib.parse.urlencode(params))
    # TODO: HTTPErrorとURLErrorの場合を追加する。その際、should_end_sessionをFalseにして再度聞く
    try:
        with urllib.request.urlopen(req) as res:
            addr_data = json.loads(res.read())
            address2 = addr_data['results'][0]['address2']
            address3 = addr_data['results'][0]['address3']
    except (KeyError, TypeError):
        address2, address3 = None

    if address2 == "調布市":
        if address3 in {"仙川町", "入間町", "若葉町", "緑ケ丘", "国領町"}:
            district_num = 1
        elif address3 in \
                {"西つつじケ丘", "菊野台", "飛田給", "上石原", "東つつじケ丘", "富士見町", "野水", "西町"}:
            district_num = 2
        elif address3 in {"深大寺東町", "深大寺元町", "布田", "深大寺北町", "深大寺南町", "染地"}:
            district_num = 3
        elif address3 in {"調布ケ丘", "柴崎", "多摩川", "下石原", "八雲台", "佐須町", "小島町"}:
            district_num = 4
    elif address2 is None:
        """ zipcloudから住所が取得できない場合、district_numを5とする """
        district_num = 5
    else:
        """ 住所が調布市ではない場合、district_numを6とする """
        district_num = 6

    return district_num, address2, address3


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
        "ようこそ、調布市のゴミの日スキルへ。知りたい調布市のゴミの日はいつですか？今日、あした、曜日で訊いてください。",
        True, "知りたい調布市のゴミの日はいつですか？今日、あした、曜日で訊いてください。", False))


def get_helpintent_response():
    return create_all_response(create_response(
        "このスキルは調布市のごみの日を教えてくれるスキルです。例えば、明日のごみを教えて？と訊くと明日に捨てられるごみを教えてくれます。",
        True, None, False))


def on_launch(launch_request):
    logger.info("on_launch got request{}".format(launch_request))
    return get_welcome_response()


def on_session_ended(sessionended_request):
    logger.info("on_session_ended got request{}".format(sessionended_request))
    """ ユーザが明示的にではなく、セッションが終了した場合、スキルからはレスポンスを返せない """
    if sessionended_request['type'] != "SessionEndedRequest":
        return create_all_response(create_response("さようなら。",
                                                   False, None, True))


def is_allowed_location_api(context_system):
    if context_system.get('apiEndpoint') \
            and context_system['device'].get('deviceId') \
            and context_system['user'].get('permissions'):
        return True
    else:
        return False


def on_intent(context_system, intent_request):
    logger.info("on_intent got request{} context_system{}".format(
        intent_request, context_system))

    """ ユーザが、スキルに端末の国と郵便番号のアクセス権を許可しているか確認してから郵便番号を取得する """
    if is_allowed_location_api(context_system):
        zip_code = fetch_zip_code(
            context_system['apiEndpoint'],
            context_system['device']['deviceId'],
            context_system['user']['permissions']['consentToken'])
    else:
        return create_all_response(create_response(
            "スキルに端末の国と郵便番号のアクセス権を許可してください。", True, None, True))

    """ ユーザのAlexa端末の所在地が不明であったり、調布市内ではない場合、その旨を応答する """
    district_num, address2, address3 = find_district_number(zip_code)
    if district_num == 5:
        return create_all_response(create_response(
            "住所が分かりませんでした。恐れ入りますが、調布市で再度お使いください。", False, None, True))
    elif district_num == 6:
        return create_all_response(create_response(
            "{}{}は調布市ではないため、スキルは対応していません。調布市でお使いください。".format(
                address2, address3), False, None, True))

    intent_name = intent_request['intent']['name']
    if intent_name == "GetChofuCityGabageIntent":
        try:
            when_value = intent_request['intent']['slots']['When']['value']
            when_resol_value = intent_request['intent']['slots']['When'][
                'resolutions']['resolutionsPerAuthority'][0][
                'values'][0]['value']
            when_resol_name = when_resol_value['name']
            when_resol_id = when_resol_value['id']
        except KeyError:
            return create_all_response(create_response(
                "いつのごみが知りたいかが分かりませんでした。もう一度、いつのごみが知りたいかを今日、あした、曜日で訊いてください。",
                False, None, False))

        target_date = find_target_date(when_resol_id, when_resol_name)
        garbage_type = fetch_garbage_type(district_num, target_date)

        return create_all_response(
            create_response("{}の第{}地区のごみ出しは{}です。".format(
                when_value, str(district_num), garbage_type),
                False, None, True))
    elif intent_name == "AMAZON.HelpIntent":
        return get_helpintent_response()
    elif intent_name == "AMAZON.CancelIntent" \
                        or intent_name == "AMAZON.StopIntent":
        return on_session_ended(intent_request)
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
        return on_session_ended(event['request'])
