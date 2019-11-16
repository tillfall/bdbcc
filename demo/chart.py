from flask import Flask, request, render_template, Markup
from urllib.request import urlopen, Request
from datetime import datetime, timedelta
import json
from flask import Flask, render_template, request
import logging
from datetime import datetime

# fundid = '110022'
# startdate = '2019-01-01'
# enddate = '2019-11-14'
# his_tag = '<fld_unitnetvalue>'
# his_tag_len = len(his_tag)

# headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
# url_template = 'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode=%s&startdate=%s&enddate=%s'
# url = url_template%(fundid, startdate, enddate)
# req = Request(url=url, headers=headers) 
# resp = urlopen(req).read().decode('utf-8')
app = Flask(__name__)

class HistoryValue:
    url_template = 'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode=%s&startdate=%s&enddate=%s'
    headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
    his_tag = '<fld_unitnetvalue>'
    his_tag_len = len(his_tag)
    
    url_template_2 = 'http://hq.sinajs.cn/list=f_%s'
    
    my_funds = '110022,110003,003318'.split(',')
    inputdatefmt = '%y%m%d'
    urldatefmt = '%Y-%m-%d'
    
    def parse_args(self, argstr):
    # <110023,600320;>190204,190504,190807
        secs = argstr.split(';')
        if len(secs) == 2:
            self.funds = self.my_funds + [item.strip() for item in secs[0].split(',')]
            self.dates = secs[1].split(',')
        elif len(secs) == 1:
            self.funds = self.my_funds
            self.dates = secs[0].split(',')
        else:
            raise Exception(argstr)
        self.dates = [item.strip() for item in self.dates]
            
        self.dates.sort()
        self.startdate = datetime.strptime(self.dates[0], self.inputdatefmt)
        self.startdate = self.startdate - timedelta(days=10)  # 10天前，以免遇到节假日
        self.startdate = datetime.strftime(self.startdate, self.urldatefmt)
        # self.enddate = datetime.strftime(datetime.now(), self.urldatefmt)  # 今天，并且加入查询列表
        # 为空，自动查询到最新数据（缺一天）
        # self.dates.append(datetime.strftime(datetime.now(), self.inputdatefmt))
        # 还是用sinajs来查最新的数据
        self.enddate = datetime.strptime(self.dates[-1], self.inputdatefmt)
        self.enddate = datetime.strftime(self.enddate, self.urldatefmt)
        
    @classmethod
    def get_one_date(cls, str, date):
        query_date = datetime.strptime(date, cls.inputdatefmt)
        for i in range(10):
            begin = str.find(datetime.strftime(query_date, cls.urldatefmt))
            if -1 == begin:
                query_date = query_date - timedelta(days=1)
                continue
            begin = str.find(cls.his_tag, begin) + cls.his_tag_len
            end = str.find('</', begin)
            return datetime.strftime(query_date, cls.inputdatefmt), str[begin:end]
            
    def get_all_date(self, str):
        ret = {}
        for date in self.dates:
            d, v = self.get_one_date(str, date)
            ret[d] = v
        return ret
        
    @classmethod
    def get_last_and_name(cls, fundid):
        url = cls.url_template_2 % fundid
        logging.debug(url)
        resp = urlopen(url).read().decode('gbk')
        # var hq_str_f_150065="长盛同瑞B,0.777,1.887,0.781,2019-10-16,0.0183126";
        begin = resp.find('="')+2
        end = resp.find(',',begin)
        name = resp[begin:end]
        
        secs = resp.split(',')
        val = secs[1]
        date = secs[4]
        return name, date, val
        # TODO 获取昨天的数据。hexun没有
        
    def get_one(self, fundid):
        url = self.url_template%(fundid, self.startdate, self.enddate)
        logging.debug(url)
        req = Request(url=url, headers=self.headers) 
        resp = urlopen(req).read().decode('utf-8')
        return resp
        
    def get_all_with_today(self, fundid):
        resp = self.get_one(fundid)
        infos = self.get_all_date(resp)
        # {'190621': '2.7040', '190708': '2.8450', '190930': '2.8860'
        
        name, newdate, newval = self.get_last_and_name(fundid)
        newdate = newdate[2:4]+newdate[5:7]+newdate[8:10]
        infos[newdate] = newval
        # 易方达消费行业股票 {'190621': '2.7040', '190708': '2.8450', '190930': '2.8860', '191016': '2.938'}
        
        keys = sorted(infos.keys())
        valdict = {}
        valdict[keys[0]] = infos[keys[0]]
        preval = float(infos[keys[0]])
        for k in keys[1:]:
            v = float(infos[k])
            diff = (v-preval)/preval*100
            valdict[k] = '%.2f'%diff
        # 易方达消费行业股票 {'190621': '2.7040', '190708': '5.21', '190930': '6.73', '191016': '8.65'}
        
        return name, valdict

    def get_all(self, argstr):
        self.parse_args(argstr)
        
        dates = []
        infos = []
        for fid in self.funds:
            name, values = self.get_all_with_today(fid)
            infos.append([name, fid, values])
            dates.extend(values.keys())
            
        dates = sorted(set(dates))
        ret = '<tr><td>name</td><td>id</td><td>' + '</td><td>'.join(dates) + '</td></tr>'
        
        for info in infos:
            infostr = '<tr><td>'+info[0]+'</td><td>'+info[1]+'</td>'
            for d in dates:
                infostr += '<td>'
                v = info[2].get(d)                
                infostr += v if v else ''
                infostr += '</td>'
            infostr += '</tr>'
            ret += infostr
            
        ret = '<table border="1">' + ret + '</table>'
        
        # dict.get(key)
        return Markup(ret) # 取消渲染时转义


