from abc import ABC, abstractmethod
from typing import Literal
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import time
import requests
import gspread
from gspread.utils import ValueRenderOption
import hmac
import hashlib
from urllib.parse import urlparse
import json
import warnings
import random


# getshopeepackagelist_fromorderdetaillist function:
def getshopeepackagelist_fromorderdetaillist(orderdetail_list):
    """
    Purpose: retrieve list of package numbers from list of orders details
    :param orderdetail_list: a list of dictionaries, each dictionary contains order details of each Shopee order
    :return: a list of string, each string is a package number
    """
    list_package = []
    for i in orderdetail_list:
        list_package.append(i['package_list'][0]['package_number'])
    return list_package


# gettiktokidlist_fromorderlist function:
def gettiktokidlist_fromorderlist(order_list):
    """
    :param order_list: a list of dictionaries, each dictionary contains information of an Tiktok order
    :return: a list of string, each string is a Tiktok order ID
    """
    idlist = []
    for i in order_list:
        idlist.append(i['id'])
    return idlist


# handle_ratelimit_api function:
def handle_ratelimit_api(old_response: dict, method: str, argument: dict[str, any], base_waittime: int, max_retry: int):
    """
    :param old_response: the response.json() from the main request that statuscode != 200
    :param method: method of the retry request
    :param argument: the argument to pass the retry request. Example: {'url': url, 'headers': headers, 'params': params, 'json':body}
    :param base_waittime: the wait time before the first time re-send the retry request
    :param max_retry: the maximum number to re-send retry requests. After this time, if response.statuscode is still not 200, raise error
    :return: response object from the server
    """
    if old_response.get('code') == 36009002 and ('tiktok' in argument.get('url', '').lower()):
        wait = base_waittime + random.uniform(1, 4)
        retry_count = 1
        while retry_count <= max_retry:
            time.sleep(wait)
            response = requests.request(method=method, **argument)
            if response.status_code == 200:
                return response
            else:
                retry_count = retry_count + 1
                wait = min(retry_count*base_waittime + random.uniform(1, 4), 300)
        raise RuntimeError(f"The {argument['url']} endpoint still returns an error after {max_retry} times retry: \n{response.json()}")
    else:
        raise RuntimeError(f"The {argument['url']} endpoint returns an error: \n{old_response}")


# generate_sign function, directly from Tiktok Shop partner center API https://partner.tiktokshop.com/docv2/page/sign-your-api-request
def generate_sign(request_option, app_secret):
    """
    Generate HMAC-SHA256 signature
    :param request_option: Request options dictionary containing qs (query params), uri (path), headers, body etc.
    :param app_secret: Secret key for signing
    :return: Hexadecimal signature string
    """
    # Step 1: Extract and filter query parameters, exclude "access_token" and "sign", sort alphabetically
    params = request_option.get('qs', {})
    exclude_keys = ["access_token", "sign"]
    sorted_params = [
        {"key": key, "value": params[key]}
        for key in sorted(params.keys())
        if key not in exclude_keys
    ]
    # Step 2: Concatenate parameters in {key}{value} format
    param_string = ''.join([f"{item['key']}{item['value']}" for item in sorted_params])
    sign_string = param_string
    # Step 3: Append API request path to the signature string
    uri = request_option.get('uri', '')
    pathname = urlparse(uri).path if uri else ''
    sign_string = f"{pathname}{param_string}"
    # Step 4: If not multipart/form-data and request body exists, append JSON-serialized body
    content_type = request_option.get('headers', {}).get('content-type', '')
    body = request_option.get('body', {})
    if content_type != 'multipart/form-data' and body:
        body_str = json.dumps(body)  # JSON serialization ensures consistency
        sign_string += body_str
        # Step 5: Wrap signature string with app_secret
    wrapped_string = f"{app_secret}{sign_string}{app_secret}"
    # Step 6: Encode using HMAC-SHA256 and generate hexadecimal signature
    hmac_obj = hmac.new(
        app_secret.encode('utf-8'),
        wrapped_string.encode('utf-8'),
        hashlib.sha256
    )
    sign = hmac_obj.hexdigest()
    return sign


# Extractor interface:
class Extractor(ABC):
    @abstractmethod
    def extractdata(self):
        pass


# ExcelExtractor class:
class ExcelExtractor(Extractor):
    """
    Purpose: convert an excel file into an dataframe
    """
    def __init__(self,
                 provider_name: str,
                 file_path: str,
                 usecolumnname: list[str],
                 usedtype: dict[str,str],
                 skip_rows: int,
                 check_filepath: list[str]):
        if file_path is not None:
            for i in check_filepath:
                if file_path.casefold().find(i.casefold()) == -1:
                    raise NameError(f"The {file_path} must contain all values in the list {check_filepath}")
        self.provider_name = provider_name
        self.file_path = file_path
        self.usecolumnname = usecolumnname
        self.usedtype = usedtype
        self.skip_rows = skip_rows
        self.check_filepath = check_filepath
    def extractdata(self) -> pd.DataFrame:
        df = pd.read_excel(io = self.file_path,
                           usecols = self.usecolumnname,
                           dtype = self.usedtype,
                           skiprows = self.skip_rows)
        return df


