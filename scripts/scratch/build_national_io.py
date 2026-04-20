from rampr.io import build_national_io_from_excels
import rampr.datasets as ds

use_xlsx = ds.fetch(
    "bea_make_use_io_tables",
    version="v1",
    files=["IOUse_After_Redefinitions_PRO_Detail.xlsx"],
)[0]

make_xlsx = ds.fetch(
    "bea_make_use_io_tables",
    version="v1",
    files=["IOMake_After_Redefinitions_PRO_Detail.xlsx"],
)[0]

nio = build_national_io_from_excels(use_xlsx=use_xlsx, make_xlsx=make_xlsx, year=2017)

print(nio.A.shape, nio.L.shape)
