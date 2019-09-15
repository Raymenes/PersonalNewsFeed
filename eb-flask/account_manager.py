import json

import boto3
import botocore

from urllib.parse import urlencode
from urllib.request import Request, urlopen

######################## Constants ##############################

default_region = 'us-east-1'

base_url = '{}/{}?response_type=code&client_id={}&redirect_uri={}'
login_domain_name = 'https://my-personal-news-feed.auth.us-east-1.amazoncognito.com'
app_client_id = '2u4jrlgsf31gvhsh7mppj7evl8'
login_redirect_uri = 'https://www.ruizeng.info/UserLogin/login'

login_url = base_url.format(
    login_domain_name,
    'login',
    app_client_id,
    login_redirect_uri
)
signup_url = base_url.format(
    login_domain_name,
    'signup',
    app_client_id,
    login_redirect_uri
)
reset_password_url = base_url.format(
    login_domain_name,
    'forgotPassword',
    app_client_id,
    login_redirect_uri
)

cognito_id_provider = boto3.client('cognito-idp', default_region)

##################################################################

def get_user_info(code):
    print(code)
    print("rui debug 1")

    # Post request to oauth endpoint to exchange code for access token 
    # https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html
    # Set destination URL here
    url = 'https://my-personal-news-feed.auth.us-east-1.amazoncognito.com/oauth2/token'
    # Set POST fields here
    post_fields = {
            'grant_type': 'authorization_code',
            'client_id': '2u4jrlgsf31gvhsh7mppj7evl8',
            'code': code,
            'redirect_uri': login_redirect_uri
        }

    req = Request(url, urlencode(post_fields).encode())
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('Authorization', '')
    token_json = json.loads(urlopen(req).read().decode())

    id_token = token_json['id_token']
    access_token = token_json['access_token']
    refresh_token = token_json['access_token']

    # call CognitoIdentityProvider to get complete user info
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html
    user_info = cognito_id_provider.get_user(
        AccessToken=access_token
    )

    print(user_info)

    return user_info