####################################################

    def one_fund_all_history(self, fund_id, startdate):
        date_tag = '<fld_enddate>'
        date_tag_len = len(date_tag)

        self.startdate = startdate
        self.enddate = datetime.now().strftime('%Y-%m-%d')
        resp = self.get_one(fund_id)
        val_dict = {}
        secs = resp.split('</Data>')[:-1]
        for sec in secs:
            begin1 = sec.index(date_tag)+date_tag_len
            end1 = sec.index('</', begin1)
            begin2 = sec.index(self.his_tag)+self.his_tag_len
            end2 = sec.index('</', begin2)
            val_dict[sec[begin1:end1]] = float(sec[begin2:end2])

        name, date, val = self.get_last_and_name(fund_id)
        val = float(val)
        val_dict[date] = val

        return name, val_dict, val

    def one_fund_all_history_percent(self, fund_id, startdate):
        name, val_dict, last_val = self.one_fund_all_history(fund_id, startdate)
        first_day = val_dict[min(val_dict.keys())]
        for val_key in val_dict.keys():
            val_dict[val_key] = round((val_dict[val_key] - first_day)/first_day*100, 2)
        return name, first_day, last_val, val_dict

    @staticmethod
    def set_buy_records(buy_dict, history_dict, first_val, last_val): # {date: [$, share]}, {date: %}
        total_money = 0
        total_share = 0
        buy_point = {}
        buy_val = {}
        for buy_date, buy_info in buy_dict.items():
            if 0 == buy_info[0]:
                continue
            # 总投入
            total_money += buy_info[0]
            # 总份额
            total_share += buy_info[1]
            # 折线图上的点
            buy_point[buy_date] = history_dict[buy_date]
            # 折线图上的值
            buy_val[buy_date] = buy_info[0]

        if 0 == total_share:
            buy_cost_percent = 0
            buy_remain = 0
            buy_remain_percent = 0
        else:
            buy_cost = total_money/total_share
            buy_cost_percent = round((buy_cost - first_val)/first_val*100, 2)
            buy_remain = int(last_val * total_share - total_money)
            buy_remain_percent = round(buy_remain/total_money*100, 2)

        # 当前净值%首日    收益    收益率    买卖点    买卖金额
        return buy_cost_percent, buy_remain, buy_remain_percent, buy_point, buy_val
    
from pyecharts.charts import Line
import pyecharts.options as opts
from pyecharts.globals import SymbolType