# DeliveryOrdersExcelExtractor class:
class DeliveryOrdersExcelExtractor(ExcelExtractor):
    """
    Purpose: convert a delivery orders data excel file into a dataframe
    """
    def __init__(self,
                 provider_name: str,
                 file_path: str,
                 usecolumnname: list[str],
                 usedtype: dict[str,str],
                 skip_rows: int,
                 delivery_account: str,
                 check_filepath: list[str]):
        if file_path is not None:
            for i in check_filepath:
                if file_path.casefold().find(i.casefold()) == -1:
                    raise NameError(f"The {file_path} must contain all values in the list {check_filepath}")
        super().__init__(provider_name, file_path, usecolumnname, usedtype, skip_rows, check_filepath)
        self.delivery_account = delivery_account
    def extractdata(self) -> pd.DataFrame:
        df = super().extractdata()
        df['ĐVVC'] = self.provider_name
        df['Tài khoản ĐVVC'] = self.delivery_account
        return df


# NhanhvnOrdersAPIExtractor class:
class NhanhvnOrdersAPIExtractor(Extractor):
    """
    Purpose: Retrieve Nhanh.vn orders data from Nhanh.vn open API
    """
    def __init__(self,
                 url: str,
                 params: dict[str,str],
                 headers: dict[str,str],
                 startdate: str,
                 enddate: str,
                 *,
                 orderstatus: list[int] = None,
                 salechannel: list[int] = None):
        """
        :param url: the url of the endpoint to send requests to. Should be: 'https://pos.open.nhanh.vn/v3.0/order/list'
        :param params: a dictionary contains 2 information: 'appId' and 'businessId'. Example: {'appId':123456, 'businessId':20266789}
        :param headers: a dictionary contains 2 information: 'Authorization' and 'Content-Type'. Example: {'Authorization':'a24T86Huy97Gy90Wxbhu9', 'Content-Type':'application/json'}
        :param startdate: the created order date to start retrieving data, the time part must be '00:00:00'. Example: '2026-04-12 00:00:00'
        :param enddate: the created at order date to stop retrieving data, the time part must be '23:59:59'. Example: '2026-05-20 23:59:59'
        :param orderstatus: a list of integers. Each integer is a status id. In default, retrieve all statuses
        :param salechannel: a list of integers. Each integer is a sale channel id. In default, retrieve all sale channels
        """
        self.url = url
        self.params = params
        self.headers = headers
        self.startdate = startdate
        self.enddate = enddate
        self.orderstatus = orderstatus
        self.salechannel = salechannel
    def extractdata(self) -> list[dict]:
        self.startdate = datetime.strptime(self.startdate, "%Y-%m-%d %H:%M:%S")
        self.startdate = self.startdate.replace(tzinfo=timezone(timedelta(hours=7)))
        self.startdate = int(self.startdate.timestamp())
        self.enddate = datetime.strptime(self.enddate, "%Y-%m-%d %H:%M:%S")
        self.enddate = self.enddate.replace(tzinfo=timezone(timedelta(hours=7)))
        self.enddate = int(self.enddate.timestamp())
        if self.startdate > self.enddate:
            raise ValueError("The enddate must greater than startdate")
        currentdate = datetime.now(timezone(timedelta(hours=7)))
        currentdate = currentdate.replace(hour=0, minute=0, second=0, microsecond=0)
        currentdate = int(currentdate.timestamp())
        if self.enddate > currentdate:
            raise ValueError("The enddate must less than today")
        orderlist_2 = []
        count = 0
        for date in range(self.startdate, self.enddate, 30*24*60*60):
            if date + 30*24*60*60-1 < self.enddate:
                edate = date + 30*24*60*60-1
            else:
                edate = self.enddate
            pagi = {'size':100}
            orderlist_1 = []
            while True:
                count = count+1
                if count%10 == 0:
                    time.sleep(2)
                print(f'Performing fetch data from Nhanh.vn API, sending request times: {count}')
                filters = {
                    "filters": {"createdAtFrom": date, "createdAtTo": edate, "statuses": self.orderstatus,
                                "saleChannels": self.salechannel},
                    "paginator": pagi,
                    "dataOptions": {}
                }
                response = requests.post(url=self.url, params=self.params, headers=self.headers, json=filters)
                if response.status_code != 200:
                    raise RuntimeError(f"The Nhanhvn orders API call return an error: \n{response.json()}")
                ordersdata = response.json()
                if ordersdata['data']!='':
                    orderlist_1.extend(ordersdata['data'])
                try:
                    next_id = ordersdata['paginator']['next']['id']
                    pagi = {'size': 100, 'next': {'id': next_id}}
                except:
                    break
            orderlist_2.extend(orderlist_1)
        return orderlist_2


