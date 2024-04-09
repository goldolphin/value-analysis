# 数据爬虫
import requests
import json
import re
import  pandas as pd

from dataclasses import dataclass
from datetime import datetime

YEAR_BEGIN = 2022

def http_get(url):
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("Failed to retrieve data. Status code:", response.status_code)

@dataclass(unsafe_hash=True, order=True)
class YearQuarter:
    year: int
    quarter: int

    def decode(s: str):
        match = re.match(r'(\d{4})Q([1-4])', s)
        if match:
            year = int(match.group(1))
            quarter = int(match.group(2))
            return YearQuarter(year, quarter)
        else:
            raise Exception(f"Decode error: {s}")
    
    def encode(self):
        return f"{self.year}Q{self.quarter}"

def parse_year_quarter(date_time_str: str):
    date_format = "%Y-%m-%d %H:%M:%S"
    dt = datetime.strptime(date_time_str, date_format)
    year = dt.year
    quarter = (dt.month - 3) // 3 + 1 # 1,2月份发布算上一年Q4，以此类推
    if quarter <= 0:
        year -= 1
        quarter = 4

    return YearQuarter(year, quarter)

def parse_hk_report(data):
    json_data = json.loads(data)
    parsed = pd.DataFrame()
    for item in json_data["result"]["data"]:
        yq = parse_year_quarter(item["REPORT_DATE"])
        if yq.year < YEAR_BEGIN:
            continue
        parsed[yq] = {
            "营收": item["OPERATE_INCOME"],
            "毛利润": item["GROSS_PROFIT"],
            "营业利润": item["OPERATE_PROFIT"],
            "净利润": item["HOLDER_PROFIT"],
            "市值": item["TOTAL_MARKET_CAP"],
            "PE": item["PE_TTM"],
            "股本": item["ISSUED_COMMON_SHARES"]
        }

    res = pd.DataFrame()
    for yq, fd in parsed.items():
        if yq.quarter > 1:
            last_yq = YearQuarter(yq.year, yq.quarter-1)
            last_fd = parsed.get(last_yq)
            if last_fd is None:
                continue
            fd = {
                "营收": fd["营收"] - last_fd["营收"],
                "毛利润": fd["毛利润"] - last_fd["毛利润"],
                "营业利润": fd["营业利润"] - last_fd["营业利润"],
                "净利润": fd["净利润"] - last_fd["净利润"],
                "市值": fd["市值"],
                "PE": fd["PE"],
                "股本": fd["股本"],
            }
        res[yq.encode()] = fd
    return res

def parse_us_report(data):
    json_data = json.loads(data)
    parsed = {}
    for item in json_data["result"]["data"]:
        if not re.match(r'\d{4}/Q[1-4]', item["REPORT"]):
            continue
        yq = parse_year_quarter(item["REPORT_DATE"])
        if yq.year < YEAR_BEGIN:
            continue
        fd = parsed.setdefault(yq.encode(), {})
        if item["STD_ITEM_CODE"] == "004001001":
            fd["营收"] = item["AMOUNT"]
        elif item["STD_ITEM_CODE"] == "004005999":
            fd["毛利润"] = item["AMOUNT"]
        elif item["STD_ITEM_CODE"] == "004009999":
            fd["营业利润"] = item["AMOUNT"]
        elif item["STD_ITEM_CODE"] == "004013999":
            fd["净利润"] = item["AMOUNT"]
        else:
            continue
    return pd.DataFrame(parsed)

def request_hk_report(stock_code: str):
    url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_HKF10_FN_MAININDICATOR&columns=ALL&quoteColumns=&filter=(SECUCODE%3D%22{stock_code}%22)&pageNumber=1&pageSize=9&sortTypes=-1&sortColumns=STD_REPORT_DATE&source=F10"
    data = http_get(url)
    return parse_hk_report(data)

def request_us_report0(stock_code: str):
    url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_USF10_DATA_MAININDICATOR&columns=ALL&quoteColumns=&filter=(SECUCODE%3D%22{stock_code}%22)&pageNumber=1&pageSize=200&sortTypes=-1&sortColumns=REPORT_DATE&source=F10"
    data = http_get(url)
    json_data = json.loads(data)
    parsed = pd.DataFrame()
    for item in json_data["result"]["data"]:
        yq = parse_year_quarter(item["REPORT_DATE"])
        parsed[yq.encode()] = {
            "市值": item["TOTAL_MARKET_CAP"],
            "PE": item["PE_TTM"],
            "股本": item["ISSUED_COMMON_SHARES"]
        }
    return parsed

def request_us_report(stock_code: str):
    url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_USF10_FN_INCOME&columns=SECUCODE%2CSECURITY_CODE%2CSECURITY_NAME_ABBR%2CREPORT%2CREPORT_DATE%2CSTD_ITEM_CODE%2CAMOUNT&quoteColumns=&filter=(SECUCODE%3D%22{stock_code}%22)&pageNumber=1&pageSize=&sortTypes=1%2C-1&sortColumns=STD_ITEM_CODE%2CREPORT_DATE&source=SECURITIES"
    data = http_get(url)
    report = parse_us_report(data)
    report0 = request_us_report0(stock_code)
    fd0 = report0.iloc[:, 0]
    return report.apply(lambda col: pd.concat([col, fd0]))

def request_report(stock_code: str):
    if stock_code.endswith(".HK"):
        return request_hk_report(stock_code)
    elif stock_code.endswith(".O"):
        return request_us_report(stock_code)
    else:
        raise Exception(f"Unknown stock_code: {stock_code}")
    
def save_report(stock_code: str, report: pd.DataFrame):
    report.to_csv(f"data/report.{stock_code}.csv")

def load_report(stock_code: str):
    return pd.read_csv(f"data/report.{stock_code}.csv", index_col=0, skipinitialspace=True)
