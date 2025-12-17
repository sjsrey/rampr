import pandas as pd

data_pth = "../data/raw/input_output/"
fname = f"{data_pth}IOUse_After_Redefinitions_PRO_Detail.xlsx"
dfs = pd.read_excel(fname, sheet_name=None)
print(fname, dfs.keys())

use = dfs["2017"]
print(use.shape)

flows = use.values[5:, 2:]
print(flows.shape)

labels = use.values[5:, 0]
print(labels)

columns = use.iloc[4].values[2:]

use_df = pd.DataFrame(data=flows, columns=columns, index=labels).fillna(0)

commodity_names = use.values[5:, 1]
commodity_codes = use.values[5:, 0]
commodity_df = pd.DataFrame(data=use.values[5:, 0:2], columns=["Code", "Description"])

industry_df = pd.DataFrame(use.values[3:5, 3:].T, columns=["Description", "Code"])

make_dfs = dfs = pd.read_excel(
    "../data/raw/input_output/IOMake_After_Redefinitions_PRO_Detail.xlsx",
    sheet_name=None,
)
make = make_dfs["2017"]
columns = make.iloc[4].values[2:]
flows = make.values[5:, 2:]
labels = make.values[5:, 0]
make_df = pd.DataFrame(data=flows, columns=columns, index=labels).fillna(0)

import numpy as np

U = use_df.values[:400, :]
X = use_df.values.sum(axis=0)
Xd = np.diag(1 / (X + (X == 0)))
B = U @ Xd
Q = make_df.values.sum(axis=0)
Qd = np.diag(1 / (Q + (Q == 0)))
D = make_df.values @ Qd

A = D[:-1, :400] @ B
print(A.shape)
print(A[0:5, 1])
A = A[:, :402]
print(A.shape)
L = np.linalg.inv(np.eye(402) - A)
print(L.sum(axis=0))
