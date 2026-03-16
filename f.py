import pickle
from google.oauth2.credentials import Credentials

with open('token.json', 'rb') as f:
    creds = pickle.load(f)

with open('token_new.json', 'w') as f:
    f.write(creds.to_json())