# GoogleSheetExtractor class:
class GoogleSheetExtractor:
    """
    Purpose: read data from a google sheet file
    """
    def __init__(self,
                 servicekey_path):
        self._client = gspread.service_account(filename=servicekey_path)
        self._idfile = None
        self._idsheet = None
        self._workbook = None
        self._worksheet = None
    def extractfile(self, idfile: str):
        if idfile != self._idfile:
            self._idfile = idfile
            self._workbook = self._client.open_by_key(self._idfile)
        return self._workbook
    def extractsheet(self,
                     idfile: str,
                     idsheet: int):
        if idsheet != self._idsheet or idfile != self._idfile:
            self._idsheet = idsheet
            workbook = self.extractfile(idfile)
            self._worksheet = workbook.get_worksheet_by_id(self._idsheet)
        return self._worksheet
    def extractlist(self,
                    idfile: str,
                    idsheet: int,
                    datarange: str,
                    *,
                    valuerender = ValueRenderOption.formatted) -> list:
        sheet = self.extractsheet(idfile, idsheet)
        return sheet.get_values(range_name=datarange, value_render_option=valuerender) # return a list that contains lists of values
    def extractdataframe(self,
                         idfile: str,
                         idsheet: int,
                         datarange: str,
                         columns: list[str],
                         *,
                         valuerender = ValueRenderOption.formatted) -> pd.DataFrame:
        datalist = self.extractlist(idfile, idsheet, datarange, valuerender=valuerender) # datalist is a list that contains lists of values
        return pd.DataFrame(data=datalist, columns=columns)


# ShopeeAPIAuthentication class:
class ShopeeAPIAuthentication(Extractor):
    """
    Purpose: return a dictionary containing authentication information (access_token, refresh_token, expire_in,...) using Shopee Open API
    """
    def __init__(self,
                 endpoint: str,
                 partnerid: int,
                 partnerkey: str,
                 shopid: int,
                 token: str,
                 headers: dict[str, str]):
        """
        :param endpoint: only accept 2 endpoints: '/api/v2/auth/token/get' or '/api/v2/auth/access_token/get'
        :param partnerid: partner ID of an app
        :param partnerkey: partner key of an app
        :param shopid: Shopee shop's id
        :param token: access_code (in case you want to retrieve access_token) or refresh_token (in case you want to retrieve new access_token)
        :param headers: header of the request sending to the server
        """
        if endpoint != '/api/v2/auth/token/get' and endpoint != '/api/v2/auth/access_token/get':
            raise ValueError(f"Only accept 2 endpoints '/api/v2/auth/token/get' or '/api/v2/auth/access_token/get'. But you parsed the endpoint {endpoint}")
        self.endpoint = endpoint
        self.partnerid = partnerid
        self.partnerkey = partnerkey
        self.shopid = shopid
        self.token = token
        self.headers = headers
    def extractdata(self):
        # Create sign paramater:
        timest = int(time.time())
        basestring =str(self.partnerid) + self.endpoint + str(timest)
        basestring = basestring.encode()
        partnerkey_byte = self.partnerkey.encode()
        sign = hmac.new(partnerkey_byte, basestring, hashlib.sha256).hexdigest()
        # Create url, params, json parameters:
        link = 'https://partner.shopeemobile.com' + self.endpoint
        extension = {'partner_id':self.partnerid, 'timestamp':timest, 'sign':sign}
        if self.endpoint == '/api/v2/auth/token/get':
            body = {'code': self.token, 'shop_id': self.shopid, 'partner_id': self.partnerid}
        else:
            body = {'refresh_token': self.token, 'shop_id': self.shopid, 'partner_id': self.partnerid}
        # Send a request to the Shopee server:
        response = requests.post(url=link, headers=self.headers, params=extension, json=body)
        return response.json()


# ShopeeAPIBaseExtractor class:
class ShopeeAPIBaseExtractor(Extractor):
    """
    Purpose: calculate url and params parameters (for requests you want to send to the Shopee API server)
    """
    def __init__(self,
                 endpoint: str,
                 partnerid: int,
                 partnerkey: str,
                 shopid: int,
                 token: str,
                 *,
                 params_extension: dict[str, str] = None):
        """
        :param endpoint: the endpoint to send the request
        :param partnerid: partner ID of an app
        :param partnerkey: partner key of an app
        :param shopid: Shopee shop's id
        :param token: access_token of an app
        :param params_extension: some parameters add to the base params of the request. Base params is a dictionary with 5 keys are: access_token, shop_id, partner_id, sign, timestamp. Only add this parameter when common parameters (in Shopee API docs) have more than 5 base params
        """
        self.endpoint = endpoint
        self.partnerid = partnerid
        self.partnerkey = partnerkey
        self.shopid = shopid
        self.token = token
        self.params_extension = params_extension
    def extractdata(self):
        # Create sign parameter:
        timest = int(time.time())
        basestring =str(self.partnerid) + self.endpoint + str(timest) + self.token + str(self.shopid)
        basestring =basestring.encode()
        partnerkey_byte = self.partnerkey.encode()
        sign = hmac.new(partnerkey_byte, basestring, hashlib.sha256).hexdigest()
        # Create url parameter:
        link = 'https://partner.shopeemobile.com' + self.endpoint
        # Create params parameters:
        baseparams = {'access_token':self.token, 'shop_id':self.shopid, 'partner_id':self.partnerid, 'sign':sign, 'timestamp':timest}
        if self.params_extension is None:
            extension = baseparams
        else:
            extension = baseparams | self.params_extension
        return link, extension


