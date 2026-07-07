from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from unidecode import unidecode
import warnings


# append_iferror() function:
def append_iferror(append_list: list,
                  origin_dict: dict,
                  list_of_paths: list[str],
                  iferrorvalue=None):
    """
    Purpose: If the value return error, append the append_list with iferrorvalue value
    :param append_list: the list want to append
    :param origin_dict: you find the value in this dictionary
    :param list_of_paths: a list containing str, this is the path which you used to find the value in the origin_dict
    :param iferrorvalue: when value return error, this value will be appended in the append_list
    :return: None
    """
    try:
        value = origin_dict
        for i in list_of_paths:
            value = value[i]
    except:
        value = iferrorvalue
    append_list.append(value)


# map_valuedf() function:
def map_valuedf(df: pd.DataFrame,
                col_name: str,
                mapping_list: list[list]):
    """
    Purpose: Replace values in a column
    :param df: a dataframe, containing a column you want to replace values
    :param col_name: a string, the column name you want to replace values
    :param mapping_list: a list of lists, each list containing 2 values, corresponding are: [original value, new value]. Example: [[1,'Ha Noi'], [2,'Thai Nguyen'], [3,'Phu Tho'], [4,'Yen Bai'], [5,'Bac Ninh']]
    :return: None
    """
    mapping_dict = dict(mapping_list)
    df[col_name] = df[col_name].map(mapping_dict)


# DatetimeCleaner function:
def cleandatetime_df(df, columns: dict[str,str], *, to_datetime_param='format') -> pd.DataFrame:
    """
    Purpose: convert int64 or object datatype column(s) of a dataframe into datetime datatype column
    :param df: the dataframe needed to convert datatype
    :param columns: a dictionary with keys are strings showing column name that needed to convert datatype, values are strings showing format of original data format in that column. Examples: {'Thời gian tạo đơn':'%Y-%m-%d %H:%M:%S'} or {'Created_time':'s'}
    :param to_datetime_param: accept only 'format' or 'unit', using 'format' when original columns contain string values showing day-month-year, using 'unit' when original columns contain integer values showing unix timestamp
    :return: a dataframe
    """
    for col, type in columns.items():
        if to_datetime_param=='unit':
            df[col] = pd.to_datetime(df[col], unit=type, utc=True).dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)
        else:
            df[col] = pd.to_datetime(df[col], format=type)
    return df


# Cleaner interface:
class Cleaner(ABC):
    @abstractmethod
    def cleandata(self):
        pass


