from re import U
from textwrap import wrap

from attr import s

from pyfreeleh.providers.google import OAuth2GoogleAuthClient
from pyfreeleh.kv import GoogleSheetKVStore

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

auth_client = OAuth2GoogleAuthClient.from_authorized_user_file(
    "token.json",
    client_secret_filename="credentials.json",
    scopes=SCOPES,
)

# wrapper = GoogleSheetWrapper(auth_client)
# print(wrapper.create_spreadsheet("test"))

spreadsheet_id = "1DOp-O87JU3zmpb9q_VcyKPYShNQytpKptZJFJc-bxdY"
# wrapper.create_sheet(spreadsheet_id, "tmp")

# update = wrapper.insert_rows(spreadsheet_id, A1Range.from_notation("A1"), [["gg1", "ez"]])
# print(update)

# wrapper.clear(spreadsheet_id, ranges=[A1Range.from_notation("A2:B2")])
# print(wrapper.update_rows(spreadsheet_id=spreadsheet_id, range=A1Range.from_notation("A1"), values=[["haha"]]))

kv = GoogleSheetKVStore(auth_client, spreadsheet_id, "data")

import code

code.interact(local=locals())
