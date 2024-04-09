import io
import pandas as pd

def read_csv(csv_str):
    return pd.read_csv(io.StringIO(csv_str), comment='#', index_col=0, skipinitialspace=True)

stock_table = read_csv(
"""
名称,    代码,       外汇
网易,    09999.HK,  HKD
腾讯,    00700.HK,  HKD
快手,    01024.HK,  HKD
京东,    09618.HK,  HKD
美团,    03690.HK,  HKD
拼多多,  PDD.O,     USD
苹果,    AAPL.O,
微软,    MSFT.O,
英伟达,  NVDA.O,
"""
)