# ShopeeGetRecordsByTimeintervalAPIExtractor class:
class ShopeeGetRecordsByTimeintervalAPIExtractor(ShopeeAPIBaseExtractor):
    """
    Purpose: retrieve a list of records in a specific time
    """
    def __init__(self,
                 endpoint: str,
                 method: Literal['GET', 'POST'],
                 partnerid: int,
                 partnerkey: str,
                 shopid: int,
                 token: str,
                 headers: dict[str, str],
                 starttime: dict[str, str],
                 endtime: dict[str, str],
                 accepttypetime: Literal['int', 'str'],
                 chunk_date: int,
                 pagesize: int,
                 pieceinfo_position: list[str],
                 cursor_position: list[str],
                 *,
                 params_extension: dict = None,
                 append_returnlist_position: list[str] = None):
        """
        :param endpoint: the endpoint to send requests.
        :param method: the method to send requests, only accept 'GET' or 'POST'.
        :param partnerid: partner ID of an app.
        :param partnerkey: partner key of an app.
        :param shopid: shop ID of the Shopee shop that you want to retrieve data from.
        :param token: access_token of an app.
        :param headers: the header to send requests.
        :param starttime: a dictionary with key is a parameter name of requests, value is a parameter value showing the start time to fetch data.
                          Example: {'time_from':'2026-03-20 00:00:00'}
                          Note: If accepttypetime=='str', the datetime part must be 00:00:00
        :param endtime: a dictionary with key is a parameter name of requests, value is a parameter value showing the end time to fetch data.
                        Example: {'date_to':'2026-03-25 23:59:59'}
                        Note: If accepttypetime=='str', the datetime part must be 23:59:59
        :param accepttypetime: determine what is datatype of start time and end time to convert to. Only accept 'int' (convert to unix timestamp) or 'str' (convert to text YYYY-MM-DD).
        :param chunk_date: Some endpoints require the disparity between start time and end time must be less than a specific day. Read Shopee API docs to determine what integer to pass this parameter.
        :param pagesize: Limit the number of records return per request. Each endpoint have different limit number, read Shopee API docs to determine what integer to pass this parameter.
        :param pieceinfo_position: In each json response, this is a path leads to the list containing records.
        :param cursor_position: In each json response, this is a path leads to the cursor value.
        :param params_extension: some parameters add to the base params of the request. Base params is a dictionary with 5 keys are: access_token, shop_id, partner_id, sign, timestamp.
                                 Note: do not use following extensions (because you already declare them in other attributes): start_time, end_time, page_size, cursor.
        :param append_returnlist_position: In list of records, this is a path leads to the object you want to append in a return list.
        """
        if method not in ['GET', 'POST']:
            raise ValueError(f"The method attribute must be 'GET' or 'POST'. You passed '{method}'!")
        if accepttypetime not in ['int', 'str']:
            raise ValueError(f"The accepttypetime attribute must be 'int' or 'str'. You passed the '{accepttypetime}'")
        super().__init__(endpoint, partnerid, partnerkey, shopid, token, params_extension=params_extension)
        self.method = method
        self.headers = headers
        self.starttime = starttime
        self.endtime = endtime
        self.accepttypetime = accepttypetime
        self.chunk_date = chunk_date
        self.pagesize = pagesize
        self.pieceinfo_position = pieceinfo_position
        self.cursor_position = cursor_position
        self.append_returnlist_position = append_returnlist_position
    def extractdata(self) -> list:
        # Set variables:
        link, extension = super().extractdata()
        finaldata = []
        count = 0
        # Calculate starttime_value, endtime_value, and check starttime and endtime validation:
        starttime_key, starttime_value = next(iter(self.starttime.items()))
        endtime_key, endtime_value = next(iter(self.endtime.items()))
        currentdate = datetime.now(timezone(timedelta(hours=7)))
        currentdate = currentdate.replace(hour=0, minute=0, second=0, microsecond=0)
        currentdate = int(currentdate.timestamp())
        starttime_value = datetime.strptime(starttime_value, "%Y-%m-%d %H:%M:%S")
        starttime_value = starttime_value.replace(tzinfo=timezone(timedelta(hours=7)))
        starttime_value = int(starttime_value.timestamp())
        endtime_value = datetime.strptime(endtime_value, "%Y-%m-%d %H:%M:%S")
        endtime_value = endtime_value.replace(tzinfo=timezone(timedelta(hours=7)))
        endtime_value = int(endtime_value.timestamp())
        if starttime_value > endtime_value:
            raise ValueError("The endtime must greater than starttime")
        if endtime_value > currentdate:
            raise ValueError("The enddate must less than today")
        # If the disparity between starttime_value and endtime_value exceeds self.chunk_date, deviding the starttime_value and endtime_value interval into smaller interval, the long of each smaller interval is equal to or less than chunk_date:
        for date in range(starttime_value, endtime_value, self.chunk_date*24*60*60):
            if date + self.chunk_date*24*60*60-1 < endtime_value:
                edate = date + self.chunk_date*24*60*60-1
            else:
                edate = endtime_value
            if self.accepttypetime == 'str':
                date = datetime.fromtimestamp(date, tz=timezone.utc).astimezone(timezone(timedelta(hours=7)))
                date = str(date)[0:10]
                edate = datetime.fromtimestamp(edate, tz=timezone.utc).astimezone(timezone(timedelta(hours=7)))
                edate = str(edate)[0:10]
            nextpage = {}
            filters = {'page_size': self.pagesize, starttime_key: date, endtime_key: edate}
            while True:
                # Send requests in each smaller starttime_value and endtime_value interval. If result size is larger than self.pagesize, use the nextpage dictionary to retrieve next data:
                count = count + 1
                if count % 10 == 0:
                    time.sleep(5)
                print(f"Performing fetch data from Shopee Open API (endpoint {self.endpoint}, shopid {self.shopid}), sending request times: {count}")
                if self.method == 'GET':
                    finalfilterparams = extension | filters | nextpage
                    response = requests.get(url=link, headers=self.headers, params=finalfilterparams)
                else:
                    finalfilterparams = extension
                    body = filters | nextpage
                    response = requests.post(url=link, headers=self.headers, params=finalfilterparams, json=body)
                if response.status_code != 200:
                    raise RuntimeError(f"The Shopee API call (endpoint {self.endpoint}) return an error: \n{response.json()}")
                # Retrieve necessary data from json response and calculate the nextpage dictionary:
                result = response.json() # result is a dictionary
                data = result
                cursor = result
                # Retrieve necessary data from json response:
                try:
                    for key in self.pieceinfo_position:
                        data = data[key] # after all for loop, data now is a list containing dictionaries. Each dictionary is a record
                except:
                    data = []
                if len(data) == 0:
                    warnings.warn(f"The request to the endpoint {self.endpoint} has succeeded (shop id: {self.shopid}), but the list of records is empty!\nThe time interval: {date} to {edate}\nResponse:\n{result}")
                for piece in data:
                    if self.append_returnlist_position is not None:
                        for i in self.append_returnlist_position:
                            piece = piece[i]
                    finaldata.append(piece)
                # If there is no cursor key in the response or the cursor value is '' or None, break the while loop. Else calculate the nextpage dictionary:
                try:
                    for i in self.cursor_position:
                        cursor = cursor[i]
                    if cursor != '' and cursor is not None:
                        nextpage = {'cursor': cursor}
                    else:
                        break
                except:
                    break
        return finaldata


