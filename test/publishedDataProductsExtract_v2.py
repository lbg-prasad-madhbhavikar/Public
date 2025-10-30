import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import requests
import coloredlogs
import logging
import creds
from pprint import pformat
import json
from tqdm import tqdm

coloredlogs.install(level="DEBUG")
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)

dgc_environment_url='https://lloyds.collibra.com/rest/2.0'
base_file_path = "/Users/7604844/Library/CloudStorage/OneDrive-LloydsBankingGroup/Documents/Collibra/Code/Python/OutputModule/X.RESULTS/"
view_config_path = "OutputModule/SCRIPTS/AI Agent Work/View Configs/"
config = "published_dps.json"

def cError(r):
    if not r.ok: 
        coloredlogs.install(level="ERROR")
        logging.error(f"Request Failed:\n{r.content.decode('utf-8')}")
        r.raise_for_status()

def login():
    # collibra login details
    username = creds.collibra_username
    password = creds.collibra_pw
    
    # windows/proxy login details
    proxy_user = creds.proxy_user
    proxy_password = creds.proxy_pw

    proxy_url = f'http://{proxy_user}:{proxy_password}@prodproxyarray.service.group:8080'
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }  

    session = requests.Session()
    session.proxies = proxies                         # if uploading to prod you need to uncomment this line
    session.headers.update({'accept': 'application/json, text/plain'}) # 'Content-Type':'application/json', 

    lvdata = {'username':username, 'password':password}
    r = session.post(f'{dgc_environment_url}/auth/sessions', json=lvdata)
    cError(r)

    return session

logging.debug("Logging in to Collibra")
session = login()
logging.debug("Login successful")

# ------------------------------------------------------------------------------------------------------ #
# specify view ID to extract from and obtain the view configuration
logging.info("Getting view configuration")
with open(view_config_path + config, "r", encoding="utf-8") as f:
    view_config = json.load(f)

# ------------------------------------------------------------------------------------------------------ #

r = session.post(f"{dgc_environment_url}/outputModule/export/json", json=view_config)
cError(r)

data = r.json()
asset_list = data['aaData']
logging.debug(f"Number of assets in view: {len(asset_list)}")
# logging.info(f"Assets:\n{pformat(asset_list)}")

with open(f"{base_file_path}dps_{config}", "w", encoding="utf-8") as f:
    json.dump(asset_list, f, ensure_ascii=False, indent=4)