from pyfreeleh.kv import GoogleSheetKVStore
from pyfreeleh.providers.google import OAuth2GoogleAuthClient
from pyfreeleh.providers.google.sheet.base import A1Range, BatchUpdateRowsRequest
from pyfreeleh.providers.google.sheet.wrapper import GoogleSheetWrapper
from pyfreeleh.row.gsheet import GoogleSheetRowStore, InsertStmt, Ordering, SelectStmt, UpdateStmt

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

w = GoogleSheetWrapper(auth_client)
# print(w.query(spreadsheet_id, "data", "select *"))
# w.batch_update_rows(spreadsheet_id, [BatchUpdateRowsRequest("A1", [["halo"]])])
# kv = GoogleSheetKVStore(auth_client, spreadsheet_id, "data")

store = GoogleSheetRowStore(auth_client, spreadsheet_id, "data", ["name", "description", "price"])

# print(store.select().where("name = ?", "fata").execute())

store.insert(
    [
        {
            "name": "fata2",
            "description": "hala madrid",
        }
    ]
).execute()
print(store.select().where("name = ?", "fata2").execute())

store.update({"price": 1234, "description": "yay"}).where("name = ?", "fata2").execute()

store.delete().execute()
store.close()

# col_mapping = {"date": "A", "datetime": "B", "string": "C", "number": "D", "bool": "E", "timeofday": "F"}
# # stmt = SelectStmt(wrapper=w, col_mapping=col_mapping, spreadsheet_id=spreadsheet_id, sheet_name="data")
# # print(stmt.limit(5).offset(0).order_by(number=Ordering.DESC).execute())

# # stmt = InsertStmt(
# #     wrapper=w, col_mapping=col_mapping, rows=[col_mapping], spreadsheet_id=spreadsheet_id, sheet_name="data"
# # )
# # stmt.execute()
# update_stmt = UpdateStmt(
#     wrapper=w,
#     val={"timeofday": "hehe"},
#     col_mapping=col_mapping,
#     spreadsheet_id=spreadsheet_id,
#     sheet_name="data",
#     scratchpad_cell=A1Range.from_notation("data_scratch!A1:A1"),
# )
# update_stmt.where("string = ?", "to_update")
# update_stmt.execute()

# import code

# code.interact(local=locals())