# ShopeeGetRecordsByListAPIExtractor class:
class ShopeeGetRecordsByListAPIExtractor(ShopeeAPIBaseExtractor):
    """
    Purpose: retrieve a list of records from list of IDs
    """
    def __init__(self,
                 endpoint: str,
                 method: Literal['GET', 'POST'],
                 partnerid: int,
                 partnerkey: str,
                 shopid: int,
                 token: str,
                 headers: dict[str,str],
                 idslist: list[str],
                 buildmethod: Literal['str', 'list[str]', 'list[dict]'],
                 keyoflist: str,
                 chunk_records: int,
                 pieceinfo_position: list[str],
                 *,
                 params_extension: dict[str, str] = None,
                 append_returnlist_position: list[str] = None,
                 keyname_buildmethodlistofdict = None):
        """
        :param endpoint: the endpoint to send requests.
        :param method: the method to send requests, only accept 'GET' or 'POST'.
        :param partnerid: partner ID of an app.
        :param partnerkey: partner key of an app.
        :param shopid: shop ID of the Shopee shop that you want to retrieve data from.
        :param token: access_token of an app.
        :param headers: the header to send requests.
        :param idslist: the list of IDs you want to retrieve data from.
        :param buildmethod: endpoints require different formats of idslist, this param define the format. Check the Shopee API docs to choose appropriate format. Only accept: 'str', 'list[str]', 'list[dict]'.
        :param keyoflist: this param defines the key of the dictionary whose value is the idslist.
        :param chunk_records: endpoints require limit number of IDs to pass each request, read Shopee API docs to determine what integer to pass this parameter.
        :param pieceinfo_position: in each json response, this is a path leads to the list containing records.
        :param params_extension: some parameters add to the base params of the request. Base params is a dictionary with 5 keys are: access_token, shop_id, partner_id, sign, timestamp.
                                 Note: do not use following extensions (because you already declare them in other attributes): order_sn_list/package_list.
        :param append_returnlist_position: in list of records, this is a path leads to the object you want to append in a return list.
        :param keyname_buildmethodlistofdict: if buildmethod=='list[dict]', this param defines the key of those inside dictionaries.
        """
        if method not in ['GET', 'POST']:
            raise ValueError(f"The method attribute must be 'GET' or 'POST'. You passed '{method}'!")
        if buildmethod not in ['str', 'list[str]', 'list[dict]']:
            raise ValueError(f"The buildmethod param must be one of three: 'str', 'list[str]', 'list[dict]'. But got {buildmethod}!")
        super().__init__(endpoint, partnerid, partnerkey, shopid, token, params_extension=params_extension)
        self.method = method
        self.headers = headers
        self.idslist = idslist
        self.buildmethod = buildmethod
        self.keyoflist = keyoflist
        self.chunk_records = chunk_records
        self.pieceinfo_position = pieceinfo_position
        self.append_returnlist_position = append_returnlist_position
        self.keyname_buildmethodlistofdict = keyname_buildmethodlistofdict
    def extractdata(self) -> list:
        # Set variables:
        finaldata = []
        link, extension = super().extractdata()
        count = 0
        # If the number of IDs is more than self.chunk_records, divides the list of IDs into smaller list of IDs, the number of IDs in each smaller list of IDs is less than or equals to self.chunk_records
        for x in range(0, len(self.idslist), self.chunk_records):
            subidslist = self.idslist[x:x+self.chunk_records]
            if self.buildmethod == 'str':
                idsdata = ''
                for i in range(0, len(subidslist), 1):
                    if i == len(subidslist) - 1:
                        idsdata = idsdata + str(subidslist[i])
                    else:
                        idsdata = idsdata + str(subidslist[i]) + ','
            elif self.buildmethod == 'list[str]':
                idsdata = subidslist
            elif self.buildmethod == 'list[dict]':
                idsdata = []
                for i in subidslist:
                    subdict = {self.keyname_buildmethodlistofdict:str(i)}
                    idsdata.append(subdict)
            count = count + 1
            if count % 10 == 0:
                time.sleep(5)
            print(f"Performing fetch data from Shopee Open API (endpoint {self.endpoint}, shopid {self.shopid}), sending request times: {count}")
            if self.method == 'GET':
                finalparams = extension | {self.keyoflist: idsdata}
                response = requests.get(url=link, headers=self.headers, params=finalparams)
            else:
                body = {self.keyoflist: idsdata}
                response = requests.post(url=link, headers=self.headers, params=extension, json=body)
            if response.status_code != 200:
                raise RuntimeError(f"The Shopee API call (endpoint {self.endpoint}) return an error: \n{response.json()}")
            origin_result = response.json() # origin_result is a dictionary
            result = origin_result
            try:
                for i in self.pieceinfo_position:
                    result = result[i] # after all for loop, result now is a list containing dictionaries. Each dictionary is a record
            except:
                result = []
            if len(result) == 0:
                warnings.warn(f"The request to the endpoint {self.endpoint} has succeeded (shop id: {self.shopid}), but the list of records is empty!\nList of IDs:\n{subidslist}\nResponse:\n{origin_result}")
            for piece in result:
                if self.append_returnlist_position is not None:
                    for i in self.append_returnlist_position:
                        piece = piece[i]
                finaldata.append(piece)
        return finaldata


