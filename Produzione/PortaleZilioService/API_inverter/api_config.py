import os

# API Configuration - iSolarCloud Gateway
# All API settings, credentials, and endpoints in one place

# ============================================
# API Credentials
# ============================================
API_KEY = os.getenv('ISC_API_KEY', 'dpiixeb8cnn34widwp7ihg5nzfb8eybw')
APPKEY = os.getenv('ISC_APPKEY', 'AAA324AF620903ED6ECCDDEA0B6BC866')
USER_ACCOUNT = os.getenv('ISC_USER_ACCOUNT', 'tecnico@zilioservice.com')
USER_PASSWORD = os.getenv('ISC_USER_PASSWORD', 'monitorinG_eesco22')

# ============================================
# Base URL
# ============================================
BASE_URL = os.getenv('ISC_BASE_URL', 'https://gateway.isolarcloud.eu/openapi')

# ============================================
# API Endpoints
# ============================================
ENDPOINTS = {
    'login': f'{BASE_URL}/login',
    'plant_list': f'{BASE_URL}/getPowerStationList',
    'device_list': f'{BASE_URL}/getDeviceList',
    'plant_detail': f'{BASE_URL}/getPowerStationDetail',
    'plant_data': f'{BASE_URL}/getDevicePointMinuteDataList',
    'inv_status': f'{BASE_URL}/getPVInverterRealTimeData',
    'plant_data_daily': f'{BASE_URL}/getDevicePointsDayMonthYearDataList',
    'batch_ps_detail': f'{BASE_URL}/getBatchPsDetail',
}

# ============================================
# Default Headers
# ============================================
DEFAULT_HEADERS = {
    'accept': 'application/json',
    'x-access-key': API_KEY,
    'sys_code': '901',
    'Content-Type': 'application/json',
}

# ============================================
# Request Settings
# ============================================
REQUEST_DELAY = float(os.getenv('ISC_REQUEST_DELAY', '0.1'))
REQUEST_TIMEOUT = int(os.getenv('ISC_REQUEST_TIMEOUT', '30'))
DATA_POINTS = 'p24'
PAGE_SIZE = int(os.getenv('ISC_PAGE_SIZE', '20'))
DEVICE_PAGE_SIZE = int(os.getenv('ISC_DEVICE_PAGE_SIZE', '32'))

# ============================================
# Login Parameters
# ============================================
LOGIN_PARAMS = {
    'appkey': APPKEY,
    'user_account': USER_ACCOUNT,
    'user_password': USER_PASSWORD,
    'lang': '_it_IT',
}
