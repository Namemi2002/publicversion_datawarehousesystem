from src.extractor import extractorclasses
from src.cleaner import cleanerclasses
from src.loader import loaderclasses
from datetime import datetime, timezone, timedelta
import yaml
from pathlib import Path
import pandas as pd
import time
import glob
import warnings


# Declare necessary variables
ROOTDIR = Path(__file__).resolve().parent.parent
CONFIGPATH = ROOTDIR / 'pipelineconfig.yaml'
GGSERVICEKEY = ROOTDIR / 'secretkey' / 'googlesheet_service_key.json'
SECRETKEYPATH = ROOTDIR / 'secretkey' / 'key.yaml'
ETLTOLAKE_QUERYPATH = ROOTDIR / 'warehouse' / 'datalake' / 'etltolake.sql'
LAKETOWAREHOUSE_QUERYPATH = ROOTDIR / 'warehouse' / 'datawarehouse' / 'laketowarehouse.sql'
DELETERECORDS_NHANHVN_QUERYPATH = ROOTDIR / 'warehouse' / 'deleterecords_nhanhvnorders.sql'
currenttime = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None)
successdash = '----------------------------------------------'
faileddash = '\n--------------------------------------------------------------------------------------------------------------------------------------'


# Declare variables that contain config and secret information
with open(CONFIGPATH, 'r', encoding='utf-8') as file:
    configinfo = yaml.safe_load(file) # configinfo is a dictionary
with open(SECRETKEYPATH, 'r') as file:
    secretinfo = yaml.safe_load(file) # secretinfo is a dictionary


# Build functions to run ETL pipelines:
def read_sqlquery(filepath, split_char: str, fileencoding='utf-8'):
    """
    :param filepath: the file contains queries that you want to convert to a key:value dictionary
    :param split_char: character to split queries
    :param fileencoding: 'utf-8' as default
    :return: return a key:value dictionary, key is the name of the mysql query, value is the query
    """
    with open(filepath, 'r', encoding=fileencoding) as file:
        content = file.read() # content is a string
    dict_query = {}
    content = content.split(split_char) # content now becomes a list of strings
    for text in content:
        if text.strip() == '':
            continue
        else:
            query = text.strip().split('\n') # query is a list of strings
            key = query[0].strip()
            value = ''
            for i in query[1:]:
                value = value + i.strip() + '\n'
            value = value.strip()
            dict_query[key] = value
    return dict_query
etltolake_query = read_sqlquery(ETLTOLAKE_QUERYPATH, '--name:')


def run_sqlscript(filepath, connection, *, params: dict[str,any] = None, fileencoding = 'utf-8'):
    """
    Purpose: execute all query in a .sql file
    :param filepath: the file contains queries you want to execute
    :param params: the .sql file may contain named placeholder (showed inside {}), use this parameter to fill those placeholders. params is a key:value dictionary, key is placeholder name, value is placeholder value
    :param connection: mysql.connector.connection.MySQLConnection object
    :param fileencoding: 'utf-8' as default
    :return: None.
    """
    with open(filepath, 'r', encoding=fileencoding) as file:
        content = file.read() # content is a string
    if params is not None:
        content = content.format(**params)
    content = content.split(';') # content now becomes a list of strings
    cursor = connection.cursor()
    try:
        for query in content:
            query = query.strip()
            if query == '':
                continue
            else:
                cursor.execute(query)
                print(f"Successfully perform the query:\n{query}\n{successdash}")
        connection.commit()
    except:
        connection.rollback()
        raise
    finally:
        cursor.close()