# TiktokAPIAuthentication class:
class TiktokAPIAuthentication(Extractor):
    """
    Purpose: return a dictionary contains authentication information (access_token, refresh_token, expire_in,...) using Tiktok Shop Partner API
    """
    def __init__(self,
                 endpoint: str,
                 appkey: str,
                 appsecret: str,
                 token_dictinfo: dict[str,str],
                 granttype: str):
        """
        :param endpoint: the authentication endpoint to send the request
        :param appkey: app key of the app
        :param appsecret: app secret of the app
        :param token_dictinfo: a key:value dictionary with value is a token and key is the name of that token. Example: {'refresh_token':'Ryeryua1843jcfasd6u934j0'}
        :param granttype: each type of authentication has different granttype. For example: 'authorized_code', 'refresh_token',...
        """
        self.endpoint = endpoint
        self.appkey = appkey
        self.appsecret = appsecret
        self.token_dictinfo = token_dictinfo
        self.granttype = granttype
    def extractdata(self):
        params = {
            'app_key': self.appkey,
            'app_secret': self.appsecret,
            'grant_type': self.granttype
        } | self.token_dictinfo
        url = 'https://auth.tiktok-shops.com' + self.endpoint
        response = requests.get(url=url, params=params)
        return response.json()


# TiktokAPIBaseExtractor class:
class TiktokAPIBaseExtractor(Extractor):
    def __init__(self,
                 endpoint: str,
                 appkey: str,
                 appsecret: str,
                 access_token: str,
                 shop_cipher: str,
                 *,
                 headers_extension: dict = None,
                 params_extension: dict = None,
                 body_extension: dict = None):
        self.endpoint = endpoint
        self.appkey = appkey
        self.appsecret = appsecret
        self.access_token = access_token
        self.shop_cipher = shop_cipher
        self.headers_extension = headers_extension
        self.params_extension = params_extension
        self.body_extension = body_extension
        self.baseheaders = {'content-type': 'application/json'} | ({} if headers_extension is None else headers_extension)
        self.baseparams = {'app_key': appkey, 'timestamp': int(time.time()), 'shop_cipher': shop_cipher} | ({} if params_extension is None else params_extension)
        self.basebody = ({} if body_extension is None else body_extension)
    def buildparams(self, *, addparams: dict = None,  addbody: dict = None):
        sign = generate_sign(
            {
                'uri': self.endpoint,
                'qs': self.baseparams | ({} if addparams is None else addparams),
                'headers': self.baseheaders,
                'body': ({} if addbody is None else addbody)
            },
            self.appsecret
        )
        return self.baseparams | ({} if addparams is None else addparams) | {'sign': sign}
    def buildheaders(self):
        return self.baseheaders | {'x-tts-access-token':self.access_token}
    def buildbody(self, *, addbody: dict = None):
        return self.basebody | ({} if addbody is None else addbody)


