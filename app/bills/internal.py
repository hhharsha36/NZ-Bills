from botocore.exceptions import ClientError
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import logging

from config import BaseConfig


STS_CLIENT = BaseConfig.STS_CLIENT
EMAIL_CONTENT = BaseConfig.EMAIL_CONTENT
USERS_TABLE = BaseConfig.USERS_TABLE


SIZE_RANGE = range(1000, 2500, 100)
YEAR_RANGE = [*range(2002, datetime.now().year + 1)]


def get_pm_data():
    nz_pm_table = BaseConfig.NZ_PM_TABLE
    response = nz_pm_table.scan()
    if not isinstance(response, dict) or not response.get('Items'):
        # ValueError('unable to retrieve pm information from DB')
        return None
    for r in response['Items']:
        r['term'] = int(r['term'])
    return sorted(response['Items'], key=lambda x: x.get('term'), reverse=True)


def email_image(recipient, img_path):
    # https://stackoverflow.com/questions/60430283/how-to-add-image-to-email-body-python
    # https://stackoverflow.com/questions/48587432/add-embedded-image-in-emails-in-aws-ses-service
    dt = str(datetime.now().isoformat()).replace(' ', '')
    msg = MIMEMultipart('related')
    msg["From"] = EMAIL_CONTENT['From']
    msg["To"] = recipient.lower()
    msg["Subject"] = EMAIL_CONTENT['Subject'] + dt

    html_output = f'''
    <html>
    <head></head>
    <body>
    <h1>{EMAIL_CONTENT['H1']}</h1>
    <p>{EMAIL_CONTENT['Body']}</p>
    </body>
    </html>'''
    msg.attach(MIMEText(html_output, "html"))

    with open(img_path, "rb") as fp:
        img = MIMEImage(fp.read())
    img.add_header("Content-ID", f"<NZ-Bills-{dt}>")
    msg.attach(img)

    try:
        response = STS_CLIENT.send_raw_email(
            Source=EMAIL_CONTENT['From'],
            Destinations=[
                recipient.lower()
            ],
            RawMessage={
                'Data': msg.as_string(),
            }
        )
    except ClientError as e:
        logging.error(e)
        return False
    else:
        logging.info(f'successfully sent email to: {recipient}; message id: {response["MessageId"]}')
        return True


def get_usr_from_db(username: str):
    try:
        found_usr = USERS_TABLE.get_item(Key={'Username': username})
    except ClientError as e:
        logging.error(e)
        return None
    if not found_usr or not found_usr.get('Item'):
        return None
    return found_usr['Item']


def update_usr_session(username: str, session_details: dict):
    try:
        logging.debug(f'update_usr_session; {session_details=}')
        _ = USERS_TABLE.update_item(
            Key={'Username': username},
            UpdateExpression="set LastSession.pie_order=:pie_order, LastSession.include_other=:include_other, "
                             "LastSession.time_period_range=:time_period_range, LastSession.size_range=:size_range",
            ExpressionAttributeValues={
                ":pie_order": session_details.get('pie_order', ''),
                ":include_other": session_details.get('include_other', ''),
                ":time_period_range": session_details.get('time_period_range', ''),
                ":size_range": session_details.get('size_range', ''),
            },
            # AttributeUpdates={
            #     'LastSession.pie_order': session_details.get('pie_order', ''),
            #     'LastSession.include_other': session_details.get('include_other', ''),
            #     'LastSession.time_period_range': session_details.get('time_period_range', ''),
            #     'LastSession.size_range': session_details.get('size_range', ''),
            # },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        logging.error(e)
        # TODO: remove print statements from everywhere
        print('update_usr_session: None')
        return None
    print('update_usr_session: True')
    return True


def get_last_session(username):
    found_user = get_usr_from_db(username)
    logging.debug(f'get_last_session; {found_user=}')
    if not found_user or not isinstance(found_user.get('LastSession'), dict):
        logging.debug(f'get_last_session; "LastSession"')
        return None

    if found_user['LastSession'].get('pie_order') not in ['By Prime Minister', 'By Time']:
        logging.debug(f'get_last_session; "pie_order"')
        return None
    elif found_user['LastSession'].get('include_other') not in ['Yes', 'No']:
        logging.debug(f'get_last_session; "include_other"')
        return None
    elif found_user['LastSession'].get('size_range') not in SIZE_RANGE:
        logging.debug(f'get_last_session; "size_range"')
        return None
    elif not isinstance(found_user['LastSession'].get('time_period_range'), list) or not len(
            found_user['LastSession']['time_period_range']) == 2:
        logging.debug(f'get_last_session; "time_period_range"')
        return None

    for i, e in enumerate(found_user['LastSession']['time_period_range']):
        if int(e) not in YEAR_RANGE:
            logging.debug(f'get_last_session; "time_period_range"; {e}')
            return None
        found_user['LastSession']['time_period_range'][i] = int(e)

    found_user['LastSession']['size_range'] = int(found_user['LastSession']['size_range'])
    logging.debug(f'get_last_session; "SUCCESS"')
    return found_user['LastSession']