class Buy2LineChart:
    @staticmethod
    def one_fund_line(fund_id, buy_records, first_day=''): # {date: [$, share]}
        if '' == first_day:
            first_day = min(buy_records.keys())
        name, first_val, last_val, his_dict = HistoryValue().one_fund_all_history_percent(fund_id, first_day)
        buy_cost_percent, buy_remain, _, buy_point, buy_val = HistoryValue.set_buy_records(buy_records, his_dict, first_val, last_val)

        p1 = sorted(his_dict.keys())  # 日期排序
        p2 = fund_id+name
        p3 = [his_dict.get(x) for x in p1] # 当日比首日涨幅
        p4 = opts.MarkLineOpts(data=[opts.MarkLineItem(y=buy_cost_percent)]) # 买入均价比首日涨幅
        p5 = []
        # 买卖点
        for a_buy_date in buy_point.keys():
            if buy_val[a_buy_date] > 0:
                p5.append(opts.MarkPointItem(coord=[a_buy_date, buy_point[a_buy_date]], value=buy_val[a_buy_date], symbol=SymbolType.ARROW))
            else:
                p5.append(opts.MarkPointItem(coord=[a_buy_date, buy_point[a_buy_date]], value=buy_val[a_buy_date]))
        # 最新收益
        last_x = max(his_dict.keys())
        last_y = his_dict[last_x]
        p5.append(opts.MarkPointItem(coord=[last_x, last_y], value=buy_remain, symbol=SymbolType.DIAMOND))
        
        return p1, p2, p3, p4, opts.MarkPointOpts(data=p5)

    @staticmethod
    def fund_line(buy_record_dict): # {fund_id: {date: [$, share]}}
        first_day = 'a'
        for fund_info in buy_record_dict.values():
            first_day = min(first_day, min(fund_info.keys()))
        ret = {}
        for fund_id, buy_records in buy_record_dict.items():
            p1, p2, p3, p4, p5 = Buy2LineChart.one_fund_line(fund_id, buy_records, first_day)
            ret[fund_id] = [p1, p2, p3, p4, p5]
        return ret

# class LineFundHistory:
#     fund_id = ''
#     fund_name = ''
#     fund_value = {} # {date: value}
#     first_day_value = 0
#     def __init__(self, fund_id, fund_name, fund_value):
#         self.fund_id = fund_id
#         self.fund_name = fund_name
#         self.first_day_value = fund_value[min(fund_value.keys())]
#         for a_date, a_value in fund_value.items():
#             self.fund_value[a_date] = round(100*(a_value - self.first_day_value)/self.first_day_value, 2)
# class LineFundHistoryAndBuy:
#     fund_history = None
#     fund_buy = {} # {date: [$, %]}
#     fund_cost = 0
#     def __init__(self, fund_history, buy_dict): # {date: [$, share]}
#         self.fund_history = fund_history
#         total_money = 0
#         total_share = 0
#         for a_date, a_buy in buy_dict.items():
#             self.fund_buy[a_date] = [a_buy[0], self.fund_history.fund_value[a_date]]
#             total_money += a_buy[0]
#             total_share += a_buy[1]
#         total_value = total_money / total_share
#         self.fund_cost = round(100*(total_value - fund_history.first_day_value)/fund_history.first_day_value, 2)
# class LineFund:
#     @staticmethod
#     def to_line_chart(a_fund):
#         p1 = a_fund.fund_history.fund_id+a_fund.fund_history.fund_name
#         p2 = list(a_fund.fund_history.fund_value.values())
#         p3 = opts.MarkLineOpts(data=[opts.MarkLineItem(y=a_fund.fund_cost)])
#         p4 = []
#         for a_buy_date, a_buy_info in a_fund.fund_buy.items():
#             if a_buy_info[0] > 0:
#                 p4.append(opts.MarkPointItem(coord=[a_buy_date, a_buy_info[1]], value=a_buy_info[0], symbol=SymbolType.ARROW))
#             else:
#                 p4.append(opts.MarkPointItem(coord=[a_buy_date, a_buy_info[1]], value=a_buy_info[0]))
#         return p1, p2, p3, opts.MarkPointOpts(data=p4)
    