# TiktokGetRecordsByTimeintervalAPIExtractor class:
class TiktokGetRecordsByTimeintervalAPIExtractor(TiktokAPIBaseExtractor):
    def __init__(self,
                 endpoint: str,
                 method: Literal['GET', 'POST'],
                 appkey: str,
                 appsecret: str,
                 access_token: str,
                 shop_cipher: str,
                 starttime: dict[str,str],
                 endtime: dict[str,str],
                 accepttypetime: Literal['int', 'str'],
                 pagesize,
                 pieceinfo_position: list[str],
                 nextpagetoken_position: list[str],
                 *,
                 headers_extension: dict = None,
                 params_extension: dict = None,
                 body_extension: dict = None,
                 append_returnlist_position: list[str] = None):
        """
        :param endpoint:
        :param method:
        :param appkey:
        :param appsecret:
        :param access_token:
        :param shop_cipher:
        :param starttime:
        :param endtime:
        :param accepttypetime:
        :param pagesize:
        :param pieceinfo_position: in each json response, this is a path leads to the list containing records.
        :param nextpagetoken_position: in each json response, this is a path leads to the next_page_token value.
        :param headers_extension: a dictionary contains key:value pairs to add to the headers of the request. Do not use: 'content-type' and 'x-tts-access-token'.
        :param params_extension: a dictionary contains key:value pairs to add to the params of the request. Do not use: 'app_key', 'sign', 'timestamp', 'shop_cipher', 'create(update)_time_ge'/'create(update)_time_lt', 'page_size' and 'page_token'.
        :param body_extension: a dictionary contains key:value pairs to add to the body of the request. Do not use: 'create(update)_time_ge'/'create(update)_time_lt'.
        :param append_returnlist_position: in list of records, this is a path leads to the object you want to append in a return list.
        """
        if method not in ['GET', 'POST']:
            raise ValueError(f"The method attribute must be 'GET' or 'POST'. You passed '{method}'!")
        if accepttypetime not in ['int', 'str']:
            raise ValueError(f"The accepttypetime attribute must be 'int' or 'str'. You passed the '{accepttypetime}'")
        super().__init__(endpoint, appkey, appsecret, access_token, shop_cipher, headers_extension=headers_extension, params_extension=params_extension, body_extension=body_extension)
        self.method = method
        self.starttime = starttime
        self.endtime = endtime
        self.accepttypetime = accepttypetime
        self.pagesize = pagesize
        self.pieceinfo_position = pieceinfo_position
        self.nextpagetoken_position = nextpagetoken_position
        self.append_returnlist_position = append_returnlist_position
    def extractdata(self) -> list:
        # Set variables:
        finaldata = []
        count = 0
        # Calculate starttime_value, endtime_value, and check starttime and endtime validation:
        starttime_key, starttime_value = next(iter(self.starttime.items()))
        endtime_key, endtime_value = next(iter(self.endtime.items()))
        currentdate = datetime.now(timezone(timedelta(hours=7)))
        currentdate = currentdate.replace(hour=0, minute=0, second=0, microsecond=0)
        currentdate = int(currentdate.timestamp())
        starttime_value = datetime.strptime(starttime_value, "%Y-%m-%d %H:%M:%S")
        starttime_value = starttime_value.replace(tzinfo=timezone(timedelta(hours=7)))
        starttime_value = int(starttime_value.timestamp())
        endtime_value = datetime.strptime(endtime_value, "%Y-%m-%d %H:%M:%S")
        endtime_value = endtime_value.replace(tzinfo=timezone(timedelta(hours=7)))
        endtime_value = int(endtime_value.timestamp())
        if starttime_value > endtime_value:
            raise ValueError("The endtime must greater than starttime")
        if endtime_value > currentdate:
            raise ValueError("The enddate must less than today")
        if self.accepttypetime == 'str':
            starttime_value = datetime.fromtimestamp(starttime_value, tz=timezone.utc).astimezone(timezone(timedelta(hours=7)))
            starttime_value = str(starttime_value)[0:10]
            endtime_value = datetime.fromtimestamp(endtime_value, tz=timezone.utc).astimezone(timezone(timedelta(hours=7)))
            endtime_value = str(endtime_value)[0:10]
        # Send requests to the server:
        next_page = {}
        url = 'https://open-api.tiktokglobalshop.com' + self.endpoint
        while True:
            count = count + 1
            if count % 10 == 0:
                time.sleep(3)
            print(f"Performing fetch data from Tiktok Shop Partner API (endpoint {self.endpoint}, shop cipher {self.shop_cipher}), sending request times: {count}")
            if self.method == 'GET':
                headers = super().buildheaders()
                params = super().buildparams(addparams = {'page_size': self.pagesize} | next_page | {starttime_key: starttime_value, endtime_key: endtime_value})
                arg = {'url': url, 'headers': headers, 'params': params}
            else:
                headers = super().buildheaders()
                params = super().buildparams(addparams = {'page_size': self.pagesize} | next_page, addbody = {starttime_key: starttime_value, endtime_key: endtime_value})
                body = super().buildbody(addbody = {starttime_key: starttime_value, endtime_key: endtime_value})
                arg = {'url': url, 'headers': headers, 'params': params, 'json':body}
            response = requests.request(method=self.method, **arg)
            if response.status_code != 200:
                response = handle_ratelimit_api(response.json(), self.method, arg, 20, 3)
            response_data = response.json() # response_data is a dictionary
            # Add records to the finaldata list:
            list_records = response_data
            nextpage_token = response_data
            try:
                for i in self.pieceinfo_position:
                    list_records = list_records[i] # after all loops, list_records is a list of dictionaries, each dictionary is a record
            except:
                list_records = []
            if len(list_records) == 0:
                warnings.warn(f"The request to the endpoint {self.endpoint} has succeeded (shop id: {self.shop_cipher}), but the list of records is empty!\nThe time interval: {starttime_value} to {endtime_value}.\nResponse:\n{response_data}")
            for piece in list_records:
                if self.append_returnlist_position is not None:
                    for i in self.append_returnlist_position:
                        piece = piece[i]
                finaldata.append(piece)
            # Calculate the next page parameter
            try:
                for i in self.nextpagetoken_position:
                    nextpage_token = nextpage_token[i]
                if nextpage_token != '' and nextpage_token is not None:
                    next_page = {'page_token':nextpage_token}
                else:
                    break
            except:
                break
        return finaldata


