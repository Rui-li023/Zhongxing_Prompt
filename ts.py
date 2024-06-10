name = '''
import pandas as pd

# 读取CSV文件
data = pd.read_csv('kpi.csv', encoding='utf-8')

# 获取非指标列名
non_metric_columns = ['开始时间', '粒度', '网元ID', '小区']

# 过滤出指标列并计算数量
metric_columns = [col for col in data.columns if col not in non_metric_columns]
num_metrics = len(metric_columns)

# 输出结果
print([num_metrics])
'''
exec(name)
