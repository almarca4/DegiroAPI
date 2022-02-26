import requests, json
import pandas as pd
from io import StringIO
import datetime
import getpass
from degiroapi.order import Order
from degiroapi.client_info import ClientInfo
from degiroapi.datatypes import Data
from degiroapi.intervaltypes import Interval

session = requests.Session()


class DeGiro:
    __LOGIN_URL = 'https://trader.degiro.nl/login/secure/login'
    __LOGIN_TOTP_URL = 'https://trader.degiro.nl/login/secure/login/totp'
    __CONFIG_URL = 'https://trader.degiro.nl/login/secure/config'

    __LOGOUT_URL = 'https://trader.degiro.nl/trading/secure/logout'

    __CLIENT_INFO_URL = 'https://trader.degiro.nl/pa/secure/client'

    __GET_STOCKS_URL = 'https://trader.degiro.nl/products_s/secure/v5/stocks'
    __PRODUCT_SEARCH_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/lookup'
    __PRODUCT_INFO_URL = 'https://trader.degiro.nl/product_search/secure/v5/products/info'
    __TRANSACTIONS_URL = 'https://trader.degiro.nl/reporting/secure/v4/transactions'
    __TRANSACTIONS_CSV_URL = 'https://trader.degiro.nl/reporting/secure/v3/transactionReport/csv'
    __ORDERS_URL = 'https://trader.degiro.nl/reporting/secure/v4/order-history'
    __DIVIDENDS_URL = 'https://trader.degiro.nl/reporting/secure/v3/ca/'

    __ACCOUNT_URL = 'https://trader.degiro.nl/reporting/secure/v6/accountoverview'
    __ACCOUNT_CSV_URL = 'https://trader.degiro.nl/reporting/secure/v3/cashAccountReport/csv'
    __PLACE_ORDER_URL = 'https://trader.degiro.nl/trading/secure/v5/checkOrder'
    __ORDER_URL = 'https://trader.degiro.nl/trading/secure/v5/order/'

    __DATA_URL = 'https://trader.degiro.nl/trading/secure/v5/update/'
    __PRICE_DATA_URL = 'https://charting.vwdservices.com/hchart/v1/deGiro/data.js'

    __COMPANY_RATIOS_URL = 'https://trader.degiro.nl/dgtbxdsservice/company-ratios/'
    __COMPANY_PROFILE = 'https://trader.degiro.nl/dgtbxdsservice/company-profile/v2/'

    __GET_REQUEST = 0
    __POST_REQUEST = 1
    __DELETE_REQUEST = 2

    client_token = any
    session_id = any
    client_info = any
    confirmation_id = any

    def __init__(self, username=None, password=None, totp=None):
        if username:  # Login prompt
            self.login_prompt(username=username, password=password, totp=totp)

    def login(self, username, password, totp=None):
        login_payload = {
            'username': username,
            'password': password,
            'isPassCodeReset': False,
            'isRedirectToMobile': False
        }
        if totp is not None:
            login_payload["oneTimePassword"] = totp
            login_response = self.__request(DeGiro.__LOGIN_TOTP_URL, None, login_payload,
                                            request_type=DeGiro.__POST_REQUEST,
                                            error_message='Could not login.')
        else:
            try:
                login_response = self.__request(DeGiro.__LOGIN_URL, None, login_payload, request_type=DeGiro.__POST_REQUEST,
                                                error_message='Could not login.')
            except Exception:
                totp = getpass.getpass("totp (Leave empty if none):")
                login_payload["oneTimePassword"] = totp
                login_response = self.__request(DeGiro.__LOGIN_TOTP_URL, None, login_payload,
                                                request_type=DeGiro.__POST_REQUEST,
                                                error_message='Could not login.')

        self.session_id = login_response['sessionId']
        client_info_payload = {'sessionId': self.session_id}
        client_info_response = self.__request(DeGiro.__CLIENT_INFO_URL, None, client_info_payload,
                                              error_message='Could not get client info.')
        self.client_info = ClientInfo(client_info_response['data'])

        cookie = {
            'JSESSIONID': self.session_id
        }

        client_token_response = self.__request(DeGiro.__CONFIG_URL, cookie=cookie, request_type=DeGiro.__GET_REQUEST,
                                               error_message='Could not get client config.')
        self.client_token = client_token_response['data']['clientId']

        return client_info_response

    def login_prompt(self, username=None, password=None, totp=None):

        if not username: username = input("Username: ")
        if not password: password = getpass.getpass("Password:")
        if not totp:     totp = getpass.getpass("totp (Leave empty if none):")

        return self.login(username, password, totp or None)

    def logout(self):
        logout_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
        }
        self.__request(DeGiro.__LOGOUT_URL + ';jsessionid=' + self.session_id, None, logout_payload,
                       error_message='Could not log out')

    @staticmethod
    def __request(url, cookie=None, payload=None, headers=None, data=None, post_params=None, request_type=__GET_REQUEST,
                  csv=False, error_message='An error occurred.'):

        if request_type == DeGiro.__DELETE_REQUEST:
            response = session.delete(url, json=payload)
        elif request_type == DeGiro.__GET_REQUEST and cookie:
            response = session.get(url, cookies=cookie)
        elif request_type == DeGiro.__GET_REQUEST:
            response = session.get(url, params=payload)
        elif request_type == DeGiro.__POST_REQUEST and headers and data:
            response = session.post(url, headers=headers, params=payload, data=data)
        elif request_type == DeGiro.__POST_REQUEST and post_params:
            response = session.post(url, params=post_params, json=payload)
        elif request_type == DeGiro.__POST_REQUEST:
            response = session.post(url, json=payload)
        else:
            raise Exception(f'Unknown request type: {request_type}')

        if response.status_code == 200 or response.status_code == 201:
            if csv == True:
                try:
                    df = pd.read_csv(StringIO(response.text))
                    return df
                except:
                    return "No data"
            try:
                return response.json()
            except ValueError:
                df = pd.read_csv(StringIO(response.text))
                return df
            except:
                return "No data"
        else:
            raise Exception(f'{error_message} Response: {response.text}')

    def search_products(self, search_text, limit=1):
        product_search_payload = {
            'searchText': search_text,
            'limit': limit,
            'offset': 0,
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__PRODUCT_SEARCH_URL, None, product_search_payload,
                              error_message='Could not get products.')['products']

    def product_info(self, product_id):
        product_info_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__PRODUCT_INFO_URL, None, product_info_payload,
                              headers={'content-type': 'application/json'},
                              data=json.dumps([str(product_id)]),
                              request_type=DeGiro.__POST_REQUEST,
                              error_message='Could not get product info.')['data'][str(product_id)]

    def transactions(self, from_date, to_date, group_transactions=False):
        transactions_payload = {
            'fromDate': self.validate(from_date),
            'toDate': self.validate(to_date),
            'group_transactions_by_order': group_transactions,
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__TRANSACTIONS_URL, None, transactions_payload,
                              error_message='Could not get transactions.')['data']

    def account_overview(self, from_date, to_date):
        account_payload = {
            'fromDate': self.validate(from_date),
            'toDate': self.validate(to_date),
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__ACCOUNT_URL, None, account_payload,
                              error_message='Could not get account overview.')['data']

    def orders(self, from_date, to_date, not_executed=None):
        orders_payload = {
            'fromDate': from_date.strftime('%d/%m/%Y'),
            'toDate': to_date.strftime('%d/%m/%Y'),
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        # max 90 days
        if (to_date - from_date).days > 90:
            raise Exception('The maximum timespan is 90 days')
        data = self.__request(DeGiro.__ORDERS_URL, None, orders_payload, error_message='Could not get orders.')['data']
        data_not_executed = []
        if not_executed:
            for d in data:
                if d['isActive']:
                    data_not_executed.append(d)
            return data_not_executed
        else:
            return data

    def delete_order(self, orderId):
        delete_order_params = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
        }

        return self.__request(DeGiro.__ORDER_URL + orderId + ';jsessionid=' + self.session_id, None,
                              delete_order_params,
                              request_type=DeGiro.__DELETE_REQUEST,
                              error_message='Could not delete order' + " " + orderId)

    @staticmethod
    def filtercashfunds(cashfunds):
        data = []
        for item in cashfunds['cashFunds']['value']:
            if item['value'][2]['value'] != 0:
                data.append(item['value'][1]['value'] + " " + str(item['value'][2]['value']))
        return data

    @staticmethod
    def filterportfolio(portfolio, filter_zero=None):
        data = []
        data_non_zero = []
        for item in portfolio['portfolio']['value']:
            positionType = size = price = value = breakEvenPrice = None
            for i in item['value']:
                size = i['value'] if i['name'] == 'size' else size
                positionType = i['value'] if i['name'] == 'positionType' else positionType
                price = i['value'] if i['name'] == 'price' else price
                value = i['value'] if i['name'] == 'value' else value
                breakEvenPrice = i['value'] if i['name'] == 'breakEvenPrice' else breakEvenPrice
            data.append({
                "id": item['id'],
                "positionType": positionType,
                "size": size,
                "price": price,
                "value": value,
                "breakEvenPrice": breakEvenPrice
            })
        if filter_zero:
            for d in data:
                if d['size'] != 0.0:
                    data_non_zero.append(d)
            return data_non_zero
        else:
            return data

    def getdata(self, datatype, filter_zero=None):
        data_payload = {
            datatype: 0
        }

        if datatype == Data.Type.CASHFUNDS:
            return self.filtercashfunds(
                self.__request(DeGiro.__DATA_URL + str(self.client_info.account_id) + ';jsessionid=' + self.session_id,
                               None,
                               data_payload,
                               error_message='Could not get data'))
        elif datatype == Data.Type.PORTFOLIO:
            return self.filterportfolio(
                self.__request(DeGiro.__DATA_URL + str(self.client_info.account_id) + ';jsessionid=' + self.session_id,
                               None,
                               data_payload,
                               error_message='Could not get data'), filter_zero)
        else:
            return self.__request(
                DeGiro.__DATA_URL + str(self.client_info.account_id) + ';jsessionid=' + self.session_id, None,
                data_payload,
                error_message='Could not get data')

    def real_time_price(self, product_id, interval):
        vw_id = self.product_info(product_id)['vwdId']
        tmp = vw_id
        try:
            int(tmp)
        except:
            vw_id = self.product_info(product_id)['vwdIdSecondary']

        price_payload = {
            'requestid': 1,
            'period': interval,
            'series': ['issueid:' + vw_id, 'price:issueid:' + vw_id],
            'userToken': self.client_token
        }

        return self.__request(DeGiro.__PRICE_DATA_URL, None, price_payload,
                             error_message='Could not get real time price')['series']

    def buyorder(self, orderType, productId, timeType, size, limit=None, stop_loss=None):
        place_buy_order_params = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
        }
        place_buy_order_payload = {
            'buySell': "BUY",
            'orderType': orderType,
            'productId': productId,
            'timeType': timeType,
            'size': size,
            'price': limit,
            'stopPrice': stop_loss,
        }
        if orderType != Order.Type.STOPLIMIT and orderType != Order.Type.MARKET \
                and orderType != Order.Type.LIMIT and orderType != Order.Type.STOPLOSS:
            raise Exception('Invalid order type')

        if timeType != 1 and timeType != 3:
            raise Exception('Invalid time type')

        place_check_order_response = self.__request(DeGiro.__PLACE_ORDER_URL + ';jsessionid=' + self.session_id, None,
                                                    place_buy_order_payload, place_buy_order_params,
                                                    request_type=DeGiro.__POST_REQUEST,
                                                    error_message='Could not place order')

        self.confirmation_id = place_check_order_response['data']['confirmationId']

        self.__request(DeGiro.__ORDER_URL + self.confirmation_id + ';jsessionid=' + self.session_id, None,
                       place_buy_order_payload, place_buy_order_params,
                       request_type=DeGiro.__POST_REQUEST,
                       error_message='Could not confirm order')

    def sellorder(self, orderType, productId, timeType, size, limit=None, stop_loss=None):
        place_sell_order_params = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
        }
        place_sell_order_payload = {
            'buySell': "SELL",
            'orderType': orderType,
            'productId': productId,
            'timeType': timeType,
            'size': size,
            'price': limit,
            'stopPrice': stop_loss,
        }
        if orderType != Order.Type.STOPLIMIT and orderType != Order.Type.MARKET \
                and orderType != Order.Type.LIMIT and orderType != Order.Type.STOPLOSS:
            raise Exception('Invalid order type')

        if timeType != 1 and timeType != 3:
            raise Exception('Invalid time type')

        place_check_order_response = self.__request(DeGiro.__PLACE_ORDER_URL + ';jsessionid=' + self.session_id, None,
                                                    place_sell_order_payload, place_sell_order_params,
                                                    request_type=DeGiro.__POST_REQUEST,
                                                    error_message='Could not place order')

        self.confirmation_id = place_check_order_response['data']['confirmationId']

        self.__request(DeGiro.__ORDER_URL + self.confirmation_id + ';jsessionid=' + self.session_id, None,
                       place_sell_order_payload, place_sell_order_params,
                       request_type=DeGiro.__POST_REQUEST,
                       error_message='Could not confirm order')

    def get_stock_list(self, indexId, stockCountryId):
        stock_list_params = {
            'indexId': indexId,
            'stockCountryId': stockCountryId,
            'offset': 0,
            'limit': None,
            'requireTotal': "true",
            'sortColumns': "name",
            'sortTypes': "asc",
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return \
            self.__request(DeGiro.__GET_STOCKS_URL, None, stock_list_params, error_message='Could not get stock list')[
                'products']

    def transactions_csv(self, from_date, to_date):
        transactions_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
            'country': 'ES',
            'lang': 'es',
            'fromDate': self.validate(from_date),
            'toDate': self.validate(to_date)
        }
        df = self.__request(DeGiro.__TRANSACTIONS_CSV_URL, None, transactions_payload, csv=True,
                              error_message='Could not get transactions.')
        df.insert(loc=0, column='Date', value=pd.to_datetime(df.pop('Fecha') + df.pop('Hora'), format='%d-%m-%Y%H:%M'))
        return df

    def account_overview_csv(self, from_date, to_date):
        transactions_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id,
            'country': 'ES',
            'lang': 'es',
            'fromDate': self.validate(from_date),
            'toDate': self.validate(to_date)
        }
        df = self.__request(DeGiro.__ACCOUNT_CSV_URL, None, transactions_payload, csv=True,
                              error_message='Could not get account overview.')
        df.insert(loc=0, column='Date', value=pd.to_datetime(df.pop('Fecha') + df.pop('Hora'), format='%d-%m-%Y%H:%M'))
        return df

    def validate(self, strordate):
        if isinstance(strordate, datetime.datetime):
            strordate = strordate.strftime('%d/%m/%Y')
        else:
            try:
                strordate = datetime.datetime.strptime(strordate, '%d/%m/%Y').strftime('%d/%m/%Y')
            except ValueError:
                raise ValueError("Incorrect data format, should be DD-MM-YYYY")
        return strordate

    def future_dividends(self):
        dividends_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__DIVIDENDS_URL + str(self.client_info.account_id), None, dividends_payload,
                              error_message='Could not get future dividends.')['data']

    def products_info(self, product_ids):
        product_info_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__PRODUCT_INFO_URL, None, product_info_payload,
                              headers={'content-type': 'application/json'},
                              data=json.dumps([str(p) for p in product_ids]),
                              request_type=DeGiro.__POST_REQUEST,
                              error_message='Could not get product info.')['data']

    def company_ratios(self, product_isin):
        if isinstance(product_isin, int):
            product_isin = str(product_isin)
        product_info_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__COMPANY_RATIOS_URL + product_isin,
                              None, product_info_payload,
                              headers={'content-type': 'application/json'},
                              data=None,
                              request_type=DeGiro.__GET_REQUEST,
                              error_message='Could not get company ratios.')['data']

    def company_profile(self, product_isin):
        product_info_payload = {
            'intAccount': self.client_info.account_id,
            'sessionId': self.session_id
        }
        return self.__request(DeGiro.__COMPANY_PROFILE + product_isin,
                              None, product_info_payload,
                              headers={'content-type': 'application/json'},
                              error_message='Could not get company profile.')['data']