def run_shopee_apietl(sqlconnection):
    shopeetoken = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
    shopinfo = shopeetoken.extractlist(secretinfo['shopee']['token']['workbookid'], secretinfo['shopee']['token']['sheetid'], 'A2:I')
    for shop in shopinfo:
        try:
            # If the access_token is nearly or was expired, refresh the access_token and store new access_token and new refresh_token into the google sheet file:
            current = int(currenttime.timestamp())
            if int(shop[7]) + int(shop[8]) < current + configinfo['shopee']['token']['timerenew_beforeexpired']:
                print(f"orchestrator: run_shopee_apietl: refresh the access_token for shop {shop[1]}")
                # Refresh the access_token:
                refresh_shopee = extractorclasses.ShopeeAPIAuthentication(
                    '/api/v2/auth/access_token/get',
                    int(shop[3]),
                    shop[4],
                    int(shop[2]),
                    shop[6],
                    configinfo['shopee']['token']['header_gettoken_endpoint']
                )
                tokeninfo = refresh_shopee.extractdata() # tokeninfo is a dictionary: dict[str, str]
                shop[5] = tokeninfo['access_token']
                # Store new access_token and new refresh_token:
                sheetupdate = shopeetoken.extractsheet(secretinfo['shopee']['token']['workbookid'], secretinfo['shopee']['token']['sheetid'])
                sheetupdate.update_acell('F' + str(int(shop[0])+1), tokeninfo['access_token'])
                sheetupdate.update_acell('G' + str(int(shop[0])+1), tokeninfo['refresh_token'])
                sheetupdate.update_acell('H' + str(int(shop[0])+1), current)
                sheetupdate.update_acell('I' + str(int(shop[0])+1), tokeninfo['expire_in'])
            # Extract: retrieve json data:
            print(f"orchestrator: run_shopee_apietl: retrieve orders data from API, shop {shop[1]}")
            orders = extractorclasses.ShopeeGetRecordsByTimeintervalAPIExtractor(
                '/api/v2/order/get_order_list',
                'GET',
                int(shop[3]),
                shop[4],
                int(shop[2]),
                shop[5],
                configinfo['shopee']['api']['header_other_endpoints'],
                configinfo['shopee']['api']['orders']['starttime'],
                configinfo['shopee']['api']['orders']['endtime'],
                'int',
                configinfo['shopee']['api']['orders']['chunk_date'],
                configinfo['shopee']['api']['orders']['page_size'],
                ['response', 'order_list'],
                ['response', 'next_cursor'],
                params_extension={'time_range_field': 'create_time'},
                append_returnlist_position=['order_sn']
            )
            orders_data = orders.extractdata() # orders_data is a list of string, each string is an order ID
            orderdetail = extractorclasses.ShopeeGetRecordsByListAPIExtractor(
                '/api/v2/order/get_order_detail',
                'GET',
                int(shop[3]),
                shop[4],
                int(shop[2]),
                shop[5],
                configinfo['shopee']['api']['header_other_endpoints'],
                orders_data,
                'str',
                'order_sn_list',
                configinfo['shopee']['api']['orderdetail']['chunk_record'],
                ['response', 'order_list'],
                params_extension={'response_optional_fields':'buyer_user_id,buyer_username,estimated_shipping_fee,recipient_address,actual_shipping_fee,note,note_update_time,item_list,pay_time,buyer_cancel_reason,cancel_by,cancel_reason,actual_shipping_fee_confirmed,fulfillment_flag,pickup_done_time,package_list,shipping_carrier,payment_method,total_amount,buyer_username,invoice_data,return_request_due_date,payment_info,model_discounted_price,model_original_price'}
            )
            orderdetail_data = orderdetail.extractdata() # orderdetail_data is a list of dictionaries, each dictionary is detail information of an order
            escrowdetail = extractorclasses.ShopeeGetRecordsByListAPIExtractor(
                '/api/v2/payment/get_escrow_detail_batch',
                'POST',
                int(shop[3]),
                shop[4],
                int(shop[2]),
                shop[5],
                configinfo['shopee']['api']['header_other_endpoints'],
                orders_data,
                'list[str]',
                'order_sn_list',
                configinfo['shopee']['api']['escrowdetail']['chunk_record'],
                ['response'],
                append_returnlist_position=['escrow_detail']
            )
            escrowdetail_data = escrowdetail.extractdata() # escrowdetail_data is list of dictionaries, each dictionary is escrow detail information of an order
            trackingnumber = extractorclasses.ShopeeGetRecordsByListAPIExtractor(
                '/api/v2/logistics/get_mass_tracking_number',
                'POST',
                int(shop[3]),
                shop[4],
                int(shop[2]),
                shop[5],
                configinfo['shopee']['api']['header_other_endpoints'],
                extractorclasses.getshopeepackagelist_fromorderdetaillist(orderdetail_data),
                'list[dict]',
                'package_list',
                configinfo['shopee']['api']['mass_tracking_number']['chunk_record'],
                ['response', 'success_list'],
                keyname_buildmethodlistofdict='package_number'
            )
            trackingnumber_data = trackingnumber.extractdata() # trackingnumber_data is a list of dictionaries, each dictionary contains information of package_number and tracking_number
            incomedetail = extractorclasses.ShopeeGetRecordsByTimeintervalAPIExtractor(
                '/api/v2/payment/get_income_detail',
                'GET',
                int(shop[3]),
                shop[4],
                int(shop[2]),
                shop[5],
                configinfo['shopee']['api']['header_other_endpoints'],
                configinfo['shopee']['api']['orderincome']['starttime'],
                configinfo['shopee']['api']['orderincome']['endtime'],
                'str',
                configinfo['shopee']['api']['orderincome']['chunk_date'],
                configinfo['shopee']['api']['orderincome']['page_size'],
                ['response', 'list'],
                ['response', 'next_page', 'cursor'],
                params_extension={'income_status': 1}
            )
            incomedetail_data = incomedetail.extractdata() # incomedetail_data is a list of dictionaries, each dictionary is income detail of an order
            # Clean: Convert json data to dataframe:
            print(f"orchestrator: run_shopee_apietl: clean orders data from API, shop {shop[1]}")
            cleanshopeeorder = cleanerclasses.OrdersShopeeAPICleaner(orderdetail_data, escrowdetail_data, trackingnumber_data, shop[1])
            shopeeorders_df = cleanshopeeorder.cleandata()
            shopeeorderdetails_df = cleanshopeeorder.cleandata_orderdetails()
            shopeeorders_df = cleanerclasses.cleandatetime_df(
                shopeeorders_df,
                {'Ngày đặt hàng':'s', 'Ngày lấy hàng':'s', 'Ngày hoàn thành':'s'},
                to_datetime_param = 'unit'
            )
            cleanincomedetail = cleanerclasses.IncomeShopeeAPICleaner(incomedetail_data)
            incomedetail_df = cleanincomedetail.cleandata()
            incomedetail_df = cleanerclasses.cleandatetime_df(
                incomedetail_df,
                {'Thời gian giao dịch': 's'},
                to_datetime_param='unit'
            )
            # Upload: Upload the dataframe to datalake:
            print(f"orchestrator: run_shopee_apietl: upload orders data from API to datalake, shop {shop[1]}")
            loadorders = loaderclasses.DataframeToDatabaseLoader(
                shopeeorders_df,
                sqlconnection,
                etltolake_query['shopeeorders'],
                currenttime
            )
            loadorderdetail = loaderclasses.DataframeToDatabaseLoader(
                shopeeorderdetails_df,
                sqlconnection,
                etltolake_query['shopeeorderdetails'],
                currenttime
            )
            loadincomedetail = loaderclasses.DataframeToDatabaseLoader(
                incomedetail_df,
                sqlconnection,
                etltolake_query['delivery_reconciliation'],
                currenttime
            )
            loadorders.loaddata()
            loadorderdetail.loaddata()
            loadincomedetail.loaddata()
            print(f"orchestrator: run_shopee_apietl: the whole ETL for shop {shop[1]} has run successfully!{successdash}")
            time.sleep(5)
        except Exception as e:
            warnings.warn(f"orchestrator: run_shopee_apietl: the ETL pipeline for shop {shop[1]} has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_tiktok_apietl(sqlconnection):
    tiktoktoken = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
    shopinfo = tiktoktoken.extractlist(secretinfo['tiktok']['token']['workbookid'], secretinfo['tiktok']['token']['sheetid'], 'A2:I')
    for shop in shopinfo:
        try:
            # If the access_token is nearly or was expired, refresh the access_token and store new access_token and new refresh_token into the google sheet file:
            current = int(currenttime.timestamp())
            if int(shop[7]) < current + configinfo['tiktok']['token']['timerenew_beforeexpired']:
                print(f"orchestrator: run_tiktok_apietl: refresh the access_token for shop {shop[1]}")
                # Refresh the access_token:
                refresh_tiktok = extractorclasses.TiktokAPIAuthentication(
                    '/api/v2/token/refresh',
                    shop[3],
                    shop[4],
                    {'refresh_token': shop[6]},
                    'refresh_token'
                )
                tokeninfo = refresh_tiktok.extractdata()  # tokeninfo is a dictionary: dict[str, Any]
                shop[5] = tokeninfo['data']['access_token']
                # Store new access_token and new refresh_token:
                sheetupdate = tiktoktoken.extractsheet(secretinfo['tiktok']['token']['workbookid'], secretinfo['tiktok']['token']['sheetid'])
                sheetupdate.update_acell('F' + str(int(shop[0]) + 1), tokeninfo['data']['access_token'])
                sheetupdate.update_acell('G' + str(int(shop[0]) + 1), tokeninfo['data']['refresh_token'])
                sheetupdate.update_acell('H' + str(int(shop[0]) + 1), tokeninfo['data']['access_token_expire_in'])
                sheetupdate.update_acell('I' + str(int(shop[0]) + 1), tokeninfo['data']['refresh_token_expire_in'])
            # Extract: retrieve json data:
            print(f"orchestrator: run_tiktok_apietl: retrieve orders data from API, shop {shop[1]}")
            orders = extractorclasses.TiktokGetRecordsByTimeintervalAPIExtractor(
                '/order/202309/orders/search',
                'POST',
                shop[3],
                shop[4],
                shop[5],
                shop[2],
                configinfo['tiktok']['api']['orders']['strattime'],
                configinfo['tiktok']['api']['orders']['endtime'],
                'int',
                configinfo['tiktok']['api']['orders']['page_size'],
                ['data', 'orders'],
                ['data', 'next_page_token']
            )
            orders_data = orders.extractdata() # orders_data is a list of dictionaries, each dictionary is information of an order
            returnorders = extractorclasses.TiktokGetRecordsByListAPIExtractor(
                '/return_refund/202602/returns/search',
                'POST',
                shop[3],
                shop[4],
                shop[5],
                shop[2],
                extractorclasses.gettiktokidlist_fromorderlist(orders_data),
                'list[str]',
                'order_ids',
                configinfo['tiktok']['api']['returnorders']['chunk_record'],
                ['data', 'return_orders']
            )
            returnorders_data = returnorders.extractdata() # returnorders_data is a list of dictionaries, each dictionary is information of a returned order
            # Clean: Convert json data to dataframe:
            print(f"orchestrator: run_tiktok_apietl: clean orders data from API, shop {shop[1]}")
            cleantiktokorder = cleanerclasses.OrdersTiktokAPICleaner(orders_data, returnorders_data, shop[1])
            tiktokorders_df = cleantiktokorder.cleandata()
            tiktokorderdetails_df = cleantiktokorder.cleandata_orderdetails()
            tiktokorders_df = cleanerclasses.cleandatetime_df(
                tiktokorders_df,
                {'create_time': 's', 'collection_time': 's', 'delivery_time': 's', 'cancel_time': 's'},
                to_datetime_param='unit'
            )
            # Upload: Upload the dataframe to datalake:
            print(f"orchestrator: run_tiktok_apietl: upload orders data from API to datalake, shop {shop[1]}")
            loadorders = loaderclasses.DataframeToDatabaseLoader(
                tiktokorders_df,
                sqlconnection,
                etltolake_query['tiktokorders'],
                currenttime
            )
            loadorderdetail = loaderclasses.DataframeToDatabaseLoader(
                tiktokorderdetails_df,
                sqlconnection,
                etltolake_query['tiktokorderdetails'],
                currenttime
            )
            loadorders.loaddata()
            loadorderdetail.loaddata()
            print(f"orchestrator: run_tiktok_apietl: the whole ETL for shop {shop[1]} has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_tiktok_apietl: the ETL pipeline for shop {shop[1]} has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_ghtk_exceletl(sqlconnection):
    for deliacc in configinfo['ghtk']['excel']['path'].values(): # deliacc is a dictionary
        try:
            accountname = deliacc['name']
            path_deliveryorders = deliacc['deliveryorders']
            checkpath_deliveryorders = deliacc['checkpath_deliveryorders']
            path_paymentminutes = deliacc['paymentminutes']
            checkpath_paymentminutes = deliacc['checkpath_paymentminutes']
            path_canceledorders = deliacc['canceledorders']
            checkpath_canceledorders = deliacc['checkpath_canceledorders']
            path_compensations = deliacc['compensations']
            checkpath_compensations = deliacc['checkpath_compensations']
            if path_deliveryorders is None or path_paymentminutes is None:
                warnings.warn(f"orchestrator: run_ghtk_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
            else:
                # Extract: Extract data from excel files:
                ghtk_deliveryorders = extractorclasses.DeliveryOrdersExcelExtractor(
                    'Giao Hang Tiet Kiem',
                    path_deliveryorders,
                    configinfo['ghtk']['excel']['usecols']['deliveryorders'],
                    configinfo['ghtk']['excel']['usedtype']['deliveryorders'],
                    15,
                    accountname,
                    checkpath_deliveryorders
                )
                ghtk_paymentminutes = extractorclasses.ExcelExtractor(
                    'Giao Hang Tiet Kiem',
                    path_paymentminutes,
                    configinfo['ghtk']['excel']['usecols']['paymentminutes'],
                    configinfo['ghtk']['excel']['usedtype']['deliveryorders'],
                    10,
                    checkpath_paymentminutes
                )
                ghtk_canceledorders = extractorclasses.ExcelExtractor(
                    'Giao Hang Tiet Kiem',
                    path_canceledorders,
                    configinfo['ghtk']['excel']['usecols']['deliveryorders'],
                    configinfo['ghtk']['excel']['usedtype']['deliveryorders'],
                    15,
                    checkpath_canceledorders
                )
                ghtk_compensations = extractorclasses.ExcelExtractor(
                    'Giao Hang Tiet Kiem',
                    path_compensations,
                    configinfo['ghtk']['excel']['usecols']['compensations'],
                    configinfo['ghtk']['excel']['usedtype']['compensations'],
                    0,
                    checkpath_compensations
                )
                df_ghtk_deliveryorders = ghtk_deliveryorders.extractdata()
                df_ghtk_paymentminutes = ghtk_paymentminutes.extractdata()
                if path_canceledorders is None:
                    df_ghtk_canceledorders = None
                else:
                    df_ghtk_canceledorders = ghtk_canceledorders.extractdata()
                if path_compensations is None:
                    df_ghtk_compensations = None
                else:
                    df_ghtk_compensations = ghtk_compensations.extractdata()
                # Clean: Clean dataframes:
                cleanghtkorders = cleanerclasses.DeliveryOrdersGHTKExcelCleaner(
                    configinfo['ghtk']['excel']['clean']['finalcols'],
                    df_ghtk_deliveryorders,
                    df_ghtk_paymentminutes,
                    configinfo['ghtk']['excel']['clean']['listfee_paymentminutes'],
                    df_ghtk_canceledorders,
                    df_ghtk_compensations
                )
                ghtkorders_df = cleanghtkorders.cleandata()
                ghtkorders_df = cleanerclasses.cleandatetime_df(
                    ghtkorders_df,
                    {'Thời gian tạo đơn':'%Y-%m-%d %H:%M:%S', 'Thời gian lấy thành công':'%Y-%m-%d %H:%M:%S', 'Thời gian giao hàng thành công':'%Y-%m-%d %H:%M:%S'},
                    to_datetime_param='format'
                )
                # Upload: Upload the dataframe to datalake:
                loadghtkorders = loaderclasses.DataframeToDatabaseLoader(
                    ghtkorders_df,
                    sqlconnection,
                    etltolake_query['deliveryorders'],
                    currenttime
                )
                loadghtkorders.loaddata()
                print(f"orchestrator: run_ghtk_exceletl: the whole ETL for the {accountname} account has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_ghtk_exceletl: the ETL pipeline for the {deliacc.get('name', 'WRONG AT CONFIG')} account has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_ghn_exceletl(sqlconnection):
    for deliacc in configinfo['ghn']['excel']['path'].values():
        try:
            accountname = deliacc['name']
            path_deliveryorders = deliacc['deliveryorders']
            checkpath_deliveryorders = deliacc['checkpath_deliveryorders']
            path_cointransactions = deliacc['cointransactions']
            checkpath_cointransactions = deliacc['checkpath_cointransactions']
            if path_deliveryorders is None or path_cointransactions is None:
                warnings.warn(f"orchestrator: run_ghn_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
            else:
                # Extract:
                ghn_deliveryorders = extractorclasses.DeliveryOrdersExcelExtractor(
                    'Giao Hang Nhanh',
                    path_deliveryorders,
                    configinfo['ghn']['excel']['usecols']['deliveryorders'],
                    configinfo['ghn']['excel']['usedtype']['deliveryorders'],
                    0,
                    accountname,
                    checkpath_deliveryorders
                )
                ghn_cointransactions = extractorclasses.ExcelExtractor(
                    'Giao Hang Nhanh',
                    path_cointransactions,
                    configinfo['ghn']['excel']['usecols']['cointransactions'],
                    configinfo['ghn']['excel']['usedtype']['cointransactions'],
                    2,
                    checkpath_cointransactions
                )
                df_ghn_deliveryorders = ghn_deliveryorders.extractdata()
                df_ghn_cointransactions = ghn_cointransactions.extractdata()
                # Clean:
                cleanghnorders = cleanerclasses.DeliveryOrdersGHNExcelCleaner(
                    configinfo['ghn']['excel']['clean']['finalcols'],
                    df_ghn_deliveryorders,
                    df_ghn_cointransactions
                )
                ghnorders_df = cleanghnorders.cleandata()
                ghnorders_df = cleanerclasses.cleandatetime_df(
                    ghnorders_df,
                    {'Ngày tạo đơn':'%d/%m/%Y', 'Ngày lấy hàng thành công':'%d/%m/%Y', 'Ngày giao hàng thành công':'%d/%m/%Y'},
                    to_datetime_param='format'
                )
                # Upload:
                loadghnorders = loaderclasses.DataframeToDatabaseLoader(
                    ghnorders_df,
                    sqlconnection,
                    etltolake_query['deliveryorders'],
                    currenttime
                )
                loadghnorders.loaddata()
                print(f"orchestrator: run_ghn_exceletl: the whole ETL for the {accountname} account has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_ghn_exceletl: the ETL pipeline for the {deliacc.get('name', 'WRONG AT CONFIG')} account has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_jte_exceletl(sqlconnection):
    for deliacc in configinfo['jte']['excel']['path'].values():
        try:
            accountname = deliacc['name']
            path_deliveryorders = deliacc['deliveryorders']
            checkpath_deliveryorders = deliacc['checkpath_deliveryorders']
            if path_deliveryorders is None:
                warnings.warn(f"orchestrator: run_jte_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
            else:
                # Extract:
                jte_deliveryorders = extractorclasses.DeliveryOrdersExcelExtractor(
                    'JT Express',
                    path_deliveryorders,
                    configinfo['jte']['excel']['usecols']['deliveryorders'],
                    configinfo['jte']['excel']['usedtype']['deliveryorders'],
                    0,
                    accountname,
                    checkpath_deliveryorders
                )
                df_jte_deliveryorders = jte_deliveryorders.extractdata()
                # Clean:
                cleanjteorders = cleanerclasses.DeliveryOrdersJTEExcelCleaner(
                    configinfo['jte']['excel']['clean']['finalcols'],
                    df_jte_deliveryorders
                )
                jteorders_df = cleanjteorders.cleandata()
                jteorders_df = cleanerclasses.cleandatetime_df(
                    jteorders_df,
                    {'Thời gian tạo đơn':'%Y-%m-%d %H:%M', 'Thời gian lấy hàng':'%Y-%m-%d %H:%M', 'Thời gian ký nhận':'%Y-%m-%d %H:%M'},
                    to_datetime_param='format'
                )
                # Upload:
                loadjteorders = loaderclasses.DataframeToDatabaseLoader(
                    jteorders_df,
                    sqlconnection,
                    etltolake_query['deliveryorders'],
                    currenttime
                )
                loadjteorders.loaddata()
                print(f"orchestrator: run_jte_exceletl: the whole ETL for the {accountname} account has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_jte_exceletl: the ETL pipeline for the {deliacc.get('name', 'WRONG AT CONFIG')} account has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_spx_exceletl(sqlconnection):
    for deliacc in configinfo['spx']['excel']['path'].values():
        try:
            accountname = deliacc['name']
            path_deliveryorders = deliacc['deliveryorders']
            checkpath_deliveryorders = deliacc['checkpath_deliveryorders']
            if path_deliveryorders is None:
                warnings.warn(f"orchestrator: run_spx_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
            else:
                # Extract:
                spx_deliveryorders = extractorclasses.DeliveryOrdersExcelExtractor(
                    'Shopee Express',
                    path_deliveryorders,
                    configinfo['spx']['excel']['usecols']['deliveryorders'],
                    configinfo['spx']['excel']['usedtype']['deliveryorders'],
                    3,
                    accountname,
                    checkpath_deliveryorders
                )
                df_spx_deliveryorders = spx_deliveryorders.extractdata()
                # Clean:
                cleanspxorders = cleanerclasses.DeliveryOrdersSPXExcelCleaner(
                    configinfo['spx']['excel']['clean']['finalcols'],
                    df_spx_deliveryorders
                )
                spxorders_df = cleanspxorders.cleandata()
                spxorders_df = cleanerclasses.cleandatetime_df(
                    spxorders_df,
                    {'Thời gian tạo đơn':'%Y-%m-%d %H:%M', 'Thời gian lấy hàng/gửi hàng':'%Y-%m-%d %H:%M', 'Thời gian giao hàng':'%Y-%m-%d %H:%M'},
                    to_datetime_param='format'
                )
                # Upload:
                loadspxorders = loaderclasses.DataframeToDatabaseLoader(
                    spxorders_df,
                    sqlconnection,
                    etltolake_query['deliveryorders'],
                    currenttime
                )
                loadspxorders.loaddata()
                print(f"orchestrator: run_spx_exceletl: the whole ETL for the {accountname} account has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_spx_exceletl: the ETL pipeline for the {deliacc.get('name', 'WRONG AT CONFIG')} account has failed. Data have not been loaded to datalake. Error messgae:\n{e}{faileddash}")


def run_cusbank_apietl(sqlconnection):
    try:
        idfile = configinfo['cusbank']['idfile']
        idsheet = configinfo['cusbank']['idsheet']
        # Extract:
        print(f"orchestrator: run_cusbank_apietl: retrive customer banking data from google sheet API (idfile: {idfile}, idsheet: {idsheet})")
        opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
        df_cusbank = opensheet.extractdataframe(
            idfile,
            idsheet,
            configinfo['cusbank']['datarange'],
            configinfo['cusbank']['usecols']
        )
        # Clean:
        print(f"orchestrator: run_cusbank_apietl: clean customer banking data from google sheet API")
        cleancusbank = cleanerclasses.CustomerBankingAPICleaner(
            configinfo['cusbank']['finalcols'],
            df_cusbank
        )
        df_cusbank = cleancusbank.cleandata()
        df_cusbank = cleanerclasses.cleandatetime_df(
            df_cusbank,
            {'Ngày':'%d/%m/%Y'},
            to_datetime_param='format'
        )
        # Upload:
        print(f"orchestrator: run_cusbank_apietl: upload customer banking data from google sheet API on datalake")
        loadcusbank = loaderclasses.DataframeToDatabaseLoader(
            df_cusbank,
            sqlconnection,
            etltolake_query['customerbanks'],
            currenttime
        )
        loadcusbank.loaddata()
        print(f"orchestrator: run_cusbank_apietl: the whole ETL has run successfully!{successdash}")
    except Exception as e:
        warnings.warn(f"orchestrator: run_cusbank_apietl: the ETL pipeline has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_codtvc_apietl(sqlconnection):
    for file,sheet in configinfo['codtvc']['files'].items():
        try:
            # Extract:
            print(f"orchestrator: run_codtvc_apietl: retrieve codtvc data from google sheet API (idfile: {file}, idsheet: {sheet})")
            opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
            df_codtvc = opensheet.extractdataframe(
                file,
                sheet,
                configinfo['codtvc']['datarange'],
                configinfo['codtvc']['usecols']
            )
            # Clean:
            print(f"orchestrator: run_codtvc_apietl: clean codtvc data from google sheet API (idfile: {file}, idsheet: {sheet})")
            cleancodtvc = cleanerclasses.CodTvcAPICleaner(
                configinfo['codtvc']['finalcols'],
                df_codtvc
            )
            df_codtvc = cleancodtvc.cleandata()
            df_codtvc = cleanerclasses.cleandatetime_df(
                df_codtvc,
                {'Ngày lên':'%d/%m/%Y', 'Ngày đi':'%d/%m/%Y'},
                to_datetime_param='format'
            )
            # Upload:
            print(f"orchestrator: run_codtvc_apietl: upload codtvc data from google sheet API (idfile: {file}, idsheet: {sheet}) on datalake")
            loadcodtvc = loaderclasses.DataframeToDatabaseLoader(
                df_codtvc,
                sqlconnection,
                etltolake_query['deliveryorders'],
                currenttime
            )
            loadcodtvc.loaddata()
            print(f"orchestrator: run_codtvc_apietl: the whole ETL (file {file}, sheet: {sheet}) has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_codtvc_apietl: the ETL pipeline for codtvc data in (file {file}, sheet: {sheet}) has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}\nNote that some 'Tu Van Chuyen' orders may don't have their tracking number in the fact_orderdetails table")


def run_internalprice_apietl(sqlconnection):
    try:
        idfile = configinfo['internalprice']['idfile']
        idsheet = configinfo['internalprice']['idsheet']
        # Extract:
        print(f"orchestrator: run_internalprice_apietl: retrieve internal price information of products using google sheet API (idfile: {idfile}, idsheet: {idsheet})")
        opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
        df_internalprice = opensheet.extractdataframe(
            idfile,
            idsheet,
            configinfo['internalprice']['datarange'],
            configinfo['internalprice']['usecols']
        )
        # Clean:
        print(f"orchestrator: run_internalprice_apietl: clean internal price information of products using google sheet API")
        cleaninternalprice = cleanerclasses.InternalPriceAPICleaner(
            configinfo['internalprice']['finalcols'],
            df_internalprice
        )
        df_internalprice = cleaninternalprice.cleandata()
        # Upload:
        print(f"orchestrator: run_internalprice_apietl: upload internal price information of products using google sheet API on data warehouse")
        loadinterprice = loaderclasses.DataframeToDatabaseLoader(
            df_internalprice,
            sqlconnection,
            etltolake_query['dim_product'],
            currenttime,
            enable_updatetime='No'
        )
        loadinterprice.loaddata()
        print(f"orchestrator: run_internalprice_apietl: the whole ETL has run successfully!{successdash}")
    except Exception as e:
        warnings.warn(f"orchestrator: run_internalprice_apietl: the ETL pipeline has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_returnedorderscan_apietl(sqlconnection):
    for deli in configinfo['returnedorderscan']['sheetinfo'].values(): # deli is a dictionary
        try:
            # Extract:
            print(f"orchestrator: run_returnedorderscan_apietl: retrieve returned orders scanning data from google sheet API (idfile: {configinfo['returnedorderscan']['idfile']}, idsheet: {deli['idsheet']})")
            opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
            df_scanreturnedorder = opensheet.extractdataframe(
                configinfo['returnedorderscan']['idfile'],
                deli['idsheet'],
                deli['datarange'],
                deli['usecols']
            )
            time.sleep(5)
            # Clean:
            print(f"orchestrator: run_returnedorderscan_apietl: clean returned orders scanning data from google sheet API")
            cleanscanreturnedorder = cleanerclasses.ReturnedOrdersScanTrackingNumberAPICleaner(
                configinfo['returnedorderscan']['finalcols'],
                df_scanreturnedorder,
                2026
            )
            df_scanreturnedorder = cleanscanreturnedorder.cleandata()
            df_scanreturnedorder = cleanerclasses.cleandatetime_df(
                df_scanreturnedorder,
                {'Ngày bắn':'%Y-%m-%d'},
                to_datetime_param='format'
            )
            # Upload:
            print(f"orchestrator: run_returnedorderscan_apietl: upload returned orders scanning data from google sheet API to datalake")
            loadreturnedorder = loaderclasses.DataframeToDatabaseLoader(
                df_scanreturnedorder,
                sqlconnection,
                etltolake_query['returnedorders_scan'],
                currenttime
            )
            loadreturnedorder.loaddata()
            print(f"orchestrator: run_returnedorderscan_apietl: the whole ETL for {deli['idsheet']} sheet has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_returnedorderscan_apietl: the ETL pipeline for (file: {configinfo['returnedorderscan']['idfile']}, sheet: {deli.get('idsheet', 'WRONG AT CONFIG')}) has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_deliveryorderscan_apietl(sqlconnection):
    try:
        idfile = configinfo['deliveryorderscan']['idfile']
        idsheet = configinfo['deliveryorderscan']['idsheet']
        # Extract:
        opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
        df_scandeliveryorder = opensheet.extractdataframe(
            idfile,
            idsheet,
            configinfo['deliveryorderscan']['datarange'],
            configinfo['deliveryorderscan']['usecols']
        )
        # Clean:
        cleanscandeliveryorder = cleanerclasses.DeliveryOrdersScanTrackingNumberAPICleaner(
            configinfo['deliveryorderscan']['finalcols'],
            df_scandeliveryorder
        )
        df_scandeliveryorder = cleanscandeliveryorder.cleandata()
        df_scandeliveryorder = cleanerclasses.cleandatetime_df(
            df_scandeliveryorder,
            {'Ngày bắn đơn':'%Y-%m-%d'},
            to_datetime_param='format'
        )
        # Upload:
        loaddeliveryorder = loaderclasses.DataframeToDatabaseLoader(
            df_scandeliveryorder,
            sqlconnection,
            etltolake_query['handle_deliveryorders'],
            currenttime
        )
        loaddeliveryorder.loaddata()
        print(f"orchestrator: run_deliveryorderscan_apietl: the whole ETL has run successfully!{successdash}")
    except Exception as e:
        warnings.warn(f"orchestrator: run_deliveryorderscan_apietl: the ETL pipeline has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_deliveryordershandlingteam_apietl(sqlconnection):
    for deli in configinfo['deliveryordershandlingteam']['sheetpath'].values(): # deli is a dictionary
        try:
            # Extract:
            print(f"orchestrator: run_deliveryordershandlingteam_apietl: retrieve note data of handling team using google sheet API, idfile: {deli['idfile']}")
            finaldf = pd.DataFrame(columns=configinfo['deliveryordershandlingteam']['finalcols']).astype('object')
            opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
            for sheet in deli['sheets']: # sheet is an integer
                print(f"orchestrator: run_deliveryordershandlingteam_apietl: retrieve data sheet {sheet}")
                df_handleteam = opensheet.extractdataframe(
                    deli['idfile'],
                    sheet,
                    configinfo['deliveryordershandlingteam']['datarange'],
                    configinfo['deliveryordershandlingteam']['usecols']
                )
                time.sleep(5)
                # Clean:
                print(f"orchestrator: run_deliveryordershandlingteam_apietl: clean data sheet {sheet}")
                cleanhandleteam = cleanerclasses.DeliveryOrdersHandlingTeamAPICleaner(
                    configinfo['deliveryordershandlingteam']['finalcols'],
                    df_handleteam
                )
                df_handleteam = cleanhandleteam.cleandata()
                finaldf = pd.concat([finaldf, df_handleteam], axis=0)
            # Upload
            print(f"orchestrator: run_deliveryordershandlingteam_apietl: upload note data of handling team using google sheet API on datalake, idfile: {deli['idfile']}")
            loadhandleteam = loaderclasses.DataframeToDatabaseLoader(
                finaldf,
                sqlconnection,
                etltolake_query['handle_deliveryorders'],
                currenttime
            )
            loadhandleteam.loaddata()
            print(f"orchestrator: run_deliveryordershandlingteam_apietl: the whole ETL has run successfully!{successdash}")
        except Exception as e:
            warnings.warn(f"orchestrator: run_deliveryordershandlingteam_apietl: the ETL pipeline for file {deli.get('idfile', 'WRONG AT CONFIG')} has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_jtetransactions_exceletl(sqlconnection):
    if configinfo['transaction_jte']['excel']['folderpath'] is None:
        warnings.warn(f"orchestrator: run_jtetransactions_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
    else:
        listpath = glob.glob(configinfo['transaction_jte']['excel']['folderpath'] + r'\*') # listpath is a list of strings, each string is a path of an excel file
        for path in listpath:
            try:
                if path.casefold().find('(') == -1:
                    # Extract:
                    jtetransac = extractorclasses.ExcelExtractor(
                        'JT Express',
                        path,
                        configinfo['transaction_jte']['excel']['usecols'],
                        configinfo['transaction_jte']['excel']['usedtype'],
                        0,
                        configinfo['transaction_jte']['excel']['check_filepath']
                    )
                    df_jtetransac = jtetransac.extractdata()
                    # Clean:
                    cleanjtetransac = cleanerclasses.TransactionsJTEExcelCleaner(
                        configinfo['transaction_jte']['excel']['finalcols'],
                        df_jtetransac
                    )
                    df_jtetransac = cleanjtetransac.cleandata()
                    # Upload:
                    loadjtetransac = loaderclasses.DataframeToDatabaseLoader(
                        df_jtetransac,
                        sqlconnection,
                        etltolake_query['delivery_reconciliation'],
                        currenttime
                    )
                    loadjtetransac.loaddata()
                    print(f"orchestrator: run_jtetransactions_exceletl: the whole ETL for the {path} filepath has run successfully!{successdash}")
                else:
                    raise warnings.warn(f"The file path {path} contains '(' characters, data in this file won't be upload on database!{faileddash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_jtetransactions_exceletl: the ETL pipeline for the {path} filepath has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_spxtransactions_exceletl(sqlconnection):
    if configinfo['transaction_spx']['excel']['folderpath'] is None:
        warnings.warn(f"orchestrator: run_spxtransactions_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
    else:
        listpath = glob.glob(configinfo['transaction_spx']['excel']['folderpath'] + r'\*') # listpath is a list of strings, each string is a path of an excel file
        for path in listpath:
            try:
                if path.casefold().find('(') == -1:
                    # Extract:
                    spxtransac = extractorclasses.ExcelExtractor(
                        'SPX Express',
                        path,
                        configinfo['transaction_spx']['excel']['usecols'],
                        configinfo['transaction_spx']['excel']['usedtype'],
                        0,
                        configinfo['transaction_spx']['excel']['check_filepath']
                    )
                    df_spxtransac = spxtransac.extractdata()
                    # Clean:
                    cleanspxtransac = cleanerclasses.TransactionsSPXExcelCleaner(
                        configinfo['transaction_spx']['excel']['finalcols'],
                        df_spxtransac
                    )
                    df_spxtransac = cleanspxtransac.cleandata()
                    df_spxtransac = cleanerclasses.cleandatetime_df(
                        df_spxtransac,
                        {'Thời gian giao dịch':'%Y/%m/%d %H:%M:%S'},
                        to_datetime_param='format'
                    )
                    # Upload:
                    loadspxtransac = loaderclasses.DataframeToDatabaseLoader(
                        df_spxtransac,
                        sqlconnection,
                        etltolake_query['delivery_reconciliation'],
                        currenttime
                    )
                    loadspxtransac.loaddata()
                    print(f"orchestrator: run_spxtransactions_exceletl: the whole ETL for the {path} filepath has run successfully!{successdash}")
                else:
                    raise warnings.warn(f"The file path {path} contains '(' characters, data in this file won't be upload on database!{faileddash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_spxtransactions_exceletl: the ETL pipeline for the {path} filepath has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_ghntransactions_exceletl(sqlconnection):
    if configinfo['transaction_ghn']['excel']['folderpath'] is None:
        warnings.warn(f"orchestrator: run_ghntransactions_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
    else:
        listpath = glob.glob(configinfo['transaction_ghn']['excel']['folderpath'] + r'\*')  # listpath is a list of strings, each string is a path of an excel file
        for path in listpath:
            try:
                if path.casefold().find('(') == -1:
                    # Extract:
                    infodf = pd.read_excel(path, header=None, usecols='A:B', skiprows=7, nrows=2)
                    ma_gd = infodf.loc[0,1]
                    ngay_gd = infodf.loc[1,1]
                    ghntransac = extractorclasses.ExcelExtractor(
                        'Giao Hang Nhanh',
                        path,
                        configinfo['transaction_ghn']['excel']['usecols'],
                        configinfo['transaction_ghn']['excel']['usedtype'],
                        20,
                        configinfo['transaction_ghn']['excel']['check_filepath']
                    )
                    df_ghntransac = ghntransac.extractdata()
                    # Clean:
                    cleanghntransac = cleanerclasses.TransactionsGHNExcelCleaner(
                        configinfo['transaction_ghn']['excel']['finalcols'],
                        df_ghntransac,
                        ma_gd,
                        ngay_gd
                    )
                    df_ghntransac = cleanghntransac.cleandata()
                    # Upload:
                    loadghntransac = loaderclasses.DataframeToDatabaseLoader(
                        df_ghntransac,
                        sqlconnection,
                        etltolake_query['delivery_reconciliation'],
                        currenttime
                    )
                    loadghntransac.loaddata()
                    print(f"orchestrator: run_ghntransactions_exceletl: the whole ETL for the {path} filepath has run successfully!{successdash}")
                else:
                    raise warnings.warn(f"The file path {path} contains '(' characters, data in this file won't be upload on database!{faileddash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_ghntransactions_exceletl: the ETL pipeline for the {path} filepath has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_ghncointransactions_exceletl(sqlconnection):
    if configinfo['cointransaction_ghn']['excel']['folderpath'] is None:
        warnings.warn("orchestrator: run_ghncointransactions_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
    else:
        listpath = glob.glob(configinfo['cointransaction_ghn']['excel']['folderpath'] + r'\*')  # listpath is a list of strings, each string is a path of an excel file
        for path in listpath:
            try:
                if path.casefold().find('(') == -1:
                    # Extract:
                    ghncointransac = extractorclasses.ExcelExtractor(
                        'Giao Hang Nhanh',
                        path,
                        configinfo['cointransaction_ghn']['excel']['usecols'],
                        configinfo['cointransaction_ghn']['excel']['usedtype'],
                        2,
                        configinfo['cointransaction_ghn']['excel']['check_filepath']
                    )
                    df_ghncointransac = ghncointransac.extractdata()
                    # Clean:
                    cleanghncointransac = cleanerclasses.CoinTransactionsGHNExcelCleaner(
                        configinfo['cointransaction_ghn']['excel']['finalcols'],
                        df_ghncointransac
                    )
                    df_ghncointransac = cleanghncointransac.cleandata()
                    # Upload:
                    loadghncointrans = loaderclasses.DataframeToDatabaseLoader(
                        df_ghncointransac,
                        sqlconnection,
                        etltolake_query['delivery_reconciliation'],
                        currenttime
                    )
                    loadghncointrans.loaddata()
                    print(f"orchestrator: run_ghncointransactions_exceletl: the whole ETL for the {path} filepath has run successfully!{successdash}")
                else:
                    raise warnings.warn(f"The file path {path} contains '(' characters, data in this file won't be upload on database!{faileddash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_ghncointransactions_exceletl: the ETL pipeline for the {path} filepath has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_nhanhvn_apietl(sqlconnection):
    try:
        run_sqlscript(
            DELETERECORDS_NHANHVN_QUERYPATH,
            sqlconnection,
            params={'startdate': configinfo['nhanhvn']['api']['orders']['startdate'], 'enddate': configinfo['nhanhvn']['api']['orders']['enddate']}
        )
    except:
        warnings.warn(f"orchestrator: run_nhanhvn_apietl: the queries to delete reocrds have failed! Stop this pipeline{faileddash}")
    else:
        for nhanhvnacc in secretinfo['nhanhvn']['account'].values():
            try:
                appid = nhanhvnacc['appid']
                businessid = nhanhvnacc['businessid']
                accesstoken = nhanhvnacc['accesstoken']
                # Extract:
                print(f"orchestrator: run_nhanhvn_apietl: retrieve orders and orderdetails data from Nhanhvn Open API")
                nhanh = extractorclasses.NhanhvnOrdersAPIExtractor(
                    'https://pos.open.nhanh.vn/v3.0/order/list',
                    {'appId': appid, 'businessId': businessid},
                    {'Authorization': accesstoken, 'Content-Type': 'application/json'},
                    configinfo['nhanhvn']['api']['orders']['startdate'],
                    configinfo['nhanhvn']['api']['orders']['enddate'],
                    salechannel=[1, 10]
                )
                json_nhanh = nhanh.extractdata()
                # Clean:
                print(f"orchestrator: run_nhanhvn_apietl: clean orders and orderdetails data from Nhanhvn Open API")
                cleannhanh = cleanerclasses.OrdersNhanhvnAPICleaner(
                    configinfo['nhanhvn']['api']['orders']['orderfinalcols'],
                    configinfo['nhanhvn']['api']['orders']['orderdetailfinalcols'],
                    json_nhanh
                )
                df_orders = cleannhanh.cleandata()
                df_orderdetails = cleannhanh.cleandata_orderdetails()
                df_orders = cleanerclasses.cleandatetime_df(
                    df_orders,
                    {'Thoi gian':'s', 'Ngay gui HVC':'s'},
                    to_datetime_param='unit'
                )
                opensheet = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
                orderstatus_des = opensheet.extractlist(
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idfile'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idsheet'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['orderstatus']['datarange']
                )
                cleanerclasses.map_valuedf(df_orders, 'Trang thai', orderstatus_des)
                salechannel_des = opensheet.extractlist(
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idfile'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idsheet'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['salechannel']['datarange']
                )
                cleanerclasses.map_valuedf(df_orders, 'Nen tang', salechannel_des)
                cityaddress_des = opensheet.extractlist(
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idfile'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idsheet'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['cityaddress']['datarange']
                )
                cleanerclasses.map_valuedf(df_orders, 'Thanh pho', cityaddress_des)
                districtaddress_des = opensheet.extractlist(
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idfile'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['idsheet'],
                    configinfo['nhanhvn']['api']['orders']['codeexplain']['districtaddress']['datarange']
                )
                cleanerclasses.map_valuedf(df_orders, 'Quan huyen', districtaddress_des)
                # Upload:
                print(f"orchestrator: run_nhanhvn_apietl: upload orders and orderdetails data from Nhanhvn Open API to datalake")
                loadorders = loaderclasses.DataframeToDatabaseLoader(
                    df_orders,
                    sqlconnection,
                    etltolake_query['nhanhvnorders'],
                    currenttime
                )
                loadorders.loaddata()
                loadorderdetails = loaderclasses.DataframeToDatabaseLoader(
                    df_orderdetails,
                    sqlconnection,
                    etltolake_query['nhanhvnorderdetails'],
                    currenttime
                )
                loadorderdetails.loaddata()
                print(f"orchestrator: run_nhanhvn_apietl: the whole ETL has run successfully!{successdash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_nhanhvn_apietl: the ETL pipeline for {nhanhvnacc.get('appid', 'WRONG AT CONFIG')} appid has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def run_tiktokincome_exceletl(sqlconnection):
    if configinfo['tiktok']['excel']['income']['folderpath'] is None:
        warnings.warn(f"orchestrator: run_tiktokincome_exceletl: the file path is None. There is nothing to load to datalake{faileddash}")
    else:
        listpath = glob.glob(configinfo['tiktok']['excel']['income']['folderpath'] + r'\*')  # listpath is a list of strings, each string is a path of an excel file
        for path in listpath:
            try:
                # Extract:
                tiktokincome = extractorclasses.ExcelExtractor(
                    'Tiktok shops',
                    path,
                    configinfo['tiktok']['excel']['income']['finalcols'],
                    configinfo['tiktok']['excel']['income']['usedtype'],
                    0,
                    ['']
                )
                df_tiktokincome = tiktokincome.extractdata()
                # Clean:
                cleantiktokincome = cleanerclasses.IncomeTiktokExcelCleaner(
                    configinfo['tiktok']['excel']['income']['finalcols'],
                    df_tiktokincome
                )
                df_tiktokincome = cleantiktokincome.cleandata()
                df_tiktokincome = cleanerclasses.cleandatetime_df(
                    df_tiktokincome,
                    {'Thời gian quyết toán đơn hàng': '%Y/%m/%d'},
                    to_datetime_param='format'
                )
                # Upload:
                loadtiktokincome = loaderclasses.DataframeToDatabaseLoader(
                    df_tiktokincome,
                    sqlconnection,
                    etltolake_query['tiktok_reconciliation'],
                    currenttime
                )
                loadtiktokincome.loaddata()
                print(f"orchestrator: run_tiktokincome_exceletl: the whole ETL for the {path} filepath has run successfully!{successdash}")
            except Exception as e:
                warnings.warn(f"orchestrator: run_tiktokincome_exceletl: the ETL pipeline for the {path} filepath has failed. Data have not been loaded to datalake. Error message:\n{e}{faileddash}")


def updatereport_googlesheet(sqlconnection):
    updateinfo_object = extractorclasses.GoogleSheetExtractor(GGSERVICEKEY)
    updateinfo = updateinfo_object.extractlist(configinfo['updatereport_ggsheet']['googlesheet']['idfile'], configinfo['updatereport_ggsheet']['googlesheet']['idsheet'], 'A2:F')
    for report in updateinfo:
        try:
            if report[4] == 'YES':
                worksheet_report = updateinfo_object.extractsheet(report[1], report[2])
                sheetloader = loaderclasses.DatabaseToSheetLoader(
                    sqlconnection,
                    report[5].format(**configinfo['updatereport_ggsheet']['params']),
                    worksheet_report,
                    report[3]
                )
                sheetloader.loaddata()
                print(f"orchestrator: updatereport_googlesheet: successfully updated the report: '{report[0]}'{successdash}")
            else:
                continue
        except Exception as e:
            warnings.warn(f"orchestrator: updatereport_googlesheet: failed updated the report: '{report[0]}', error message:\n{e}{faileddash}")