def line():
    # lfh = LineFundHistory('1','1',{'19-1-1':1.1, '19-1-2':1.2, '19-1-3':1.05, '19-1-4':1.25, '19-1-5':1.2})
    # lfhb = LineFundHistoryAndBuy(lfh, {'19-1-1':[111,100], '19-1-2':[-59,-50], '19-1-3':[108,100]})
    # p1,p2,p3,p4 = LineFund.to_line_chart(lfhb)
    buy_records = {
        '003318': {
            '2019-08-30':[45000,48955.51], '2019-09-06':[20000,20856.15], '2019-09-09':[50000,51357.53],
            '2019-09-10':[50000,51527.1], '2019-09-17':[50000,52518.74], '2019-10-30':[10000,10821.24]
        },
        '110003': {
            '2019-11-11':[10000,5521.77], '2019-11-08':[10000,5435.2], '2019-09-20':[1800,1011.87], 
            '2019-09-17':[50000,28525.37], '2019-09-16':[1800,1017.37], '2019-09-10':[50000,28131.57], 
            '2019-09-09':[50000,28035.21], '2019-09-06':[1800,1008.64], '2019-08-30':[1800,1034.23], 
            '2019-08-23':[1800,1022.99], '2019-08-16':[1800,1054.62], '2019-08-09':[1800,1082.05], 
            '2019-08-02':[1800,1063.49], '2019-07-26':[1800,1032.75], '2019-07-19':[1800,1046.52], 
            '2019-07-12':[1800,1040.4], '2019-07-08':[4000,2335.81], '2019-07-05':[1800,1029.2], 
            '2019-06-28':[1800,1051.11], '2019-06-21':[1800,1060.97], '2019-06-14':[1800,1116.12], 
            '2019-06-10':[1800,1141.57], '2019-05-31':[1000,634.97], '2019-05-30':[1000,633], 
            '2019-05-23':[800,516.45], '2019-05-22':[800,508.88], '2019-05-20':[800,512.47], 
            '2019-05-17':[5000,3167.43], '2019-05-14':[400,255.66], '2019-05-13':[800,508.72], 
            '2019-05-10':[1800,1131.44], '2019-05-06':[6600,4166.2], '2019-04-26':[1600,978.66], 
            '2019-04-25':[3000,1813.48], '2019-04-22':[5000,2998.5], '2019-04-19':[1600,938.32], 
            '2019-04-18':[1000,593.32], '2019-04-12':[1600,975.87], '2019-04-11':[2000,1213.9], 
            '2019-04-09':[1000,594.87], '2019-04-08':[1000,603.72], '2019-03-29':[1800,1128.03], 
            '2019-03-22':[1600,1035.65], '2019-05-15':[1800,1189.87], '2019-03-08':[1800,1235.17], 
            '2019-02-28':[2000,1315.46], 
        },
        }
    chart_data = Buy2LineChart.fund_line(buy_records)
    # p1, p2, p3, p4, p5 = chart_data[0],chart_data[1],chart_data[2],chart_data[3],chart_data[4]
    # p1, p2, p3, p4, p5 = Buy2LineChart.one_fund_line('003318', buy_records, '2019-07-20')

    line_data = Line()
    for chart_data_key, chart_data_val in chart_data.items():
        p1, p2, p3, p4, p5 = chart_data_val[0],chart_data_val[1],chart_data_val[2],chart_data_val[3],chart_data_val[4]
        line_data = line_data.add_xaxis(p1).add_yaxis(p2, p3, markline_opts=p4, markpoint_opts=p5)
    c = (line_data)
    # c = (
    #     Line()
    #     .add_xaxis(p1).add_yaxis(p2, p3, markline_opts=p4, markpoint_opts=p5)
        # Line()
        # .add_xaxis(['苹果','香蕉','凤梨','桔子','橙','桃子'])
        # .add_yaxis("商家A", [1,2,3,4,5,6], 
            # markpoint_opts=opts.MarkPointOpts(data=[
                # opts.MarkPointItem(coord=['凤梨', 3], value=3, symbol=SymbolType.ARROW),
                # opts.MarkPointItem(coord=['橙', 5], value=5),
                # ]),
            # markline_opts=opts.MarkLineOpts(data=[
                # opts.MarkLineItem(y=1.4)
                # ]))
        # .add_yaxis("商家B", [5,4,3,2,1], markline_opts=opts.MarkLineOpts(data=[opts.MarkLineItem(y=1.4)]))
    # )
    return c

@app.route("/")
def index():
    return render_template("chart.html")
    
@app.route("/lineChart")
def get_bar_chart():
    c = line()
    return c.dump_options_with_quotes()

if __name__ == "__main__":
    app.run(debug=True)
    # buy_records = {'2019-08-30':[45000,48955.51], '2019-09-06':[20000,20856.15], '2019-09-09':[50000,51357.53],
    #     '2019-09-10':[50000,51527.1], '2019-09-17':[50000,52518.74], '2019-10-30':[10000,10821.24]}
    # name, first_val, last_val, his_dict = HistoryValue().one_fund_all_history_percent('003318','2019-08-30')
    # buy_cost_percent, buy_remain, buy_remain_percent, buy_point, buy_val = HistoryValue.set_buy_records(buy_records, his_dict, first_val, last_val)
    # print(name, first_val, last_val, buy_remain, buy_remain_percent, buy_cost_percent, his_dict, buy_point, buy_val)