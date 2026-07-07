from abc import ABC, abstractmethod
from typing import Literal
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, date, time, timedelta


# Loader interface:
class Loader(ABC):
    @abstractmethod
    def loaddata(self):
        pass


# PreparationLoader class:
class DataframeToDatabaseLoader(Loader):
    """
    Purpose: upload data from a dataframe onto a database table
    """
    def __init__(self,
                 df: pd.DataFrame,
                 connection,
                 query: str,
                 updatetime,
                 *,
                 chunk: int = 1000,
                 enable_updatetime = 'Yes'):
        """
        :param df: dataframe want to upload.
        :param connection: mysql.connector.connection.MySQLConnection object
        :param query: the MySQL INSERT INTO query to execute.
        :param chunk: the dataframe have many (tens of thousands of) records, those records should be divided into smaller chunk records, avoid overloading for the system.
        :param enable_updatetime: whether add the updatetime to the dataframe before upload? Only add if your target table is inside a datalake.
        """
        self.df = df
        self.connection = connection
        self.query = query
        self.updatetime = updatetime
        self.chunk = chunk
        self.enable_updatetime = enable_updatetime
    def loaddata(self) -> None:
        # Add the 'update_at' column to the last of dataframe:
        if self.enable_updatetime == 'Yes':
            self.df['update_at'] = self.updatetime
        # Convert dataframe to a list of tuples:
        array = self.df.to_numpy() # array is a ndarray object (in this case: 2-dimension array)
        list_records = []
        for row in array:
            new_row = []
            for value in row:
                if pd.isna(value):
                    new_value = None
                elif isinstance(value, pd.Timestamp):
                    new_value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    new_value = value
                new_row.append(new_value)
            list_records.append(tuple(new_row))
        # Upload data on database table:
        cursor = self.connection.cursor()
        for i in range(0, len(list_records), self.chunk):
            batch = list_records[i:i+self.chunk]
            cursor.executemany(self.query, batch)
        self.connection.commit()
        cursor.close()
        return None


# DatabaseToSheetLoader class:
class DatabaseToSheetLoader(Loader):
    def __init__(self,
                 connection,
                 select_query,
                 worksheet_object,
                 sheet_rangeupdate):
        if select_query.casefold().find('insert') != -1 or select_query.casefold().find('update') != -1 or select_query.casefold().find('delete') != -1:
            raise ValueError("DatabaseToSheetLoader class: select_query must be select statement")
        self.connection = connection
        self.select_query = select_query
        self.worksheet_object = worksheet_object
        self.sheet_rangeupdate = sheet_rangeupdate
    def loaddata(self):
        # Retrieve data from the database:
        cursor = self.connection.cursor()
        cursor.execute(self.select_query)
        reportdata = cursor.fetchall() # reportdata is a tuple of tuples
        cursor.close()
        # Upload data on the sheet:
        self.worksheet_object.batch_clear([self.sheet_rangeupdate])
        list_reportdata = []
        for row in reportdata:
            new_row = []
            for value in row:
                if isinstance(value, Decimal):
                    new_value = float(value)
                elif isinstance(value, (datetime, date, time, timedelta)):
                    new_value = str(value)
                else:
                    new_value = value
                new_row.append(new_value)
            list_reportdata.append(new_row)
        self.worksheet_object.update(list_reportdata, self.sheet_rangeupdate, value_input_option="USER_ENTERED") # with value_input_option="USER_ENTERED": if the list contains a string look like a number, it becomes a number in the sheet
        return None