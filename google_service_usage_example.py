from google_service import GService, df_to_value_range, numeric_col_to_letter_col
import pandas as pd

# Testing sheet: https://docs.google.com/spreadsheets/d/1CH5nkNA5-zeeA3wYuU0WRF6Fg4zxg2iJoL3Ti_HGbXc/
gsheet_id = '1CH5nkNA5-zeeA3wYuU0WRF6Fg4zxg2iJoL3Ti_HGbXc' 

g_service = GService() # Initialization step, only needs to be done once

# Get the names of sheet in the gsheet
sheet_names = g_service.get_sheet_names(gsheet_id)

# Adding sheet
g_service.add_sheet(gsheet_id, 'Sheet1')

# Writing pandas df to existing sheet
df = pd.DataFrame({'column_name':['hello world']})
g_service.write_google_sheet(gsheet_id, 'Sheet1!A1', df_to_value_range(df))

# Writing to existing sheet
g_service.write_google_sheet(gsheet_id, 'Sheet1!A1', [['A1','B1'],['A2','B2']])

# Appending to existing sheet
g_service.append_google_sheet(gsheet_id, 'Sheet1!A1', [['A3','B3']])

# Appending dataframe to existing sheet
g_service.append_google_sheet(gsheet_id, 'Sheet1!A1', df_to_value_range(df, include_header=False))

# Reading gsheet into pandas df
df = g_service.read_google_sheet(gsheet_id, 'Sheet1!A1:B3')

# Get sheet dimension
row_count, column_count = g_service.get_sheet_dimension(gsheet_id, 'Sheet1')

# Get sheet_id
sheet_id = g_service.get_sheet_id(gsheet_id, 'Sheet1')
print(sheet_id)

# Add dropdown validation to cells
g_service.add_dropdown_validation(
    gsheet_id = gsheet_id,
    sheet_id = sheet_id,
    start_col = 0,
    end_col = 2,
    start_row = 0,
    end_row = 2,
    values = ['Normal','Freeze','Ban'],
    input_msg = 'Please select an action',
    strict = False
)

# Delete rows
g_service.delete_row(gsheet_id, sheet_id, 0, 2)

# Clear sheet
g_service.clear_google_sheet(gsheet_id, 'Sheet1!A1:B3')

# Delete sheet
g_service.delete_sheet(gsheet_id, sheet_id)

# Converting column number to alphabet
column_number = 26
column_alphabet = numeric_col_to_letter_col(column_number)
print(column_alphabet)