# -*- coding: utf-8 -*-

from googleapiclient.http import MediaFileUpload
import pandas as pd
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from oauth2client import file, client, tools
from apiclient import errors, discovery
from httplib2 import Http
from typing import *
from pprint import pprint
import traceback
import string
import getpass

# HOME_PATH = '/ldap_home/{}/chat_keywords_screening/keyword-screening/'.format(getpass.getuser())
HOME_PATH = './'
TOKEN_PATH = HOME_PATH + 'token.json'
CREDENTIAL_PATH = HOME_PATH + 'credentials.json'
SCOPES=['https://www.googleapis.com/auth/spreadsheets','https://mail.google.com/','https://www.googleapis.com/auth/drive']

# assert os.path.exists(TOKEN_PATH), "could not find %s" % (TOKEN_PATH)
assert os.path.exists(CREDENTIAL_PATH), "could not find %s" % (CREDENTIAL_PATH)

class GService:
    sheet_service = None
    mail_service = None
    drive_service = None

    def __init__(self) -> None:
        """
        Service Provider Object for Google Sheet, Drive, and Mail
        """
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIAL_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        self.sheet_service = build('sheets', 'v4', credentials=creds)
        self.mail_service = build('gmail', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)

    def add_dropdown_validation(
        self,
        gsheet_id: str, 
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        values: Iterable,
        input_msg: str = '',
        strict: bool = False
    ) -> dict:
        """
        Will apply dropdown style validation on cells bounded by starting & ending rows & columns. \n
        Row & column indexes start from 0 (cell A1 is row 0 column 0). \n
        `start_row` and `start_col` are inclusive. \n
        `end_row` and `end_col` are exclusive. \n
        
        Example
        -------
        `start_row` = 0 \n
        `end_row` = 5 \n
        `start_col` = 0 \n
        `end_col` = 2 \n
        Validation will be applied on cell range A1:B5
        """
        
        service = self.sheet_service
        spreadsheets = service.spreadsheets()
        request_body = {
            'requests': [{
                'setDataValidation': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': start_row,
                        'endRowIndex': end_row,
                        'startColumnIndex': start_col,
                        'endColumnIndex': end_col
                    },
                    'rule': {
                        'condition': {
                            'type': 'ONE_OF_LIST',
                            'values':[{'userEnteredValue':v} for v in values]
                            # 'values': [
                            #     {'userEnteredValue': 'Banned'},
                            #     {'userEnteredValue': 'Normal'}
                            # ]
                        },
                        'inputMessage': input_msg,
                        'showCustomUi': True,
                        'strict': strict
                    },
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        pprint(response)

        return response

    def get_sheet_id(self, gsheet_id: str, sheet_name: str) -> int:
        service = self.sheet_service
        sheet_metadata = service.spreadsheets().get(spreadsheetId=gsheet_id).execute()
        properties = sheet_metadata.get('sheets')
        id: int = [p.get('properties').get('sheetId') for p in properties if p.get('properties').get('title') == sheet_name][0]
        
        return id

    def add_sheet(self, gsheet_id: str, name: str, row_cnt: int = 100, col_cnt: int = 10) -> dict:
        service = self.sheet_service
        spreadsheets = service.spreadsheets()
        
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': name,
                        'gridProperties': {
                            'columnCount': col_cnt,
                            'rowCount': row_cnt
                        }
                    }
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        pprint(response)

        return response

    def delete_sheet(self, gsheet_id: str, sheet_id: int) -> dict:        
        service = self.sheet_service
        spreadsheets = service.spreadsheets()
        request_body = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        pprint(response)

        return response

    def get_sheet_names(self, gsheet_id: str) -> List[str]:
        service = self.sheet_service
        sheet_metadata = service.spreadsheets().get(spreadsheetId=gsheet_id).execute()
        properties = sheet_metadata.get('sheets')
        titles = [p.get('properties').get('title') for p in properties]
        
        return titles

    def read_google_sheet(self, gsheet_id: str, cell_range: str) -> pd.DataFrame:
        service = self.sheet_service
        result = service.spreadsheets().values() \
            .get(spreadsheetId=gsheet_id, range=cell_range) \
            .execute() \
            .get('values', ())
        
        try:
            header, rows = result[0], result[1:]
            numColumn = len(header)
        except IndexError as e:
            traceback.print_exc()
            print('Error opening sheet_id {} cell_range {}'.format(gsheet_id,cell_range))
            return None

        series = list()
        for row in rows:
            # fill the end of the list with enough data
            row = row + ([None] * (numColumn - len(row)))
            series.append(row)

        return pd.DataFrame(series, columns=header)

    def write_google_sheet(self, gsheet_id: str, cell_range: str, values: List[List[Union[str,int]]], input_option: str = 'USER_ENTERED') -> dict:
        """
        `input_option` -> 'RAW' or 'USER_ENTERED'

        USER_ENTERED -> gsheet takes the cell values as if typed in by a human (e.g. '2021-11-01' will be auto converted to date)
        RAW -> gsheet takes the cell values directly (e.g. '2021-11-01' will remain as string)
        """
        body = {'values':values}
        service = self.sheet_service
        result = service.spreadsheets().values() \
            .update(spreadsheetId=gsheet_id, range=cell_range, valueInputOption=input_option, body=body) \
            .execute()
        print('{0} cells updated'.format(result.get('updatedCells')))

        return result

    def clear_google_sheet(self, gsheet_id: str, cell_range: str) -> dict:
        service = self.sheet_service
        request = service.spreadsheets().values().clear(spreadsheetId=gsheet_id, range=cell_range)
        response = request.execute()
        
        pprint(response)

        return response

    def append_google_sheet(self, gsheet_id: str, cell_range: str, values: List[List[Union[str,int]]], insert_new_row: bool=False, input_option: str = 'USER_ENTERED') -> dict:
        body = {'values':values}
        service = self.sheet_service
        
        if insert_new_row:
            insert_data_option = 'INSERT_ROWS'
        else:
            insert_data_option = 'OVERWRITE'
        
        result = service.spreadsheets().values() \
            .append(spreadsheetId=gsheet_id, range=cell_range, insertDataOption=insert_data_option, valueInputOption=input_option, body=body) \
            .execute()
        pprint(result)

        return result
    
    def append_column(self, gsheet_id: str, sheet_id: int, n_cols: int) -> dict:
        service = self.sheet_service
        body = {
            "requests": [
                {
                    "appendDimension": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "length": n_cols
                    }
                }
            ]
        }

        result = service.spreadsheets().batchUpdate(spreadsheetId=gsheet_id, body=body).execute()
        pprint(result)

        return result

    def append_row(self, gsheet_id: str, sheet_id: int, n_rows: int) -> dict:
        service = self.sheet_service
        body = {
            "requests": [
                {
                    "appendDimension": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "length": n_rows
                    }
                }
            ]
        }

        result = service.spreadsheets().batchUpdate(spreadsheetId=gsheet_id, body=body).execute()
        pprint(result)

        return result
    
    def delete_column(self, gsheet_id: str, sheet_id: int, start_col: int, end_col: int) -> dict:
        """
        Row & column indexes start from 0 (cell A1 is row 0 column 0). \n
        `start_col` is inclusive. \n
        `end_col` is exclusive. \n
        
        Example
        -------
        `start_col` = 0 \n
        `end_col` = 3 \n
        Columns A-C will be deleted
        """
        service = self.sheet_service
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_col,
                            "endIndex": end_col
                        }
                    }
                }
            ],
        }

        result = service.spreadsheets().batchUpdate(spreadsheetId=gsheet_id, body=body).execute()
        pprint(result)

        return result

    def delete_row(self, gsheet_id: str, sheet_id: int, start_row: int, end_row: int) -> dict:
        """
        Row & column indexes start from 0 (cell A1 is row 0 column 0). \n
        `start_row` is inclusive. \n
        `end_row` is exclusive. \n
        
        Example
        -------
        `start_row` = 0 \n
        `end_row` = 5 \n
        Rows 1-5 will be deleted
        """
        service = self.sheet_service
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": start_row,
                            "endIndex": end_row
                        }
                    }
                }
            ],
        }
        
        result = service.spreadsheets().batchUpdate(spreadsheetId=gsheet_id, body=body).execute()
        pprint(result)

        return result

    def get_sheet_dimension(self, gsheet_id: str, sheet_name: str) -> Tuple[int, int]:
        """return -> tuple(row_count, column_count)"""
        service = self.sheet_service
        sheet_metadata = service.spreadsheets().get(spreadsheetId=gsheet_id).execute()
        properties = sheet_metadata.get('sheets')
        grid_properties = [p.get('properties').get('gridProperties') for p in properties if p.get('properties').get('title') == sheet_name][0]
        row_count, column_count = grid_properties.get('rowCount'), grid_properties.get('columnCount')
        return row_count, column_count
    
    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> dict:
        service = self.drive_service
        
        if parent_folder_id is None:
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
        else:
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }

        folder = service.files().create(
            body=metadata,
            fields='id'
        ).execute()

        print('Folder ID:', folder.get('id'))
        return folder
    
    def upload_file(self, local_file_path: str, gdrive_file_name: str, parent_gdrive_folder_id: str = None, file_type: str = None, google_docs_type: str = None) -> dict:
        service = self.drive_service

        metadata = {'name': gdrive_file_name}
        if parent_gdrive_folder_id is not None:
            metadata.update({'parents': [parent_gdrive_folder_id]})
        if google_docs_type is not None:
            metadata.update({'mimeType': google_docs_type})
        
        media = MediaFileUpload(local_file_path, mimetype=file_type)
        gdrive_file = service.files().create(
            body=metadata,
            media_body=media,
            fields='id'
        ).execute()

        print('File ID:', gdrive_file.get('id'))
        return gdrive_file
    
    def list_files(self, gdrive_folder_id: str) -> list:
        service = self.drive_service
        response = service.files().list(
            q="'{}' in parents".format(gdrive_folder_id)
        ).execute()

        return response.get('files', [])

def df_to_value_range(df: pd.DataFrame, include_header=True) -> List[List[str]]:
    df.fillna('', inplace=True)
    headers = [str(h) for h in list(df.columns)]
    content = [[str(c) for c in df.loc[i]] for i in df.index]
    if include_header:
        return [headers] + content
    else:
        return content

def numeric_col_to_letter_col(col_index: int):
    """
    Examples
    -------------
    0 --> A \n
    25 --> Z \n
    26 --> AA \n
    and so on ...
    """
    if col_index < 26:
        return string.ascii_uppercase[col_index]
    else:
        return numeric_col_to_letter_col(col_index // 26 - 1) + numeric_col_to_letter_col(col_index % 26)

# Testing sheet: https://docs.google.com/spreadsheets/d/1CH5nkNA5-zeeA3wYuU0WRF6Fg4zxg2iJoL3Ti_HGbXc/

if __name__ == "__main__":
    gs = GService()
    g_files = gs.list_files('1OyGEzGwnwsWdvQM9SlDkMHOnLnahpy_y')
    print(g_files)