# DeliveryOrdersGHTKExcelCleaner class:
class DeliveryOrdersGHTKExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df_deliveryorders: pd.DataFrame,
                 df_paymentminutes: pd.DataFrame,
                 listfee_paymentminutes: list[str],
                 df_canceledorders: pd.DataFrame = None,
                 df_compensations: pd.DataFrame = None):
        """
        Purpose: clean GHTK orders data from excel files
        :param finalcolumns: a list containing strings showing column names of the dataframe after using cleandata() method
        :param df_deliveryorders: a dataframe containing delivery orders data of GHTK
        :param df_paymentminutes: a dataframe containing payment of minutes data of GHTK
        :param listfee_paymentminutes: a list of strings, containing column names of fee in df_paymentminutes dataframe
        :param df_canceledorders: a dataframe containing canceled orders data of GHTK
        :param df_compensations: a dataframe containing compensation orders data of GHTK
        """
        self.finalcolumns = finalcolumns
        self.df_deliveryorders = df_deliveryorders
        self.df_paymentminutes = df_paymentminutes
        self.listfee_paymentminutes = listfee_paymentminutes
        self.df_canceledorders = df_canceledorders
        self.df_compensations = df_compensations
    def cleandata(self):
        # Concat df_deliveryorders dataframe and df_canceledorders dataframe into 1 dataframe:
        if self.df_canceledorders is not None:
            self.df_canceledorders['Trạng thái đơn hàng'] = 'Don huy'
            self.df_deliveryorders = pd.concat([self.df_deliveryorders, self.df_canceledorders], axis=0)
        # Clean the 'Mã ĐH' column:
        self.df_deliveryorders['Mã ĐH'] = self.df_deliveryorders['Mã ĐH'].str[-10:]
        check = self.df_deliveryorders[self.df_deliveryorders['Mã ĐH'].str.contains(r'[A-Za-z]', na=True)]
        if len(check) > 0:
            print(check['Mã ĐH'])
            raise ValueError("Existing values in 'Mã ĐH' column of the df_deliveryorders that's not 10 digits format")
        if self.df_compensations is not None:
            # Merge the df_deliveryorders and df_compensations into 1 dataframe:
            self.df_compensations['Mã đơn hàng'] = self.df_compensations['Mã đơn hàng'].str[-10:]
            check = self.df_compensations[self.df_compensations['Mã đơn hàng'].str.contains(r'[A-Za-z]', na=True)]
            if len(check) > 0:
                print(check['Mã đơn hàng'])
                raise ValueError("Existing values in 'Mã đơn hàng' column of the df_compensations that's not 10 digits format")
            self.df_deliveryorders = pd.merge(self.df_deliveryorders, self.df_compensations, left_on='Mã ĐH', right_on='Mã đơn hàng', how='left')
            # Clean data from 'compensation' records:
            self.df_deliveryorders = self.df_deliveryorders.drop('Mã đơn hàng', axis='columns')
            if len(self.df_deliveryorders[self.df_deliveryorders['Tiền bồi hoàn']<=0]) > 0:
                raise ValueError("The 'Tiền bồi hoàn' of some GHTK orders are less than or equals to 0!")
            self.df_deliveryorders.loc[self.df_deliveryorders['Tiền bồi hoàn']>0, 'Trạng thái đơn hàng'] = 'Boi hoan'
            self.df_deliveryorders.loc[self.df_deliveryorders['Tiền bồi hoàn'].isna(), 'Tiền bồi hoàn'] = 0
        else:
            self.df_deliveryorders['Tiền bồi hoàn'] = 0
        # Clean the 'Mã đơn hàng' column of the df_paymentminutes dataframe:
        self.df_paymentminutes = self.df_paymentminutes[self.df_paymentminutes['STT'].apply(lambda x: isinstance(x, int))]
        self.df_paymentminutes['Mã đơn hàng'] = self.df_paymentminutes['Mã đơn hàng'].str[-10:]
        check = self.df_paymentminutes[self.df_paymentminutes['Mã đơn hàng'].str.contains(r'[A-Za-z]', na=True)]
        if len(check) > 0:
            print(check['Mã đơn hàng'])
            raise ValueError("Existing values in 'Mã đơn hàng' column of the df_paymentminutes that's not 10 digits format")
        # Calculate the 'Tổng vận phí' column in the df_paymentminutes dataframe:
        for i in self.listfee_paymentminutes:
            self.df_paymentminutes[i] = self.df_paymentminutes[i].fillna(0)
            self.df_paymentminutes[i] = self.df_paymentminutes[i].astype('int64')
            if self.df_paymentminutes[i].dtype != 'int64':
                warnings.warn(f"The {i} column in the GHTK df_paymentminutes contains non-numeric values, these values will be converted to 0 values")
                self.df_paymentminutes[i] = pd.to_numeric(self.df_paymentminutes[i], errors='coerce')
                self.df_paymentminutes[i] = self.df_paymentminutes[i].fillna(0)
                self.df_paymentminutes[i] = self.df_paymentminutes[i].astype('int64')
        self.df_paymentminutes['Tổng vận phí'] = self.df_paymentminutes[self.listfee_paymentminutes].sum(axis=1)
        self.df_paymentminutes['Tổng vận phí'] = self.df_paymentminutes['Tổng vận phí'] * (-1)
        self.df_paymentminutes = self.df_paymentminutes.drop(self.listfee_paymentminutes, axis='columns')
        # Merge the df_deliveryorders and df_paymentminutes into 1 dataframe:
        self.df_deliveryorders = pd.merge(self.df_deliveryorders, self.df_paymentminutes, left_on='Mã ĐH', right_on='Mã đơn hàng', how='left') # If an order exists in df_deliveryorders but doesn't exist in df_paymentminutes, the 'Tổng vận phí' = np.nan
        # Clean the 'Trạng thái đơn hàng' column:
        self.df_deliveryorders['Trạng thái đơn hàng'] = self.df_deliveryorders['Trạng thái đơn hàng'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        # Choose only necessary columns:
        self.df_deliveryorders = self.df_deliveryorders[self.finalcolumns]
        return self.df_deliveryorders


# DeliveryOrdersGHNExcelCleaner class:
class DeliveryOrdersGHNExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df_deliveryorders: pd.DataFrame,
                 df_cointransactions: pd.DataFrame):
        """
        Purpose: clean GHN orders data from excel files
        :param finalcolumns: a list containing strings showing column names of the dataframe after using cleandata() method
        :param df_deliveryorders: a dataframe containing delivery orders data of GHN
        :param df_cointransactions: a dataframe containing delivery coin transaction data of GHN
        """
        self.finalcolumns = finalcolumns
        self.df_deliveryorders = df_deliveryorders
        self.df_cointransactions = df_cointransactions
    def cleandata(self):
        # Clean the df_cointransactions:
        self.df_cointransactions = self.df_cointransactions[self.df_cointransactions['Loại giao dịch'] == 'Đền bù hoặc chiết khấu']
        self.df_cointransactions.loc[self.df_cointransactions['Nội dung'].str.endswith('_PR'), 'Nội dung'] = self.df_cointransactions['Nội dung'].str[:-3]
        check = self.df_cointransactions[~self.df_cointransactions['Số tiền'].apply(lambda x: isinstance(x, int))]
        if len(check) > 0:
            raise ValueError("Detect records where the value of the 'Số tiền' column in the df_cointransactions is not interger")
        self.df_cointransactions = self.df_cointransactions.groupby('Nội dung', as_index=False)['Số tiền'].sum()
        # Drop virtual returning order IDs (that 3 last characters in order ID are "_PR") in df_deliveryorders:
        self.df_deliveryorders = self.df_deliveryorders[~self.df_deliveryorders['Mã đơn hàng'].str.endswith("_PR")]
        # Clean the 'Ngày giao hàng thành công' column in df_deliveryorders:
        self.df_deliveryorders.loc[self.df_deliveryorders['Ngày giao hàng thành công'].isna(), 'Ngày giao hàng thành công'] = self.df_deliveryorders['Ngày giao hàng lần đầu']
        for col in ['Tổng phí dịch vụ', 'Phí hoàn hàng', 'Tiền COD', 'GTB - Thu tiền']:
            if len(self.df_deliveryorders[self.df_deliveryorders[col].isna()]):
                raise TypeError(f'The {col} column in the df_deliveryorders of GHN contains NaN values')
        # Calculate the 'Tổng vận phí' column in df_deliveryorders:
        for i in ['Tổng phí dịch vụ', 'Phí hoàn hàng']:
            if self.df_deliveryorders[i].dtype != 'int64':
                warnings.warn(f"The {i} column in the GHN df_deliveryorders contains non-numeric values, these values will be converted to 0 values")
                self.df_deliveryorders[i] = pd.to_numeric(self.df_deliveryorders[i], errors='coerce')
                self.df_deliveryorders[i] = self.df_deliveryorders[i].fillna(0)
                self.df_deliveryorders[i] = self.df_deliveryorders[i].astype('int64')
        self.df_deliveryorders['Tổng vận phí'] = self.df_deliveryorders['Tổng phí dịch vụ'] + self.df_deliveryorders['Phí hoàn hàng']
        # Calculate the 'Tiền bồi hoàn' column in df_deliveryorders:
        self.df_deliveryorders['Tiền bồi hoàn'] = 0
        # Calculate the real 'Tiền COD' column in df_deliveryorders:
        self.df_deliveryorders.loc[self.df_deliveryorders['Ngày thu GTB - thu tiền'].isna(), 'Tiền COD'] = self.df_deliveryorders['Tiền COD']
        self.df_deliveryorders.loc[~self.df_deliveryorders['Ngày thu GTB - thu tiền'].isna(), 'Tiền COD'] = self.df_deliveryorders['Tiền COD'] + self.df_deliveryorders['GTB - Thu tiền']
        # The df_deliveryorders left join df_cointransactions, to take 'Đền bù hoặc chiết khấu' data from the df_cointransactions:
        self.df_deliveryorders = pd.merge(self.df_deliveryorders, self.df_cointransactions, left_on='Mã đơn hàng', right_on='Nội dung', how='left')
        self.df_deliveryorders.loc[self.df_deliveryorders['Trạng thái']=='Hàng thất lạc', 'Tiền COD'] = 0
        self.df_deliveryorders.loc[(self.df_deliveryorders['Trạng thái'] != 'Hàng thất lạc') & (self.df_deliveryorders['Số tiền'].notna()), 'Tiền COD'] = self.df_deliveryorders['Tiền COD'] + self.df_deliveryorders['Số tiền']
        self.df_deliveryorders.loc[(self.df_deliveryorders['Trạng thái'] == 'Hàng thất lạc') & (self.df_deliveryorders['Số tiền'].notna()), 'Tiền bồi hoàn'] = self.df_deliveryorders['Số tiền']
        # Clean the 'Trạng thái' column:
        self.df_deliveryorders['Trạng thái'] = self.df_deliveryorders['Trạng thái'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        # Choose only necessary columns:
        self.df_deliveryorders = self.df_deliveryorders[self.finalcolumns]
        return self.df_deliveryorders


# DeliveryOrdersJTEExcelCleaner class:
class DeliveryOrdersJTEExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df_deliveryorders: pd.DataFrame):
        """
        Purpose: clean JTE orders data from an excel file
        :param finalcolumns: a list containing strings showing column names of the dataframe after using cleandata() method
        :param df_deliveryorders: a dataframe containing delivery orders data of JTE
        """
        self.finalcolumns = finalcolumns
        self.df_deliveryorders = df_deliveryorders
    def cleandata(self):
        # Calculate the 'Tiền bồi hoàn' column:
        self.df_deliveryorders['Tiền bồi hoàn'] = 0
        # Calculate the 'Tổng vận phí' column:
        for col in ['Cước phí', 'Phí lưu kho']:
            self.df_deliveryorders[col] = self.df_deliveryorders[col].fillna(0)
            self.df_deliveryorders[col] = self.df_deliveryorders[col].astype('int64')
        self.df_deliveryorders['Tổng vận phí'] = self.df_deliveryorders['Cước phí'] + self.df_deliveryorders['Phí lưu kho']
        # Clean the 'Trạng thái vận đơn' column:
        self.df_deliveryorders['Trạng thái vận đơn'] = self.df_deliveryorders['Trạng thái vận đơn'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        # Choose only necessary columns:
        self.df_deliveryorders = self.df_deliveryorders[self.finalcolumns]
        return self.df_deliveryorders


# DeliveryOrdersSPXExcelCleaner class:
class DeliveryOrdersSPXExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df_deliveryorders: pd.DataFrame):
        """
        Purpose: clean SPX orders data from an excel file
        :param finalcolumns: a list containing strings showing column names of the dataframe after using cleandata() method.
        :param df_deliveryorders: a dataframe containing delivery orders data of SPX.
        """
        self.finalcolumns = finalcolumns
        self.df_deliveryorders = df_deliveryorders
    def cleandata(self):
        # Check whether unexpected values exists in 'Số tiền COD', 'Giá trị đơn hàng', 'Phí vận chuyển thực tế':
        for col in ['Số tiền COD', 'Giá trị đơn hàng', 'Phí vận chuyển thực tế']:
            if self.df_deliveryorders[col].dtype != 'int64':
                warnings.warn(f"The {col} column in the SPX df_deliveryorders contains non-numeric values, these values will be converted to NaN values")
                self.df_deliveryorders[col] = pd.to_numeric(self.df_deliveryorders[col], errors='coerce')
            check = self.df_deliveryorders.loc[((self.df_deliveryorders[col]<3000)&(self.df_deliveryorders[col]!=0)) | (self.df_deliveryorders[col]>1000000000), ['Mã vận đơn', col]]
            if len(check) > 0:
                warnings.warn(f"The {col} column in the SPX df_deliveryorders contains values that less than 3000 (<>0) or more than 1000000000, see these values in following:\n{check}\nThese values will still be uploaded on database.")
        # Briefly clean the 'Thời gian tạo đơn', 'Thời gian lấy hàng/gửi hàng', 'Thời gian giao hàng' columns:
        for col in ['Thời gian tạo đơn', 'Thời gian lấy hàng/gửi hàng', 'Thời gian giao hàng']:
            self.df_deliveryorders[col] = self.df_deliveryorders[col].replace('-', np.nan)
        # Create the 'Mã ĐH Shop' and 'Tiền bồi hoàn' column:
        self.df_deliveryorders['Mã ĐH Shop'] = np.nan
        self.df_deliveryorders['Tiền bồi hoàn'] = 0
        # Clean the 'Trạng thái hiện tại' column:
        self.df_deliveryorders['Trạng thái hiện tại'] = self.df_deliveryorders['Trạng thái hiện tại'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        # Choose only necessary columns:
        self.df_deliveryorders = self.df_deliveryorders[self.finalcolumns]
        return self.df_deliveryorders


# OrdersNhanhvnAPICleaner class:
class OrdersNhanhvnAPICleaner(Cleaner):
    def __init__(self,
                 orders_finalcols: list[str],
                 orderdetails_finalcols: list[str],
                 orderslist: list[dict]):
        """
        Convert json data from Nhanhvnorders_APIExtractor class into a dataframe.
        :param orders_finalcols: a list of strings, containing column names of the final dataframe after applying the cleandata() method.
        :param orderdetails_finalcols: a list of strings, containing column names of the final dataframe after applying the cleandata_orderdetails() method.
        :param orderslist: a list of dictionaries, each dictionary showing information of an order.
        """
        if isinstance(orderslist, list):
            pass
        else:
            raise TypeError("The orderslist parameter must be a list")
        self.orders_finalcols = orders_finalcols
        self.orderdetails_finalcols = orderdetails_finalcols
        self.orderslist = orderslist
    def cleandata(self):
        # Convert the nested list into a dataframe:
        all_record = []
        for order in self.orderslist: #order is a dictionary
            record = []
            append_iferror(record, order, ['info', 'id'])
            append_iferror(record, order, ['info', 'createdAt'])
            append_iferror(record, order, ['shippingAddress', 'name'])
            append_iferror(record, order, ['shippingAddress', 'mobile'])
            append_iferror(record, order, ['shippingAddress', 'cityId'])
            append_iferror(record, order, ['shippingAddress', 'districtId'])
            append_iferror(record, order, ['carrier', 'name'])
            append_iferror(record, order, ['carrier', 'carrierCode'])
            append_iferror(record, order, ['info', 'status'])
            append_iferror(record, order, ['channel', 'trafficSource'])
            append_iferror(record, order, ['channel', 'saleChannel'])
            append_iferror(record, order, ['carrier', 'sendCarrierAt']) # If an order haven't been sent to a delivery yet, this returns 0 value (integer). I have converted these 0 values into NaN values in dataframe at below code
            append_iferror(record, order, ['payment', 'transfer', 'amount'], 0)
            append_iferror(record, order, ['payment', 'deposit', 'amount'], 0)
            append_iferror(record, order, ['info', 'privateDescription'])
            append_iferror(record, order, ['info', 'description'])
            append_iferror(record, order, ['info', 'createdByName'])
            all_record.append(record)
        NhanhAPIcolumns = [
            'ID',
            'Thoi gian',
            'Ten khach hang',
            'So dien thoai',
            'Thanh pho',
            'Quan huyen',
            'Hang van chuyen',
            'Ma don hang van chuyen',
            'Trang thai',
            'Nguon don hang',
            'Nen tang',
            'Ngay gui HVC',
            'Tien chuyen khoan',
            'Tien dat coc',
            'Ghi chu noi bo',
            'Ghi chu cua khach',
            'Nguoi tao don'
        ]
        df = pd.DataFrame(all_record, columns=NhanhAPIcolumns)
        # Lower all string values and convert diacritic Vietnamese values into non-diacritic values:
        object_cols = ['Ten khach hang', 'So dien thoai', 'Hang van chuyen', 'Nguon don hang', 'Ghi chu noi bo', 'Ghi chu cua khach', 'Nguoi tao don']
        for col in object_cols:
            non_str = df[df[col].apply(lambda x: not isinstance(x, str) and x is not None and not pd.isna(x))][[col]]
            if len(non_str) > 0:
                warnings.warn(f'The {col} column of the dataframe inside the OrdersNhanhvnAPICleaner class containing non-string and non-None values. All those values have been converted to NaN values:\n{non_str}')
            df[col] = df[col].str.lower()
            df[col] = df[col].apply(lambda x: unidecode(x) if isinstance(x, str) else x)
        # Convert values in some columns into str datatype:
        for col in ['Thanh pho', 'Quan huyen', 'Trang thai', 'Nen tang', 'ID']:
            df[col] = df[col].astype('str')
        # Clean the 'Ngay gui HVC' column:
        df['Ngay gui HVC'] = df['Ngay gui HVC'].replace(0, np.nan)
        # Create the 'Nguon don hang cha' and 'Nguon don hang con' columns:
        df['Nguon don hang cha'] = 'di moi'
        df.loc[df['Nguon don hang'].str.endswith('don doi', na=False), 'Nguon don hang cha'] = 'don doi'
        df.loc[df['Nguon don hang'].str.endswith('bo sung', na=False), 'Nguon don hang cha'] = 'bo sung'
        df.loc[df['Nguon don hang'].str.endswith('len lai', na=False), 'Nguon don hang cha'] = 'len lai'
        df.loc[df['Nguon don hang'].str.endswith('don tach', na=False), 'Nguon don hang cha'] = 'don tach'
        df.loc[df['Nguon don hang cha'] == 'di moi', 'Nguon don hang con'] = df.loc[df['Nguon don hang cha'] == 'di moi', 'Nguon don hang']
        df.loc[df['Nguon don hang cha'] != 'di moi', 'Nguon don hang con'] = df.loc[df['Nguon don hang cha'] != 'di moi', 'Nguon don hang'].str.rsplit('-', n=1).str[0]
        df['Nguon don hang con'] = df['Nguon don hang con'].str.strip()
        # Create the 'COD tra truoc' column:
        df['COD tra truoc'] = df['Tien dat coc'] + df['Tien chuyen khoan']
        # Create the 'previous_ID ghi chu noi bo' column:
        df['previous_ID ghi chu noi bo'] = df['Ghi chu noi bo'].str.extract(r'(\b\d{9}\b)')
        # Create the 'previous_ID ghi chu cua khach' column:
        df['previous_ID ghi chu cua khach'] = df['Ghi chu cua khach'].str.extract(r'(mdu[1-9]{4})')
        df['previous_ID ghi chu cua khach'] = df['previous_ID ghi chu cua khach'].str.upper()
        # Create the 'Di lech ma' column:
        df['Di lech ma'] = False
        df.loc[df['Ghi chu noi bo'].str.contains(r'DI\s*=\s*[a-zA-Z]{3}', case=False, na=False), 'Di lech ma'] = True
        # Clean the 'Ghi chu noi bo' and 'Ghi chu cua khach column':
        df.loc[df['Ghi chu noi bo'].str.len() > 255, 'Ghi chu noi bo'] = df.loc[df['Ghi chu noi bo'].str.len() > 255, 'Ghi chu noi bo'].str[0:254]
        df.loc[df['Ghi chu cua khach'].str.len() > 255, 'Ghi chu cua khach'] = df.loc[df['Ghi chu cua khach'].str.len() > 255, 'Ghi chu cua khach'].str[0:254]
        # Choose only necessary column:
        df = df[self.orders_finalcols]
        return df
    def cleandata_orderdetails(self):
        # Convert the nested list into a dataframe:
        record_allorderdetail = []
        for order in self.orderslist: #order is a dictionary
            productsoforder = order['products'] #productoforder is a list of dictionaries
            record_productsoforder = []
            for eachproductoforder in productsoforder:
                record = []
                append_iferror(record, eachproductoforder, ['code'], iferrorvalue='') # for products haven't been created in the Product tab, they don't have code key
                append_iferror(record, order, ['info', 'id'])
                append_iferror(record, eachproductoforder, ['barcode'])
                append_iferror(record, eachproductoforder, ['price'])
                append_iferror(record, eachproductoforder, ['discountAmount'])
                append_iferror(record, eachproductoforder, ['quantity'])
                record_productsoforder.append(record)
            for i in record_productsoforder:
                record_allorderdetail.append(i)
        orderdetailcols = [
            'Ma san pham',
            'ID',
            'Ma vach',
            'Gia',
            'Chiet khau toan bo san pham',
            'So luong'
        ]
        df = pd.DataFrame(data=record_allorderdetail, columns=orderdetailcols)
        # Convert values in some columns into str datatype:
        for col in ['ID']:
            df[col] = df[col].astype('str')
        # Clean the 'Ma san pham' column:
        df['Ma san pham'] = df['Ma san pham'].str.upper()
        # Create the 'Ma san pham cha' column:
        df['Ma san pham cha'] = df['Ma san pham'].str.split("-", expand=False).str[0]
        # Check values in int64 datatype columns:
        int_cols = ['Gia', 'Chiet khau toan bo san pham', 'So luong']
        for col in int_cols:
            non_int = df[col].apply(lambda x: isinstance(x, str)).any()
            if non_int == True:
                warnings.warn(f'The {col} column of the dataframe inside the OrdersNhanhvnAPICleaner class containing string values. These values will be converted to 0 upon uploading on database in MySQL server (xampp). If you use another DBMS, be careful!')
        # Choose only necessary column:
        df = df[self.orderdetails_finalcols]
        return df


# TransactionsJTEExcelCleaner class:
class TransactionsJTEExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame):
        """
        Clean JT Express transactions data of a dataframe from an excel file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: a dataframe, containing at least 3 columns: 'Mã vận đơn' (object), 'Kỳ thanh toán' (object), 'Tiền thực nhận' (int64)
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        self.df = self.df[self.df['Mã vận đơn']!='Tổng cộng']
        # Group all records by 'Mã vận đơn' and 'Kỳ thanh toán':
        non_int = self.df['Tiền thực nhận'].apply(lambda x: not isinstance(x, int)).any()
        if non_int==True:
            raise TypeError(f"The 'Tiền thực nhận' column of the {self.df.iloc[0,1]} transaction code contains non-integer values!")
        self.df = self.df.groupby(by=['Mã vận đơn', 'Kỳ thanh toán'], as_index=False).agg({'Tiền thực nhận':'sum'})
        # Calculate the 'Ngày thanh toán' column:
        try:
            self.df['Year_Kỳ thanh toán'] = self.df['Kỳ thanh toán'].str.split("-", expand=False).str[1]
            self.df['DayMonth_Kỳ thanh toán'] = self.df['Kỳ thanh toán'].str.split("-", expand=False).str[2]
            self.df['Ngày giao dịch'] = self.df['Year_Kỳ thanh toán'].str[0:4] + "-" + self.df['DayMonth_Kỳ thanh toán'].str[0:2] + "-" + self.df['DayMonth_Kỳ thanh toán'].str[2:]
            self.df['Ngày giao dịch'] = pd.to_datetime(self.df['Ngày giao dịch'], format='%Y-%m-%d') + pd.Timedelta(days=1)
        except:
            warnings.warn(f"The {self.df.iloc[0,1]} transaction code does not have format 'accountcode-YYYYMMDD-MMDD', the transaction date of all records in this transaction session will be set to equals to today!")
            self.df['Ngày giao dịch'] = pd.Timestamp.now(tz='UTC').tz_convert('Asia/Ho_Chi_Minh').date()
        # Add the 'Hãng vận chuyển' column:
        self.df['Hãng vận chuyển'] = 'JT Express'
        # Add the 'Nội dung giao dịch' column:
        self.df['Nội dung giao dịch'] = np.nan
        # Choose only neccesary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# TransactionsSPXExcelCleaner class:
class TransactionsSPXExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame):
        """
        Clean SPX transactions data of a dataframe from an excel file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: a dataframe, containing transaction data from an excel file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Eliminate records that don't have tracking number in the 'Mã vận đơn' column:
        self.df = self.df[self.df['Mã vận đơn'] != '-']
        # Check datatype of the 'Số tiền (VND)' column:
        if str(self.df['Số tiền (VND)'].dtype) != 'int64':
            raise ValueError("TransactionsSPXExcelCleaner class: the 'Số tiền (VND)' column doesn't have int64 datatype")
        # Check 'Mã giao dịch' column:
        check = self.df[self.df.duplicated(subset='Mã giao dịch', keep=False)][['Mã giao dịch']]
        if len(check) > 0:
            raise ValueError(f"TransactionsSPXExcelCleaner class: the 'Mã giao dịch' column contains duplicated values:\n{check}")
        # Add the 'Hãng vận chuyển' column:
        self.df['Hãng vận chuyển'] = 'SPX Express'
        # Add the 'Nội dung giao dịch' column:
        self.df['Nội dung giao dịch'] = np.nan
        # Choose only neccesary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# TransactionsGHNExcelCleaner class:
class TransactionsGHNExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame,
                 sessionid: str,
                 sessiondate: str):
        self.finalcolumns = finalcolumns
        self.df = df
        self.sessionid = sessionid
        self.sessiondate = sessiondate
    def cleandata(self):
        # Check the sessionid:
        if self.sessionid[:4] != 'COD_':
            raise ValueError(f"TransactionsGHNExcelCleaner class: 4 first characters of session ID in this file are not 'COD_'")
        else:
            self.df['Phiên'] = self.sessionid
            self.df['Ngày'] = self.sessiondate
        # Remove records that don't have order ID
        self.df = self.df[self.df['Mã đơn GHN'].notna()].copy()
        # Check whether the 'Mã đơn GHN' column contains any values which don't have NVSxxxxxxxxx (x is a digit in [0,9]) or Gaaaaaaa (a is a letter in [A,Z] or a digit in [0,9]):
        check = self.df[~self.df['Mã đơn GHN'].str.match(r'^(NVS\d{9}|G[a-z0-9]{7})$', case=False, na=False)][['Mã đơn GHN', 'Phiên']]
        if len(check) > 0:
            warnings.warn(f"TransactionsGHNExcelCleaner class: The dataframe containing order ID(s) doesn't have format 'NVSxxxxxxxxx' or 'Gaaaaaaa'. But these records will be still uploaded on the database:\n{check}")
        # Check whether the '(1) + (2) + (3) + (4) + (5)' column contains non-integer value(s):
        if str(self.df['(1) + (2) + (3) + (4) + (5)'].dtype) != 'int64':
            raise TypeError(f"TransactionsGHNExcelCleaner class: The '(1) + (2) + (3) + (4) + (5)' column of {self.df.loc[0, 'Phiên']} session contains non-integer value(s)")
        # Clean the 'Ngày' column:
        try:
            self.df['Ngày'] = pd.to_datetime(self.df['Ngày'], format='%d/%m/%Y')
        except:
            warnings.warn(f"TransactionsGHNExcelCleaner class: The 'Ngày' column of the dataframe containing values that can't be converted to datetimens64 with '%d/%m/%Y' format: {self.df.loc[0,'Ngày']}.\nThe transaction date of all records in {self.df.loc[0, 'Phiên']} session will be set to equals to today!")
            self.df['Ngày'] = pd.Timestamp.now(tz='UTC').tz_convert('Asia/Ho_Chi_Minh').date()
        # Group all records by 'Mã đơn GHN' and 'Phiên':
        self.df = self.df.groupby(by=['Mã đơn GHN', 'Phiên'], as_index=False).agg({'Ngày': 'min', '(1) + (2) + (3) + (4) + (5)': 'sum'})
        # Add the 'Hãng vận chuyển' column:
        self.df['Hãng vận chuyển'] = 'Giao Hàng Nhanh'
        # Add the 'Nội dung giao dịch' column:
        self.df['Nội dung giao dịch'] = np.nan
        # Choose only necessary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# CoinTransactionsGHNExcelCleaner class:
class CoinTransactionsGHNExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame):
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Trim the '_PR' character at the end of some order IDs:
        self.df.loc[self.df['Nội dung'].str.endswith('_PR'), 'Nội dung'] = self.df.loc[self.df['Nội dung'].str.endswith('_PR'), 'Nội dung'].str[:-3]
        # Check whether the 'Mã đơn GHN' column contains any values which don't have NVSxxxxxxxxx (x is a digit in [0,9]) or Gaaaaaaa (a is a letter in [A,Z] or a digit in [0,9]):
        check = self.df[~self.df['Nội dung'].str.match(r'^(NVS\d{9}|G[a-z0-9]{7})$', case=False, na=False)][['Nội dung', 'Ngày']]
        if len(check) > 0:
            warnings.warn(f"CoinTransactionsGHNExcelCleaner class: The dataframe containing order ID(s) doesn't have format 'NVSxxxxxxxxx' or 'Gaaaaaaa'. But these records will be still uploaded on the database:\n{check}")
        # Check whether the 'Số tiền' column contains non-integer value(s):
        if str(self.df['Số tiền'].dtype) != 'int64':
            raise TypeError(f"CoinTransactionsGHNExcelCleaner class: The 'Số tiền' column of dataframe (containing '{self.df.loc[0, 'Nội dung']}' order ID) contains non-integer value(s)")
        # Calculate the 'Mã giao dịch' column:
        self.df['Loại giao dịch'] = self.df['Loại giao dịch'].str.lower()
        self.df['Loại giao dịch'] = self.df['Loại giao dịch'].str.replace(r'[\n\t ]', '', regex=True)
        self.df['Loại giao dịch'] = self.df['Loại giao dịch'].apply(lambda x: unidecode(x) if isinstance(x, str) else x)
        self.df['Mã giao dịch'] = self.df['Ngày'].str[6:10]+"-"+self.df['Ngày'].str[3:5]+"-"+self.df['Ngày'].str[0:2]+" "+self.df['Ngày'].str[-5:]+"_"+self.df['Loại giao dịch']
        # Clean the 'Ngày' column:
        try:
            self.df['Ngày'] = pd.to_datetime(self.df['Ngày'], format='%d/%m/%Y %H:%M')
        except:
            warnings.warn(f"CoinTransactionsGHNExcelCleaner class: The 'Ngày' column of the dataframe containing values that can't be converted to datetimens64 with '%d/%m/%Y %H:%M' format.\nThe transaction date of all records in this session will be set to equals to today!")
            self.df['Ngày'] = pd.Timestamp.now(tz='UTC').tz_convert('Asia/Ho_Chi_Minh').date()
        # Group all records by 'Nội dung' and 'Mã giao dịch':
        self.df = self.df.groupby(by=['Nội dung', 'Mã giao dịch'], as_index=False).agg({'Ngày': 'min', 'Số tiền': 'sum'})
        # Add the 'Hãng vận chuyển' column:
        self.df['Hãng vận chuyển'] = 'Giao Hàng Nhanh'
        # Add the 'Nội dung giao dịch' column:
        self.df['Nội dung giao dịch'] = np.nan
        # Choose only necessary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# CustomerBankingAPICleaner class:
class CustomerBankingAPICleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df:pd.DataFrame):
        """
        Clean customer's bank transfering data from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing customer's bank transfering data that fetches from a googlesheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Clean the 'ID đơn hàng' column:
        self.df['ID đơn hàng'] = self.df['ID đơn hàng'].str.strip()
        self.df['ID đơn hàng'] = self.df['ID đơn hàng'].str.replace(r'[\n\t +-]', ',', regex=True)
        self.df['ID đơn hàng'] = self.df['ID đơn hàng'].str.replace(r'[,]+', ',', regex=True)
        self.df = self.df[(self.df['ID đơn hàng']!=',') & (self.df['ID đơn hàng']!='')].copy()
        # Check the ID column:
        check = self.df[~self.df['ID'].str.match(r'^KB_\d+$', na=False)][['ID', 'Ngày', 'ID đơn hàng']]
        if len(check) > 0:
            warnings.warn(f"The ID value of some records containing value that doesn't match the format 'KB_x', please check them in the google sheet file. These values won't be uploaded to the data warehouse:\n{check}")
            self.df = self.df[self.df['ID'].str.match(r'^KB_\d+$', na=False)]
        # Clean the 'Số tiền bank' column:
        self.df['Số tiền bank'] = self.df['Số tiền bank'].str.replace(r'[\n\t .đ$]', '', regex=True)
        self.df['Số tiền bank'] = self.df['Số tiền bank'].replace('', np.nan)
        self.df['Số tiền bank'] = self.df['Số tiền bank'].astype('float')
        self.df['Số tiền bank'] = self.df['Số tiền bank'].ffill()
        group = self.df['Số tiền bank'].ne(self.df['Số tiền bank'].shift()).cumsum()
        count_per_group = group.map(group.value_counts())
        self.df['Số tiền bank'] = self.df['Số tiền bank'] / count_per_group
        # Clean the 'Sđt khách bank' column:
        self.df.loc[self.df['Sđt khách bank'].str[0]!='0', 'Sđt khách bank'] = '0' + self.df.loc[self.df['Sđt khách bank'].str[0]!='0', 'Sđt khách bank']
        # Clean the 'Ghi chú' column:
        self.df.loc[self.df['Ghi chú'].str.len() > 255, 'Ghi chú'] = self.df.loc[self.df['Ghi chú'].str.len() > 255, 'Ghi chú'].str[0:254]
        # Convert empty strings to NaN values:
        for col in ['Ngày', 'ID đơn hàng', 'Sđt khách bank', 'Người xác nhận', 'Mã FT', 'Ghi chú']:
            self.df[col] = self.df[col].replace('', np.nan)
        # Choose only necessary column:
        self.df = self.df[self.finalcolumns]
        return self.df


# CodTvcAPICleaner class:
class CodTvcAPICleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[int],
                 df: pd.DataFrame):
        """
        Clean self-delivery data from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing self-delivery data that fetches from a googlesheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Calculate the 'Mã vận đơn' column:
        self.df['ID đơn'] = self.df['ID đơn'].str.replace(r'[\n\t ]', '', regex=True)
        self.df = self.df[(self.df['ID đơn']!='')&(self.df['STT']!='STT')].copy()
        check = self.df[~self.df['ID đơn'].str.match(r'^\d{9}$', na=False)][['ID đơn', 'Ngày lên', 'Sđt khách hàng']]
        if len(check) > 0:
            warnings.warn(f"Some order IDs doesn't match the format of 9 digits, please check them in the google sheet file. These values won't be uploaded to the data warehouse:\n{check}")
            self.df = self.df[self.df['ID đơn'].str.match(r'^\d{9}$', na=False)]
        self.df['Mã vận đơn'] = 'TVC_GGSHEET_' + self.df['ID đơn']
        # Calculate the 'Tổng Cod', 'Phí Ship', 'COD thu khách' column:
        for col in ['Tổng Cod', 'Phí Ship', 'Cod BANK', 'Cod Tiền mặt']:
            self.df[col] = self.df[col].str.replace(r'[\n\t .đ]', '', regex=True)
            self.df[col] = self.df[col].replace('', 0)
            self.df[col] = self.df[col].astype('int64')
        self.df['COD thu khách'] = self.df['Cod BANK'] + self.df['Cod Tiền mặt']
        self.df['COD thu khách'] = self.df['COD thu khách'].replace(0, np.nan)
        self.df['Tổng Cod'] = self.df['Tổng Cod'].replace(0, np.nan)
        # Clean the 'Trạng thái' column:
        self.df['Trạng thái'] = self.df['Trạng thái'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        # Calculate the 'ĐVVC', 'Tài khoản ĐVVC', 'Tiền bồi hoàn' columns:
        self.df['ĐVVC'] = 'Tu Van Chuyen'
        self.df['Tài khoản ĐVVC'] = 'Tu Van Chuyen'
        self.df['Tiền bồi hoàn'] = 0
        self.df['Thời gian ký nhận'] = np.nan
        # Choose only necessary column:
        self.df = self.df[self.finalcolumns]
        return self.df


# InternalPriceAPICleaner class:
class InternalPriceAPICleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame):
        """
        Clean internal product information data from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing internal product information data that fetches from a googlesheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Clean the 'Mã SP' column:
        self.df['Mã SP'] = self.df['Mã SP'].str.replace(r'[\n\t ]', '', regex=True)
        self.df = self.df[self.df['Mã SP']!=''].copy()
        self.df['Mã SP'] = self.df['Mã SP'].str.upper()
        check = self.df[self.df['Mã SP'].str.match(r'^MDU\d{4}$')][['Mã SP', 'Giá nội bộ']]
        if len(check) < 1000:
            warnings.warn("The number of 'Mã SP' values that have format 'MDUxxxx' are less than 1000, maybe you parsed wrong 'Mã SP' column. All values won't be uploaded on the data warehouse!'")
            return []
        # Clean the 'Giá nội bộ' column:
        self.df['Giá nội bộ'] = self.df['Giá nội bộ'].str.replace(r'[ \n\t]', '', regex=True)
        self.df['Giá nội bộ'] = self.df['Giá nội bộ'].apply(lambda x: unidecode(str(x)) if pd.notnull(x) else x)
        self.df['Giá nội bộ'] = self.df['Giá nội bộ'].str.lower()
        check = self.df['Giá nội bộ'].str.match(r'(\d+)(?=k)')
        if len(check) < 1000:
            warnings.warn("The number of 'Giá nội bộ' values that have format 'nk' are less than 1000, maybe you parsed wrong 'Giá nội bộ' column. All values won't be uploaded on the data warehouse!")
            return []
        self.df['Giá nội bộ'] = self.df['Giá nội bộ'].str.extract(r'(\d+)(?=k)') # Extract all adjacent digits that appear right before the first "k" letter
        self.df['Giá nội bộ'] = pd.to_numeric(self.df['Giá nội bộ'], errors='coerce')
        check = self.df[self.df['Giá nội bộ'].isna()][['Mã SP']]
        if len(check) > 0:
            warnings.warn(f"'Giá nội bộ' of some 'Mã SP' is null or not nk format. These 'Mã SP' still be uploaded on data warehouse with null retailprice value:\n{check}")
        self.df['Giá nội bộ'] = self.df['Giá nội bộ']*1000
        # Convert empty string values to nan values:
        for col in ['Mục đích', 'Màu sắc', 'Chất liệu', 'Cổ váy', 'Tay váy', 'Chiều dài tay', 'Kiểu váy', 'Mẫu vải']:
            self.df[col] = self.df[col].replace('', np.nan)
        # Choose only necessary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# DeliveryOrdersHandlingTeamAPICleaner class:
class DeliveryOrdersHandlingTeamAPICleaner(Cleaner):
    def __init__(self,
                finalcolumns: list[str],
                df: pd.DataFrame):
        """
        Clean handling team note data from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing handling team note data that fetches from a googlesheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Add buffer columns to fit the length of target table in the datalake:
        self.df['Buffer1'] = np.nan
        # Clean dataframe:
        for col in ['Ghi chú 1', 'Ghi chú 2', 'Ghi chú 3']:
            self.df[col] = self.df[col].replace('', np.nan)
        self.df = self.df[(self.df['Mã vận đơn']!='') & (self.df['Mã vận đơn']!='Mã vận đơn')][self.finalcolumns]
        check = self.df[self.df.duplicated(subset='Mã vận đơn', keep=False)][['Mã vận đơn']]
        if len(check) > 0:
            warnings.warn(f"The dataframe in DeliveryOrdersHandlingTeamAPICleaner class containing duplicate values. Only the last records will be uploaded on the data warehouse. Please check:\n{check}")
        return self.df


