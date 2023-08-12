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
    response = USERS_TABLE.get_item(Key={'Username': username})
    if not response or not response.get('Items'):
        return None
    return response


def update_usr_session_to_db(username: str, session_data: dict):
    USERS_TABLE.update_item(
        Key={'Username': username},
        AttributeUpdates={
            'RememberSession': session_data,
        },
    )
