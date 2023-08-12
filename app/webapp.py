from datetime import datetime
import logging  # TODO: log to a file instead
from re import compile
from time import sleep
import os

from better_profanity import profanity
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError
from bson.objectid import ObjectId
from app.extensions import Crypt
import pandas as pd
from flask import url_for, flash, request, render_template, redirect, Blueprint, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from urllib.request import Request, urlopen
from urllib.error import URLError
from werkzeug.urls import url_parse

# from app.extensions import db
# from app.forms import LoginForm
# from app.forms import RegistrationForm
# from app.models import User

from app.bills.callbacks import DEFAULT_VALUES
from app.bills.internal import get_usr_from_db
from app.extensions import users_table
from config import BaseConfig


USERNAME_PATTERN = compile(r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+")


server_bp = Blueprint('main', __name__)
crypt = Crypt()


DOWNLOAD_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bills/parsedData.csv')


weak_passwords = []
weak_pwd_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "weak_passwords.txt")
with open(weak_pwd_path) as file:
    while line := file.readline():
        weak_passwords.append(line.rstrip())

breached_passwords = []
breached_pwd_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "breached_passwords.txt")
with open(breached_pwd_path) as file:
    while line := file.readline():
        breached_passwords.append(line.rstrip())

forbidden_usernames = []
forbidden_pwd_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "forbidden_usernames.txt")
with open(forbidden_pwd_path) as file:
    while line := file.readline():
        forbidden_usernames.append(line.rstrip())


# def get_user_from_db(username: str):
#     try:
#         found_usr = users_table.get_item(Key={"Username": username})
#         logging.debug(f'{found_usr=}')  # TODO: remove
#         if isinstance(found_usr, dict):
#             found_usr = found_usr.get('Item')
#     except ClientError as e:
#         logging.error(e)
#         found_usr = None
#     logging.debug(f'{found_usr=}')  # TODO: remove
#     return found_usr


class SignUp:
    def __init__(self, username: str, password: str):
        self._username = str(username).upper()
        self._password = str(password)
        self._user_col = users_table
        self._logged_in = False

    def sign_up_user(self) -> str | None:
        if msg := self.validate():
            return msg
        if msg := self.insert_to_db():
            return msg
        return None

    def validate(self) -> str | None:
        if not USERNAME_PATTERN.match(self._username):
            return "Username should be `alpha-numeric`, with optional `_` value"
        if profanity.contains_profanity(self._username):
            return "Username contains profanity words, but we know it was a typo..."
        if len(self._username) > 64:
            return "Username should not be more than 64 characters long"
        if len(self._password) < 8:
            return "We believe in your strong memory power, choose a password length greater than 8 characters"
        if len(self._password) > 64:
            return "Type a password, not an essay"
        if self._username.lower() == self._password.lower():
            return "Username and Password are same. I understand, it was an accident"
        if self._password.lower() in weak_passwords:
            return "You are a strong individual, but why is your password weak?"
        if self._password.lower() in breached_passwords:
            return "Your Password was breached by another app. Don't worry, your unused new password will " \
                   "only be between me :)"
        if self.has_repeating_char():
            return "Your password has repeating characters. If its your keyboard, I recommend you to buy " \
                   "KeyChron K2 Mechanical keyboard, which is reliable"
        if self.has_seq_chars():
            return "Your password contains four or more sequential characters, which makes it easier for " \
                   "elementary kids to guess"
        # if self.forbidden_username():
        #     return "The entered Username is a forbidden one, I see what you did there..."
        return None

    def insert_to_db(self):
        global crypt
        usr_oid = str(ObjectId())
        curr_time = datetime.now().isoformat()
        hashed_pwd = crypt.encrypt(salt=str(usr_oid), plain_txt_pwd=self._password)

        # if self._user_col.find_one({"Username": self._username}, {"_id": 1}):  # TODO: update query
        found_user = get_usr_from_db(self._username)
        if found_user:
            return "Username already exists! If you forgot your password, I am afraid the 'Forgot Password' feature " \
                   "can't be implemented with current budget"

        # self._user_col.insert_one({  # TODO: update query
        #     "_id": usr_oid,
        #     "Username": self._username,
        #     "Password": hashed_pwd,
        #     "CreatedAt": curr_time,
        #     "UpdatedAt": curr_time,
        # })
        resp = self._user_col.put_item(  # TODO: handle `resp` variable
            Item={
                "_id": usr_oid,
                "Username": self._username,
                "Password": hashed_pwd,
                "CreatedAt": curr_time,
                "UpdatedAt": curr_time,
                "LastSession": DEFAULT_VALUES,
            }
        )

        self._logged_in = True
        return None

    def has_repeating_char(self):
        repeat_count = 0
        max_repeat = 3
        for i in range(1, len(self._password)):
            if self._password[i] == self._password[i-1]:
                repeat_count += 1
                if repeat_count >= max_repeat:
                    return True
            else:
                repeat_count = 0
        return False

    def has_seq_chars(self):
        repeat_limit = 3
        seq_count = 0
        previous_char = self._password[0]
        # noinspection PyBroadException
        try:
            for i in self._password[1:]:
                i = i.lower()
                if ord(i) == ord(previous_char) + 1:
                    seq_count += 1
                    if seq_count >= repeat_limit:
                        return True
                else:
                    seq_count = 0
                previous_char = i
        except Exception:
            # TODO: log
            return False
        return False

    def forbidden_username(self):
        profanity.load_censor_words(forbidden_usernames)
        return profanity.contains_profanity(self._username)

    def is_authenticated(self):
        return self._logged_in

    def is_active(self):
        return self._logged_in

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return self._username