# DeliveryOrdersScanTrackingNumberAPICleaner class:
class DeliveryOrdersScanTrackingNumberAPICleaner(Cleaner):
    def __init__(self,
                finalcolumns: list[str],
                df: pd.DataFrame):
        """
        Clean scanning tracking number data from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing scanning tracking number data that fetches from a googlesheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        # Add buffer columns to fit the length of target table in the datalake:
        self.df['Buffer1'] = np.nan
        self.df['Buffer2'] = np.nan
        self.df['Buffer3'] = np.nan
        # Clean dataframe:
        self.df['Mã vận đơn'] = self.df['Mã vận đơn'].str.upper()
        self.df['Mã vận đơn'] = self.df['Mã vận đơn'].str.replace(r'[ \n\t]', '', regex=True)
        self.df = self.df[self.df['Mã vận đơn'] != ''][self.finalcolumns]
        return self.df


# ReturnedOrdersScanTrackingNumberAPICleaner class:
class ReturnedOrdersScanTrackingNumberAPICleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame,
                 year: int):
        """
        Clean scanning tracking number data of returned orders from a googlesheet file
        :param finalcolumns: a list of strings, containing column names of the final dataframe after applying the cleandata() method
        :param df: the dataframe containing scanning tracking number data of returned orders that fetches from a googlesheet file
        :param year: the year of the scanning returned orders google sheet file
        """
        self.finalcolumns = finalcolumns
        self.df = df
        self.year = year
    def cleandata(self):
        # Clean 'Mã vận đơn' and 'Mã SP' columns:
        self.df = self.df[((self.df['Mã vận đơn']!='') | (self.df['Mã SP']!=''))&(self.df['Key']!='STT')].copy()
        for col in ['Mã vận đơn', 'Mã SP']:
            self.df[col] = self.df[col].str.replace(r'[\n\t ]', '', regex=True)
            self.df[col] = self.df[col].str.upper()
            self.df[col] = self.df[col].replace('', np.nan)
        self.df['Mã vận đơn'] = self.df['Mã vận đơn'].ffill()
        self.df['Mã SP'] = self.df['Mã SP'].replace('#N/A', np.nan)
        # Calculate the 'Ngày bắn' column:
        self.df['THÁNG'] = self.df['THÁNG'].str.lower()
        self.df['THÁNG'] = self.df['THÁNG'].str.replace('t', '')
        for col in ['NGÀY', 'THÁNG']:
            self.df[col] = self.df[col].str.replace(r'[\n\t ]', '', regex=True)
            self.df[col] = self.df[col].replace('', np.nan)
            self.df[col] = self.df[col].ffill()
        self.df['Ngày bắn'] = str(self.year) + '-' + self.df['THÁNG'] + '-' + self.df['NGÀY']
        # Returned tracking number and original tracking number of some orders are different, make the returned tracking number looks like original tracking number:
        mask_ghn = ((self.df['Mã vận đơn'].str.startswith('NVS', na=False)) & (self.df['Mã vận đơn'].str.endswith('_PR', na=False)) & (self.df['Mã vận đơn'].str.len() == 15))
        self.df.loc[mask_ghn, 'Mã vận đơn'] = self.df.loc[mask_ghn, 'Mã vận đơn'].str[:-3]
        mask_jte = ((self.df['Mã vận đơn'].str.endswith('-001', na=False)) & (self.df['Mã vận đơn'].str.len() == 16))
        self.df.loc[mask_jte, 'Mã vận đơn'] = self.df.loc[mask_jte, 'Mã vận đơn'].str[:-4]
        # Choose only necessary columns:
        self.df = self.df[self.finalcolumns]
        return self.df


# OrdersShopeeAPICleaner class:
class OrdersShopeeAPICleaner(Cleaner):
    """
    Purpose: return a dataframe containing orders data and a dataframe containing orders details data
    """
    def __init__(self,
                 list_orderdetail: list[dict],
                 list_escrowdetail: list[dict],
                 list_trackingnumber: list[dict],
                 shopname: str):
        """
        :param list_orderdetail: a list of dictionaries, each dictionary containing order details data for an order
        :param list_escrowdetail: a list of dictionaries, each dictionary containing escrow details data for an order
        :param list_trackingnumber: a list of dictionaries, each dictionary containing a package ID and a tracking number for an order
        :param shopname: this data belong which shop?
        """
        self.list_orderdetail = list_orderdetail
        self.list_escrowdetail = list_escrowdetail
        self.list_trackingnumber = list_trackingnumber
        self.shopname = shopname
    def cleandata(self) -> pd.DataFrame:
        # Create dataframe containing necessary data from list_orderdetail:
        allrecord_orderdetail  = []
        orderdetail_col = [
            'ID đơn hàng',
            'Mã gói hàng',
            'Đơn vị vận chuyển',
            'Ngày đặt hàng',
            'Ngày lấy hàng',
            'Ngày hoàn thành',
            'Trạng thái đơn',
            'Lý do hủy',
            'Người mua'
        ]
        for x in self.list_orderdetail: # x is a dictionary
            record_orderdetail = []
            append_iferror(record_orderdetail, x, ['order_sn'])
            try:
                record_orderdetail.append(x['package_list'][0]['package_number'])
            except:
                record_orderdetail.append(None)
            try:
                record_orderdetail.append(x['package_list'][0]['shipping_carrier'])
            except:
                record_orderdetail.append(None)
            append_iferror(record_orderdetail, x, ['create_time'])
            append_iferror(record_orderdetail, x, ['pickup_done_time']) # If an order haven't been picked up by a delivery yet, this returns 0 value (integer). I have converted these 0 values into NaN values in dataframe at below code
            append_iferror(record_orderdetail, x, ['update_time']) # For orders haven't completed, the 'Ngày hoàn thành' value should be NaN. I have converted to NaN value in dataframe at below code
            append_iferror(record_orderdetail, x, ['order_status'])
            append_iferror(record_orderdetail, x, ['cancel_reason'])
            append_iferror(record_orderdetail, x, ['buyer_username'])
            allrecord_orderdetail.append(record_orderdetail)
        df_orderdetail = pd.DataFrame(data=allrecord_orderdetail, columns=orderdetail_col)
        # Create dataframe containing necessary data from list_escrowdetail:
        allrecord_escrowdetail = []
        escrowdetail_col = [
            'ID đơn hàng',
            'Mã đơn hoàn về',
            'Phương thức thanh toán của người mua',
            'Tiền về ví lý thuyết',
            'Tiền người mua đã thanh toán',
            'Phí vận chuyển',
            'Phí vận chuyển được Shopee tài trợ',
            'Phí vận chuyển được Người Bán tài trợ'
        ]
        for y in self.list_escrowdetail: # y is a dictionary
            record_escrowdetail = []
            append_iferror(record_escrowdetail, y, ['order_sn'])
            append_iferror(record_escrowdetail, y, ['return_order_sn_list'])
            append_iferror(record_escrowdetail, y, ['order_income', 'buyer_payment_method'])
            append_iferror(record_escrowdetail, y, ['order_income', 'escrow_amount'])
            append_iferror(record_escrowdetail, y, ['buyer_payment_info', 'buyer_total_amount'])
            append_iferror(record_escrowdetail, y, ['order_income', 'actual_shipping_fee'])
            append_iferror(record_escrowdetail, y, ['order_income', 'shopee_shipping_rebate'])
            append_iferror(record_escrowdetail, y, ['order_income', 'seller_shipping_discount'])
            allrecord_escrowdetail.append(record_escrowdetail)
        df_escrowdetail = pd.DataFrame(data=allrecord_escrowdetail, columns=escrowdetail_col)
        # Create dataframe containing necessary data from list_trackingnumber:
        allrecord_trackingnumber = []
        trackingnumber_col = [
            'Mã gói hàng',
            'Mã đơn hãng vận chuyển'
        ]
        for z in self.list_trackingnumber: # z is a dictionary
            record_trackingnumber = []
            append_iferror(record_trackingnumber, z, ['package_number'])
            append_iferror(record_trackingnumber, z, ['tracking_number']) # If an order haven't had a tracking_number yet, this return "" value (string). I have converted these "" values into NaN values in dataframe at below code
            allrecord_trackingnumber.append(record_trackingnumber)
        df_trackingnumber = pd.DataFrame(data=allrecord_trackingnumber, columns=trackingnumber_col)
        # Merge 3 dataframes and clean:
        df = pd.merge(df_orderdetail, df_escrowdetail, left_on='ID đơn hàng', right_on='ID đơn hàng', how='left')
        df = pd.merge(df, df_trackingnumber, left_on='Mã gói hàng', right_on='Mã gói hàng', how='left')
        # Clean the 'Ngày lấy hàng' column:
        df['Ngày lấy hàng'] = df['Ngày lấy hàng'].replace(0, np.nan)
        # Clean the 'Ngày hoàn thành' column:
        df.loc[df['Trạng thái đơn']!='COMPLETED', 'Ngày hoàn thành'] = np.nan
        # Clean the 'Mã đơn hãng vận chuyển' column:
        df['Mã đơn hãng vận chuyển'] = df['Mã đơn hãng vận chuyển'].replace("", np.nan)
        # Convert all list values in the 'Mã đơn hoàn về' column to string values:
        df['Mã đơn hoàn về'] = df['Mã đơn hoàn về'].apply(lambda x: str(x) if isinstance(x, list) else x)
        df['Mã đơn hoàn về'] = df['Mã đơn hoàn về'].replace('[]', np.nan)
        # Create the 'Tên shop' column:
        df['Tên shop'] = self.shopname
        # Check columns must contain only int values:
        for col in ['Tiền về ví lý thuyết', 'Tiền người mua đã thanh toán', 'Phí vận chuyển', 'Phí vận chuyển được Shopee tài trợ', 'Phí vận chuyển được Người Bán tài trợ']:
            if str(df[col].dtype) != 'int64':
                warnings.warn(f"The {col} column in the Shopee order dataframe must contain only integers. But the dtype of this column is not 'int64'!")
        # Clean diacritics columns:
        for col in ['Đơn vị vận chuyển']:
            df['Đơn vị vận chuyển'] = df['Đơn vị vận chuyển'].apply(lambda x: unidecode(x) if isinstance(x, str) else x)
        # Choose only necessary columns:
        df = df[[
            'ID đơn hàng',
            'Mã gói hàng',
            'Đơn vị vận chuyển',
            'Ngày đặt hàng',
            'Ngày lấy hàng',
            'Ngày hoàn thành',
            'Trạng thái đơn',
            'Lý do hủy',
            'Người mua',
            'Mã đơn hoàn về',
            'Phương thức thanh toán của người mua',
            'Tiền về ví lý thuyết',
            'Tiền người mua đã thanh toán',
            'Phí vận chuyển',
            'Phí vận chuyển được Shopee tài trợ',
            'Phí vận chuyển được Người Bán tài trợ',
            'Mã đơn hãng vận chuyển',
            'Tên shop'
        ]]
        return df
    def cleandata_orderdetails(self) -> pd.DataFrame:
        # Create dataframe containing necessary data from list_orderdetail:
        allrecord_orderdetail2 = []
        orderdetail_col = [
            'ID đơn hàng',
            'Mã sản phẩm Shopee',
            'Mã phân loại sản phẩm Shopee',
            'Mã đơn hàng_sản phẩm_modelid',
            'Mã đơn hàng_sản phẩm_itemid',
            'Tên sản phẩm',
            'Tên phân loại sản phẩm',
            'Số lượng',
            'Giá hiển thị',
            'Giá tính tiền_orderdetail'
        ]
        for order in self.list_orderdetail: # order is a dictionary
            for i in order['item_list']: # i is a dictionary
                record = []
                append_iferror(record, order, ['order_sn'])
                append_iferror(record, i, ['item_sku'])
                append_iferror(record, i, ['model_sku'])
                append_iferror(record, i, ['model_id'])
                append_iferror(record, i, ['item_id'])
                append_iferror(record, i, ['item_name'])
                append_iferror(record, i, ['model_name'])
                append_iferror(record, i, ['model_quantity_purchased'])
                append_iferror(record, i, ['model_original_price'])
                append_iferror(record, i, ['model_discounted_price'])
                allrecord_orderdetail2.append(record)
        df_orderdetail2 = pd.DataFrame(data=allrecord_orderdetail2, columns=orderdetail_col)
        # Create dataframe containing necessary data from list_escrowdetail:
        allrecord_escrowdetail2 = []
        escrowdetail_col = [
            'ID đơn hàng',
            'Mã phân loại sản phẩm Shopee',
            'Mã đơn hàng_sản phẩm_modelid',
            'Mã đơn hàng_sản phẩm_itemid',
            'Mã đơn hàng_sản phẩm_quantitypurchased',
            'Tổng discount tính tiền thật',
            'Tổng discount giảm giá của shop',
            'Tổng discount giảm giá của Shopee'
        ]
        for order in self.list_escrowdetail: # order is a dictionary
            for i in order['order_income']['items']: # i is a dictionary
                record = []
                append_iferror(record, order, ['order_sn'])
                append_iferror(record, i, ['model_sku'])
                append_iferror(record, i, ['model_id'])
                append_iferror(record, i, ['item_id'])
                append_iferror(record, i, ['quantity_purchased'])
                append_iferror(record, i, ['seller_discount'])
                append_iferror(record, i, ['discount_from_voucher_seller'])
                append_iferror(record, i, ['discount_from_voucher_shopee'])
                allrecord_escrowdetail2.append(record)
        df_escrowdetail2 = pd.DataFrame(data=allrecord_escrowdetail2, columns=escrowdetail_col)
        # Merge 2 dataframes and clean:
        df_orderdetail2['Mã đơn hàng_sản phẩm'] = df_orderdetail2['Mã đơn hàng_sản phẩm_modelid'].astype(str) + '_' + df_orderdetail2['Mã đơn hàng_sản phẩm_itemid'].astype(str) + '_' + df_orderdetail2['Số lượng'].astype(str)
        df_escrowdetail2['Mã đơn hàng_sản phẩm'] = df_escrowdetail2['Mã đơn hàng_sản phẩm_modelid'].astype(str) + '_' + df_escrowdetail2['Mã đơn hàng_sản phẩm_itemid'].astype(str) + '_' + df_escrowdetail2['Mã đơn hàng_sản phẩm_quantitypurchased'].astype(str)
        df2 = pd.merge(df_orderdetail2, df_escrowdetail2, left_on=['ID đơn hàng', 'Mã phân loại sản phẩm Shopee', 'Mã đơn hàng_sản phẩm'], right_on=['ID đơn hàng', 'Mã phân loại sản phẩm Shopee', 'Mã đơn hàng_sản phẩm'], how='left')
        if df2['Tổng discount tính tiền thật'].isna().any():
            raise ValueError("The 'Tổng discount tính tiền thật' column of Shopee_orderdetails dataframe containing NaN values. High chance is the ordinal appearance of products in get_order_detail endpoint and get_escrow_detail endpoint is different. Take a check!")
        # Calculate the 'Giá tính tiền' column ('Giá tính tiền' is counted for a single product in each record):
        df2['Giá tính tiền'] = df2['Giá tính tiền_orderdetail'].astype(float)
        df2.loc[df2['Giá tính tiền_orderdetail']==0, 'Giá tính tiền'] = df2['Giá hiển thị'] - (df2['Tổng discount tính tiền thật']/df2['Số lượng'])
        # Choose only necessary columns:
        df2 = df2[[
            'ID đơn hàng',
            'Mã phân loại sản phẩm Shopee',
            'Mã đơn hàng_sản phẩm',
            'Mã sản phẩm Shopee',
            'Tên sản phẩm',
            'Tên phân loại sản phẩm',
            'Số lượng',
            'Giá hiển thị',
            'Giá tính tiền',
            'Tổng discount giảm giá của shop',
            'Tổng discount giảm giá của Shopee'
        ]]
        return df2


# IncomeShopeeAPICleaner class:
class IncomeShopeeAPICleaner(Cleaner):
    """
    Purpose: return a dataframe containing income details data
    """
    def __init__(self, list_incomedetail):
        """
        :param list_incomedetail: a list of dictionaries, each dictionary containing income details data for an order
        """
        self.list_incomedetail = list_incomedetail
    def cleandata(self):
        # Create a dataframe containing necessary data from list_incomedetail:
        allrecords = []
        incomedetail_cols = [
            'Mã vận đơn',
            'Tiền giao dịch',
            'Thời gian giao dịch'
        ]
        for income in self.list_incomedetail: # record is a dictionary
            record = []
            append_iferror(record, income, ['order_sn'])
            append_iferror(record, income, ['released_amount'])
            append_iferror(record, income, ['actual_payout_time'])
            allrecords.append(record)
        df_incomedetail = pd.DataFrame(data=allrecords, columns=incomedetail_cols)
        # Clean the dataframe:
        df_incomedetail['Mã giao dịch'] = df_incomedetail['Mã vận đơn'] + '_' + df_incomedetail['Tiền giao dịch'].astype(str) + '_' + df_incomedetail['Thời gian giao dịch'].astype(str)
        df_incomedetail['Hãng vận chuyển'] = 'Orders from Shopee Shops'
        df_incomedetail['Nội dung'] = np.nan
        df_incomedetail = df_incomedetail[[
            'Mã giao dịch',
            'Mã vận đơn',
            'Tiền giao dịch',
            'Thời gian giao dịch',
            'Hãng vận chuyển',
            'Nội dung'
        ]]
        return df_incomedetail


# OrdersTiktokAPICleaner class:
class OrdersTiktokAPICleaner(Cleaner):
    def __init__(self, list_orders: list[dict], list_returnorders: list[dict], shopname):
        self.list_orders = list_orders
        self.list_returnorders = list_returnorders
        self.shopname = shopname
    def cleandata(self) -> pd.DataFrame:
        # Create a dataframe containing necessary data from list_orders:
        allrecord_orders = []
        orders_col = [
            'orderid',
            'shipping_provider',
            'create_time',
            'collection_time',
            'delivery_time',
            'cancel_time',
            'status',
            'cancel_reason',
            'buyer_email',
            'payment_method_name',
            'original_shipping_fee',
            'actual_shipping_fee',
            'shipping_fee_platform_discount',
            'shipping_fee_seller_discount',
            'tracking_number',
            'buyeraddress_lv0',
            'buyeraddress_lv1',
            'buyeraddress_lv2'
        ]
        for x in self.list_orders: # x is a dictionary
            record_order = []
            append_iferror(record_order, x, ['id'])
            append_iferror(record_order, x, ['shipping_provider'])
            append_iferror(record_order, x, ['create_time'])
            append_iferror(record_order, x, ['collection_time'])
            append_iferror(record_order, x, ['delivery_time'])
            append_iferror(record_order, x, ['cancel_time'])
            append_iferror(record_order, x, ['status'])
            append_iferror(record_order, x, ['cancel_reason'])
            append_iferror(record_order, x, ['buyer_email'])
            append_iferror(record_order, x, ['payment_method_name'])
            append_iferror(record_order, x, ['payment', 'original_shipping_fee'])
            append_iferror(record_order, x, ['payment', 'shipping_fee'])
            append_iferror(record_order, x, ['payment', 'shipping_fee_platform_discount'])
            append_iferror(record_order, x, ['payment', 'shipping_fee_seller_discount'])
            append_iferror(record_order, x, ['tracking_number'])
            try:
                record_order.append(x['recipient_address']['district_info'][0]['address_name'])
            except:
                record_order.append(None)
            try:
                record_order.append(x['recipient_address']['district_info'][1]['address_name'])
            except:
                record_order.append(None)
            try:
                record_order.append(x['recipient_address']['district_info'][2]['address_name'])
            except:
                record_order.append(None)
            allrecord_orders.append(record_order)
        df_orders = pd.DataFrame(data=allrecord_orders, columns=orders_col)
        # Create a dataframe containing necessary data from list_returnorders:
        allrecord_returnorders = []
        returnorders_col = [
            'order_id from df_returnorders',
            'return_order_created_time',
            'return_reason',
            'returned_trackingnumber',
            'returnstatus',
            'returnshippingfee_paidbybuyer',
            'returnshippingfee_paidbyplatform',
            'returnshippingfee_paidbyseller'
        ]
        for y in self.list_returnorders:
            record_returnorders = []
            append_iferror(record_returnorders, y, ['order_id'])
            append_iferror(record_returnorders, y, ['create_time'])
            append_iferror(record_returnorders, y, ['return_reason_text'])
            append_iferror(record_returnorders, y, ['return_tracking_number'])
            append_iferror(record_returnorders, y, ['return_status'])
            try:
                shippingfee_buyerpaid = 0
                for i in y['shipping_fee_amount']:
                    shippingfee_buyerpaid = shippingfee_buyerpaid + int(i['buyer_paid_return_shipping_fee'])
                record_returnorders.append(shippingfee_buyerpaid)
            except:
                record_returnorders.append(None)
            try:
                shippingfee_platformpaid = 0
                for i in y['shipping_fee_amount']:
                    shippingfee_platformpaid = shippingfee_platformpaid + int(i['platform_paid_return_shipping_fee'])
                record_returnorders.append(shippingfee_platformpaid)
            except:
                record_returnorders.append(None)
            try:
                shippingfee_sellerpaid = 0
                for i in y['shipping_fee_amount']:
                    shippingfee_sellerpaid = shippingfee_sellerpaid + int(i['seller_paid_return_shipping_fee'])
                record_returnorders.append(shippingfee_sellerpaid)
            except:
                record_returnorders.append(None)
            allrecord_returnorders.append(record_returnorders)
        df_returnorders = pd.DataFrame(data=allrecord_returnorders, columns=returnorders_col)
        # Merge 2 dataframes and clean:
        check_dup = df_returnorders[df_returnorders.duplicated(subset='order_id from df_returnorders', keep='first')][['order_id from df_returnorders']]
        if len(check_dup) > 0:
            # warnings.warn(f"Tiktok Shop Partner API: exists 1 order ID have >=2 returned order IDs. Check those IDs here:\n{check_dup}\nKeep only the returned order IDs that have max returned order's create_time! (Usually, max create_time is completed returned order, min create_time is canceled returned order)") # Stop triggering this warning because it appears a lot
            df_returnorders = df_returnorders.sort_values(by='return_order_created_time', ascending=True)
            df_returnorders = df_returnorders.drop_duplicates(subset='order_id from df_returnorders', keep='last')
        df = pd.merge(df_orders, df_returnorders, left_on='orderid', right_on='order_id from df_returnorders', how='left')
        # Clean the 'create_time', 'collection_time', 'delivery_time', 'cancel_time' columns: time values from json reponse have already been integers, so these columns will become float datatype (because of None values). Don't need to clean anymore
        # Clean the 'orderid' and 'tracking_number' columns:
        for col in ['orderid', 'tracking_number']:
            df[col] = df[col].apply(lambda x: x if pd.isna(x) else str(x) if isinstance(x, int) else str(round(x)) if isinstance(x, float) else x)
        # Clean 'original_shipping_fee', 'actual_shipping_fee', 'shipping_fee_platform_discount', 'shipping_fee_seller_discount' columns:
        for col in ['original_shipping_fee', 'actual_shipping_fee', 'shipping_fee_platform_discount', 'shipping_fee_seller_discount']:
            df[col] = df[col].replace('', np.nan)
            df[col] = pd.to_numeric(df[col], errors='raise')
        # Clean diacritics columns:
        for col in ['buyeraddress_lv0', 'buyeraddress_lv1', 'buyeraddress_lv2', 'cancel_reason', 'shipping_provider']:
            df[col] = df[col].apply(lambda x: unidecode(x) if isinstance(x, str) else x)
        # Clean the 'returned_trackingnumber' column:
        df.loc[df['returned_trackingnumber'].str.len() > 50, 'returned_trackingnumber'] = df.loc[df['returned_trackingnumber'].str.len() > 50, 'returned_trackingnumber'].str[0:49]
        # Create 'shopname' column:
        df['shopname'] = self.shopname
        # Choose only necessary columns:
        df = df[[
            'orderid',
            'create_time',
            'collection_time',
            'delivery_time',
            'cancel_time',
            'status',
            'cancel_reason',
            'buyer_email',
            'payment_method_name',
            'original_shipping_fee',
            'actual_shipping_fee',
            'shipping_fee_platform_discount',
            'shipping_fee_seller_discount',
            'tracking_number',
            'shipping_provider',
            'buyeraddress_lv0',
            'buyeraddress_lv1',
            'buyeraddress_lv2',
            'return_reason',
            'returned_trackingnumber',
            'returnstatus',
            'returnshippingfee_paidbybuyer',
            'returnshippingfee_paidbyplatform',
            'returnshippingfee_paidbyseller',
            'shopname'
        ]]
        return df
    def cleandata_orderdetails(self) -> pd.DataFrame:
        # Create a dataframe containing necessary data from list_orders:
        allrecord_orderdetails = []
        orderdetails_col = [
            'orderid',
            'product_skuid',
            'productid',
            'productname',
            'product_skuname',
            'displayprice',
            'shopdiscount_allquantities',
            'tiktokdiscount_allquantities'
        ]
        for order in self.list_orders:
            for i in order['line_items']: # i is a dictionary
                record = []
                append_iferror(record, order, ['id'])
                append_iferror(record, i, ['seller_sku'])
                append_iferror(record, i, ['product_id'])
                append_iferror(record, i, ['product_name'])
                append_iferror(record, i, ['sku_name'])
                append_iferror(record, i, ['original_price'])
                append_iferror(record, i, ['seller_discount'])
                append_iferror(record, i, ['platform_discount'])
                allrecord_orderdetails.append(record)
        df_orderdetails = pd.DataFrame(data=allrecord_orderdetails, columns=orderdetails_col)
        # Clean the dataframe:
        # Clean the 'displayprice', 'shopdiscount_allquantities', 'tiktokdiscount_allquantities' columns:
        for col in ['displayprice', 'shopdiscount_allquantities', 'tiktokdiscount_allquantities']:
            df_orderdetails[col] = df_orderdetails[col].replace('', np.nan)
            df_orderdetails[col] = pd.to_numeric(df_orderdetails[col], errors='raise')
        # Calculate the quantity column:
        df_orderdetails['quantity'] = 1
        df_orderdetails = df_orderdetails.groupby(['orderid', 'product_skuid', 'productid', 'productname', 'product_skuname', 'displayprice'], as_index=False).agg({'quantity':'sum', 'shopdiscount_allquantities':'sum', 'tiktokdiscount_allquantities':'sum'})
        check = df_orderdetails[df_orderdetails.duplicated(subset=['orderid', 'product_skuid'], keep=False)][['orderid', 'productid', 'displayprice']]
        if len(check) > 0:
            warnings.warn(f"OrdersTiktokAPICleaner class: detect duplicate (orderid, product_skuid) in result:\n{check}\nOnly keep the first appearance!")
            df_orderdetails = df_orderdetails.drop_duplicates(subset=['orderid', 'product_skuid'], keep='first')
        # Choose only necessary columns:
        df_orderdetails = df_orderdetails[[
            'orderid',
            'product_skuid',
            'productid',
            'productname',
            'product_skuname',
            'displayprice',
            'quantity',
            'shopdiscount_allquantities',
            'tiktokdiscount_allquantities'
        ]]
        return df_orderdetails


# IncomeTiktokExcelCleaner class:
class IncomeTiktokExcelCleaner(Cleaner):
    def __init__(self,
                 finalcolumns: list[str],
                 df: pd.DataFrame):
        self.finalcolumns = finalcolumns
        self.df = df
    def cleandata(self):
        for col in [
            'Tổng số tiền quyết toán',
            'Tổng doanh thu',
            'Tổng phụ sau giảm giá của người bán',
            'Tổng phụ trước giảm giá',
            'Giảm giá của người bán',
            'Tổng phụ của khoản hoàn tiền sau giảm giá của người bán',
            'Tổng phụ hoàn tiền trước giảm giá của người bán',
            'Khoản hoàn tiền giảm giá của người bán',
            'Tổng phí'
        ]:
            if self.df[col].dtype != 'int64':
                raise ValueError(f"IncomeTiktokExcelCleaner class: the {col} column of the dataframe is not int64 datatype. Means that there is value(s) in this {col} column (from excel file) is not integer")
        self.df['Loại giao dịch'] = self.df['Loại giao dịch'].apply(lambda x: unidecode(x) if isinstance(x, str) else x)
        self.df = self.df[self.finalcolumns]
        return self.df