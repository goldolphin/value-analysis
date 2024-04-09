import numpy as np

from value_analysis.common import *

# 估值计算过程, 针对传统 DCF 方法有一些变化, 但是总体而言并不关键, 关键的还是前面所说对于"Unstable.期末EPS"的估计
def generalized_dcf(global_params, init_rps, unstable_years, unstable_growth, unstable_margin, rapid_growth):
    """
    计算推广的DCF, 支持对不赢利或赢利不稳定的"年轻"公司的估值. 计算分为两个阶段, 见代码中注释。

    Parameters
    ----------
    
    """
    total_growth_years = global_params["成长阶段总年数"]
    terminal_years = global_params["Terminal.年数"]
    terminal_growth = global_params["Terminal.增长率"]
    discount = global_params["折现率"]

    # 1. 估计 "Unstable.期末EPS", 作为快速成长阶段计算的起点
    unstable_eps = init_rps * (1+unstable_growth) ** unstable_years * unstable_margin

    # 2. 估计 "Rapid.期末EPS", 作为永续阶段计算的起点
    rapid_years = total_growth_years - unstable_years
    rapid_eps = unstable_eps * (1+rapid_growth)**rapid_years

    # 3. 计算内在价值. 
    # 与传统 DCF 方法不同, 从利润留存/分红的角度来考虑, 在这个阶段为了保证快速成长, 绝大部分收益都应投入了扩大生产,
    # 所以并不计入快速成长阶段中的各年收益. 同时, 这样一来成长型行业与低增长型在逻辑上更有可比性(虽然一般不会这么干, 纯是心理作用).
    # 总的来说, 这个调整并不关键, 但因为不计成长阶段收益, 因此最终估值会相对其他一些估值方法偏小.
    q = (1+terminal_growth)/(1+discount) # 中间变量
    fair_values = rapid_eps*q*(1-q**terminal_years) / ((1-q)*(1+discount)**total_growth_years)
    return unstable_eps, rapid_years, rapid_eps, fair_values

# 简易包装
def perform_valuation(global_params, data, current_prices):
    data = data.join(current_prices.rename("现价"))

    # 计算估值
    init_rps = data["期初RPS"]
    unstable_years = data["Unstable.年数"]
    unstable_growth = data["Unstable.增长率"]/100
    unstable_margin = data["Unstable.期末利润率"]/100
    rapid_growth = data["Rapid.增长率"]/100
    unstable_eps, rapid_years, rapid_eps, fair_values = generalized_dcf(global_params, init_rps, unstable_years, unstable_growth, unstable_margin, rapid_growth)
    output = pd.DataFrame({
        "期初RPS" : data["期初RPS"],
        "Unstable.年数" : data["Unstable.年数"],
        "Unstable.增长率" : data["Unstable.增长率"],
        "Unstable.期末利润率" : data["Unstable.期末利润率"],
        "Unstable.期末EPS" : unstable_eps,
        "Rapid.增长率" : data["Rapid.增长率"],
        "Rapid.期末EPS" : rapid_eps,
        "内在价值" : fair_values
    })

    # 代入现价, 比较安全边际
    prices = data["现价"]
    margin_of_safety = (fair_values - prices) / fair_values
    output["现价"] = prices
    output["安全边际%"] = np.array(margin_of_safety.T * 100)
    init_eps = unstable_eps / (1+rapid_growth) ** unstable_years  # 期初估测EPS, 对于成熟公司来说等同于 EPS, 对于不成熟公司来说等于Unstable.期末EPS对增长率进行折算
    output["估测PE"] = prices / np.array(init_eps) # = 现价 / 期初EPS, 对于成熟公司来说等同于 PE
    return output
