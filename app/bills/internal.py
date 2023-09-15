from botocore.exceptions import ClientError
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import logging
from smtplib import SMTP_SSL

from config import BaseConfig


# SES_CLIENT = BaseConfig.SES_CLIENT
EMAIL_CONTENT = BaseConfig.EMAIL_CONTENT
USERS_TABLE = BaseConfig.USERS_TABLE
M_USERS_COL = BaseConfig.M_USERS_COL
SMTP_CONFIG = BaseConfig.SMTP_CONFIG
DEBUG_MODE = BaseConfig.DEBUG_MODE


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


def email_image(recipient, img_bytes):
    # https://stackoverflow.com/questions/60430283/how-to-add-image-to-email-body-python
    # https://stackoverflow.com/questions/48587432/add-embedded-image-in-emails-in-aws-ses-service
    dt = str(datetime.now().strftime('%Y-%m-%d %I:%M %p'))
    msg = MIMEMultipart('related')
    msg["From"] = EMAIL_CONTENT['From']
    msg["To"] = recipient.get_id().lower()
    msg["Subject"] = EMAIL_CONTENT['Subject']

    html_output = f'''
    <html lang="en">
    <body>
    <p>{EMAIL_CONTENT['H1']}</p>
    <p>{EMAIL_CONTENT['Body']}</p>
    <br>
    <p>Regards,<br>NZ Bills Team<p>
    </body>
    </html>'''
    msg.attach(MIMEText(html_output, "html"))

    # with open(img_path, "rb") as fp:
    #     img = MIMEImage(fp.read())
    img = MIMEImage(img_bytes)
    img.add_header('Content-ID', f'<NZ-Bills-{dt}>')
    img.add_header('Content-Disposition', f'attachment; filename= NZBills-export-{dt}')
    msg.attach(img)
    logging.debug(f'created email MIME content')

    try:
        logging.debug(f'calling smtp')
        with SMTP_SSL(SMTP_CONFIG['Credentials']['Host'], SMTP_CONFIG['Credentials']['Port']) as conn:
            logging.debug(f'smtp1')
            conn.set_debuglevel(False)
            logging.debug(f'smtp2')
            conn.login(SMTP_CONFIG['Credentials']['Username'], SMTP_CONFIG['Credentials']['Password'])
            logging.debug(f'smtp3')
            conn.sendmail(EMAIL_CONTENT['From'], recipient.get_id().lower(), msg.as_string())
            logging.debug(f'smtp4')
        return True
    except Exception as e:
        logging.error(f"error sending email: {e}")
        return False

    # conn = SMTP_SSL(SMTP_CONFIG['Credentials']['Host'])
    # try:
    # finally:
    #     conn.quit()

    # try:
    #     response = SES_CLIENT.send_email(
    #         FromEmailAddress=EMAIL_CONTENT['From'],
    #         Destination={
    #             'ToAddresses': [
    #                 recipient.get_id().lower()
    #             ],
    #             'BccAddresses': [
    #                 EMAIL_CONTENT['From']
    #             ],
    #         },
    #         Content={
    #             'Raw': {
    #                 'Data': msg.as_string(),
    #             }
    #         },
    #     )
    # except ClientError as e:
    #     logging.error(e)
    #     return False
    # else:
    #     logging.info(f'successfully sent email to: {recipient}; message id: {response["MessageId"]}')
    #     return True


def get_usr_from_db(username: str):
    try:
        found_usr = USERS_TABLE.get_item(Key={'Username': username})
    except ClientError as e:
        logging.error(e)
        return None
    if not found_usr or not found_usr.get('Item'):
        return None
    return found_usr['Item']


# def update_usr_session(username: str, session_details: dict):
#     try:
#         logging.debug(f'update_usr_session; {session_details=}')
#         _ = USERS_TABLE.update_item(
#             Key={'Username': username},
#             UpdateExpression="set LastSession.pie_order=:pie_order, LastSession.include_other=:include_other, "
#                              "LastSession.time_period_range=:time_period_range, LastSession.size_range=:size_range",
#             ExpressionAttributeValues={
#                 ":pie_order": session_details.get('pie_order', ''),
#                 ":include_other": session_details.get('include_other', ''),
#                 ":time_period_range": session_details.get('time_period_range', ''),
#                 ":size_range": session_details.get('size_range', ''),
#             },
#             # AttributeUpdates={
#             #     'LastSession.pie_order': session_details.get('pie_order', ''),
#             #     'LastSession.include_other': session_details.get('include_other', ''),
#             #     'LastSession.time_period_range': session_details.get('time_period_range', ''),
#             #     'LastSession.size_range': session_details.get('size_range', ''),
#             # },
#             ReturnValues="UPDATED_NEW"
#         )
#     except ClientError as e:
#         logging.error(e)
#         print('update_usr_session: None')
#         return None
#     print('update_usr_session: True')
#     return True


def update_usr_session(username: str, session_details: dict):
    try:
        logging.debug(f'update_usr_session; {session_details=}')
        M_USERS_COL.update_one({
            'Username': username
        }, {
            '$set': {
                'LastSession': session_details,
                'UpdatedAt': datetime.now()
            },
            '$setOnInsert': {
                'CreatedAt': datetime.now()
            }
        }, upsert=True)
    except Exception as e:
        logging.error(e)
        logging.debug('update_usr_session: None')
        return None
    logging.debug('update_usr_session: True')
    return True


# def get_last_session(username):
#     found_user = get_usr_from_db(username)
#     logging.debug(f'get_last_session; {found_user=}')
#     if not found_user or not isinstance(found_user.get('LastSession'), dict):
#         logging.debug(f'get_last_session; "LastSession"')
#         return None
#
#     if found_user['LastSession'].get('pie_order') not in ['By Prime Minister', 'By Time']:
#         logging.debug(f'get_last_session; "pie_order"')
#         return None
#     elif found_user['LastSession'].get('include_other') not in ['Yes', 'No']:
#         logging.debug(f'get_last_session; "include_other"')
#         return None
#     elif found_user['LastSession'].get('size_range') not in SIZE_RANGE:
#         logging.debug(f'get_last_session; "size_range"')
#         return None
#     elif not isinstance(found_user['LastSession'].get('time_period_range'), list) or not len(
#             found_user['LastSession']['time_period_range']) == 2:
#         logging.debug(f'get_last_session; "time_period_range"')
#         return None
#
#     for i, e in enumerate(found_user['LastSession']['time_period_range']):
#         if int(e) not in YEAR_RANGE:
#             logging.debug(f'get_last_session; "time_period_range"; {e}')
#             return None
#         found_user['LastSession']['time_period_range'][i] = int(e)
#
#     found_user['LastSession']['size_range'] = int(found_user['LastSession']['size_range'])
#     logging.debug(f'get_last_session; "SUCCESS"')
#     return found_user['LastSession']


def get_last_session(username):
    found_user = M_USERS_COL.find_one({'Username': username})
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