class SignIn:
    def __init__(self, username: str, password: str):
        self._username = username.upper()
        self._password = password
        self._user_col = users_table
        self.name = self._username
        self._logged_in = False  # TODO: remove

    def log_in(self):
        global crypt
        found_usr = get_usr_from_db(self._username)
        logging.debug(f'{found_usr=}')  # TODO: remove
        if not found_usr:
            return False
        # found_usr = self._user_col.find_one({"Username": self._username})  # TODO: update query
        # if not found_usr:
        #     sleep(0.5)
        #     return False
        if not crypt.verify(
                hash_val=found_usr.get('Password'),
                salt=str(found_usr['_id']),
                plain_txt_pwd=self._password):
            return False
        self._logged_in = True
        return True

    def is_authenticated(self):
        return self._logged_in

    def is_active(self):
        return self._logged_in

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return self._username


@server_bp.route('/')
def index():
    return render_template("index.html")


@server_bp.route('/login')
def login():
    return render_template('login.html')


@server_bp.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    # user = User.query.filter_by(email=username).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    sign_in_obj = SignIn(username=username, password=password)
    if not sign_in_obj.log_in():
        msg = "Username or Password is incorrect. Note: 'Forgot Password' feature will be made available by June 2030"
        logging.warning(msg)
        sleep(0.5)
        flash(msg)
        return redirect(url_for('main.login'))  # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(sign_in_obj, remember=remember)
    # return redirect(url_for('main.profile'))
    return redirect(url_for('/bills/'))


@server_bp.route('/logout')
@login_required
def logout():
    logout_user()
    logging.info(f"user successfully logged out")
    return redirect(url_for('main.index'))


@server_bp.route('/signup')
def signup():
    return render_template('signup.html')


@server_bp.route('/signup', methods=['POST'])
def signup_post():
    if BaseConfig.DISABLE_SIGNUP:
        logging.info(f'signup disabled in config level')
        flash("signup disabled")
        return redirect(url_for('main.signup'))
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm-password')
    logging.info(f"attempting to signup user: {username}")

    if password != confirm_password:
        msg = "'Password' and 'Confirm Password' are not same"
        logging.warning(msg)
        flash(msg)
        return redirect(url_for('main.signup'))

    sign_up_obj = SignUp(username=username, password=password)
    if err := sign_up_obj.sign_up_user():
        logging.warning(err)
        flash(err)
        return redirect(url_for('main.signup'))

    logging.info(f"successfully created user: {username.upper()}")
    return redirect(url_for('main.login'))


class UpdateData:
    def __init__(self):
        self._req_headers = {'User-Agent': 'Mozilla/5.0'}
        self.page_count: int = 0
        self.df: pd.DataFrame | None = None
        self.file_name = 'parsedData.csv'
        self.file_name = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bills/parsedData.csv')

    # def __call__(self, *args, **kwargs):
    #     self.update()

    def update(self):
        self.page_count = 0
        self.df = None
        for page_count in range(1, 55):
            req = self.get_data(page_count)
            webpage = urlopen(req).read()
            df_list = pd.read_html(webpage)[-1]

            if self.df is None:
                self.df = df_list
            else:
                self.df = pd.concat([self.df, df_list])
            print(f"\r{page_count}", end='')
        self.save_csv()
        err = self.upload_to_s3()
        return err

    def get_data(self, page_no, attempt=0):
        if attempt >= 10:
            return None
        try:
            return Request(
                f'https://www.parliament.nz/en/pb/bills-and-laws/bills-proposed-laws/all?Criteria.PageNumber={page_no}',
                headers=self._req_headers)
        except URLError:
            attempt += 1
            sleep(12)
            return self.get_data(page_no=page_no, attempt=attempt)

    def save_csv(self):
        # if os.path.exists(self.file_name):
        #     os.rename(src=self.file_name,
        #               dst=f"{self.file_name.replace('.csv', '')}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_.csv")
        self.df.to_csv(self.file_name)
        return None

    def upload_to_s3(self):
        try:
            os.path.abspath(os.path.dirname(__file__))
            BaseConfig.S3_CLIENT.upload_file(
                self.file_name, BaseConfig.BUCKET_NAME,
                f'ParseHistory/parsedData_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}_.csv')
        except (ClientError, S3UploadFailedError) as e:
            logging.error(e)
            return 'error uploading to s3'
        return None


@server_bp.route('/download', methods=['POST', 'GET', 'PUT'])
def download_data():
    req = request.get_json()
    if not req.get('key'):
        return jsonify({'error': True, 'status': '`key` missing in request'})
    elif req.get('key') != BaseConfig.DOWNLOAD_KEY:
        return jsonify({'error': True, 'status': 'wrong key'})
    update_data_obj = UpdateData()
    err = update_data_obj.update()
    if err:
        return jsonify({'error': True, 'status': err})
    # try:
    #     BaseConfig.S3_CLIENT.download_file(BaseConfig.BUCKET_NAME, BaseConfig.S3_PATH, DOWNLOAD_PATH)
    # except ClientError as e:
    #     logging.error(e)
    #     return jsonify({'error': True, 'status': 'error downloading file'})
    return jsonify({'error': False, 'status': 'success'})


@server_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)