# TiktokGetRecordsByListAPIExtractor class:
class TiktokGetRecordsByListAPIExtractor(TiktokAPIBaseExtractor):
    def __init__(self,
                 endpoint: str,
                 method: Literal['GET', 'POST'],
                 appkey: str,
                 appsecret: str,
                 access_token: str,
                 shop_cipher: str,
                 idslist: list[str],
                 buildmethod: Literal['str', 'list[str]', 'list[dict]'],
                 keyoflist: str,
                 chunk_records: int,
                 pieceinfo_position: list[str],
                 *,
                 headers_extension: dict = None,
                 params_extension: dict = None,
                 body_extension: dict = None,
                 append_returnlist_position: list[str] = None,
                 keyname_buildmethodlistofdict = None
                 ):
        if method not in ['GET', 'POST']:
            raise ValueError(f"The method attribute must be 'GET' or 'POST'. You passed '{method}'!")
        if buildmethod not in ['str', 'list[str]', 'list[dict]']:
            raise ValueError(f"The buildmethod param must be one of three: 'str', 'list[str]', 'list[dict]'. But got {buildmethod}!")
        super().__init__(endpoint, appkey, appsecret, access_token, shop_cipher, headers_extension=headers_extension, params_extension=params_extension, body_extension=body_extension)
        self.method = method
        self.idslist = idslist
        self.buildmethod = buildmethod
        self.keyoflist = keyoflist
        self.chunk_records = chunk_records
        self.pieceinfo_position = pieceinfo_position
        self.append_returnlist_position = append_returnlist_position
        self.keyname_buildmethodlistofdict = keyname_buildmethodlistofdict
    def extractdata(self) -> list:
        # Set variables:
        finaldata = []
        url = 'https://open-api.tiktokglobalshop.com' + self.endpoint
        count = 0
        # If the number of IDs is more than self.chunk_records, divides the list of IDs into smaller list of IDs, the number of IDs in each smaller list of IDs is less than or equals to self.chunk_records:
        for x in range(0, len(self.idslist), self.chunk_records):
            subidslist = self.idslist[x:x+self.chunk_records]
            if self.buildmethod == 'str':
                idsdata = ''
                for i in range(0, len(subidslist), 1):
                    if i == len(subidslist) - 1:
                        idsdata = idsdata + str(subidslist[i])
                    else:
                        idsdata = idsdata + str(subidslist[i]) + ','
            elif self.buildmethod == 'list[str]':
                idsdata = subidslist
            elif self.buildmethod == 'list[dict]':
                idsdata = []
                for i in subidslist:
                    subdict = {self.keyname_buildmethodlistofdict:str(i)}
                    idsdata.append(subdict)
            count = count + 1
            if count % 10 == 0:
                time.sleep(3)
            print(f"Performing fetch data from Tiktok Shop Partner API (endpoint {self.endpoint}, shop cipher {self.shop_cipher}), sending request times: {count}")
            # Send a request to the server:
            if self.method == 'GET':
                headers = super().buildheaders()
                params = super().buildparams(addparams = {self.keyoflist:idsdata})
                arg = {'url': url, 'headers': headers, 'params': params}
            else:
                headers = super().buildheaders()
                params = super().buildparams(addbody = {self.keyoflist:idsdata})
                body = super().buildbody(addbody = {self.keyoflist:idsdata})
                arg = {'url': url, 'headers': headers, 'params': params, 'json': body}
            response = requests.request(method=self.method, **arg)
            if response.status_code != 200:
                response = handle_ratelimit_api(response.json(), self.method, arg, 20, 3)
            response_result = response.json()
            response_data = response_result
            try:
                for i in self.pieceinfo_position:
                    response_data = response_data[i] # after all loops, response_data is a list of dictionaries, each dictionary is a record
            except:
                response_data = []
            if len(response_data) == 0:
                warnings.warn(f"The request to the endpoint {self.endpoint} has succeeded (shop id: {self.shop_cipher}), but the list of records is empty!\nList of IDs:\n{subidslist}\nResponse:\n{response_result}")
            for record in response_data:
                if self.append_returnlist_position is not None:
                    for i in self.append_returnlist_position:
                        record = record[i]
                finaldata.append(record)
        return finaldata