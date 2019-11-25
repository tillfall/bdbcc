# -*- coding:utf-8 -*-
__version__ = '2019-11-19'

from flask import Flask, request, render_template, Markup
from urllib.request import urlopen, Request
from datetime import datetime, timedelta
import json
import time
from pyecharts.charts import Line
import pyecharts.options as opts
from pyecharts.globals import SymbolType

import logging
logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%y-%m-%d %H:%M:%S',
                filename='app.log',
                filemode='a')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def get_conf():
    return json.loads(urlopen('https://tillfall.github.io/conf.json').read().decode('utf-8'))

app = Flask(__name__)

########################################

class RealtimeValue:
    conf = get_conf()
    url_template = conf['基金']['大盘净值']
    # 上证50,000016,中证500,000905，沪深300,000300，上证综指999999，深证成指399001，中小板399005，创业板399006
    index_ids = 'sh000001,sh000016,sh000905,sz399006,sz399001'
    chart_tmplate = '''<tr><td>
    <img src="%s"></img>
    <img src="%s"></img>
    </td></tr>
    ''' % (conf['基金']['基金日K线'], conf['基金']['基金实时曲线'])
    
    @classmethod
    def get_one(cls, id):
        try:
            url = cls.url_template % id
            logging.debug(url)
            resp = urlopen(url).read().decode('gbk')
            # var hq_str_s_sh000001="上证指数,2991.0459,-16.8375,-0.56,1553769,16953193";\n
            begin = resp.index('="') + 2
            end = resp.index('";')
            # 上证指数,2991.0459,-16.8375,-0.56,1553769,16953193
            data = resp[begin:end]
            secs = data.split(',')
            
            # id, 上证指数, 指数, 涨幅, 成交量
            return [id[-6:], secs[0], str(int(float(secs[1]))), secs[3], secs[5][:-4]]
        except:
            return [id[-6:]] + ['ERR']*4
                
    fund_url_template = conf['基金']['基金实时']
    fund_index_ids = '110022,110003,003318'
    @classmethod
    def get_one_fund(cls, id):
        url = cls.fund_url_template%id
        logging.info(url)
        req = urlopen(url).read().decode('utf-8')
        reqjson = json.loads(req[8:-2])
        return [reqjson['fundcode'], reqjson['name'], reqjson['gszzl'], reqjson['gztime'][5:]]

    @classmethod
    def get_all(cls):
        ids = cls.index_ids.split(',')
        all_data = [cls.get_one(id) for id in ids]
        ret = '<style>td {font-size: 4vw;}</style><a href="/fund">BACK</a><table border="1"><tr><td>id</td><td>指数名称</td><td>指数</td><td>涨幅</td><td>成交量</td></tr>'
        for data in all_data:
            ret += '<tr><td>' + '</td><td>'.join(data) + '</td></tr>'
            
        all_fund_data = [cls.get_one_fund(id) for id in cls.fund_index_ids.split(',')]
        for afund_data in all_fund_data:
            ret += '<tr><td>'+afund_data[0]+'</td><td>'+afund_data[1][:10]+'</td><td></td><td>'+afund_data[2]+'</td><td>'+afund_data[3]+'</td></tr>'
        
        ret += '</table>'
        
        ret += '<table border="1">' + ''.join([cls.chart_tmplate%(id, id) for id in ids]) + '</table>'
        
        return ret

@app.route("/realtime")
def realtime_value():
    return RealtimeValue.get_all()
    
#######################################

class HistoryValue:
    conf = get_conf()
    url_template = conf['基金']['基金历史']
    headers = {'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'}
    his_tag = '<fld_unitnetvalue>'
    his_tag_len = len(his_tag)
    
    url_template_2 = conf['基金']['基金净值']
    
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
    
    ####################################

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

@app.route('/history', methods=['GET'])
def history_value():
    inputText = request.args.get("input_text", default='')
    if '' == inputText:
        resText = HistoryValue().get_all('190101,190401,190701,191001') # 默认查询季度值
    else:
        resText = HistoryValue().get_all(inputText)
    return render_template('query.html', query_url='/history', input_text=inputText, res_text=resText, 
        hint='<110022,110003;>190602,190823')

class IndexHistory:
    @staticmethod
    def get_history(startdate):
        url = get_conf()['基金']['大盘历史'] % (startdate.replace('-', ''))
        page=urlopen(Request(url)).read().decode('gb2312')
        # 每天一条记录，然后按日期排列，然后转换成float
        vals = sorted(page.split('\r\n')[1:-1])
        vals = [float(x.split(',')[-1]) for x in vals]
        # first_val = vals[0]
        # # 只保留涨幅
        # return [round((x-first_val)/first_val*100, 2) for x in vals]
        return vals

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

@app.route("/line")
def chart():
    return render_template("chart.html")
    
@app.route("/lineChart")
def get_bar_chart():
    chart_data = Buy2LineChart.fund_line(get_conf()['基金']['基金购买记录'])
    line_data = Line()

    all_date = None

    for _, chart_data_val in chart_data.items():
        p1, p2, p3, p4, p5 = chart_data_val[0],chart_data_val[1],chart_data_val[2],chart_data_val[3],chart_data_val[4]
        line_data = line_data.add_xaxis(p1).add_yaxis(p2, p3, markline_opts=p4, markpoint_opts=p5)
        all_date = p1
        
    # 双轴，副轴为上证指数
    index_vals = IndexHistory.get_history(all_date[0])
    # min_axis, max_axis = min(index_vals), max(index_vals)
    # last_x, last_y, last_val = all_date[-1], int(index_vals[-1]-2900), index_vals[-1]
    # print(last_x, last_y, last_val)
    sh_index = Line().add_xaxis(all_date).add_yaxis('上证指数', [int(x-2900) for x in index_vals], 
    # markline_opts=[100], 
        # markpoint_opts=[opts.MarkPointItem(coord=[last_x, last_y], value=last_val, symbol=SymbolType.RECT)],
        yaxis_index=1)
        # .extend_axis(yaxis=opts.AxisOpts(min_=[min_axis], max_=[max_axis]))
    line_data.extend_axis(yaxis=opts.AxisOpts(interval=50)).overlap(sh_index)
    # see: http://pyecharts.org/#/zh-cn/rectangular_charts

    c = (line_data)
    return c.dump_options_with_quotes()


##########################################
@app.route('/url')
def myurl():
    us = [
        ['异次元软件', 'https://www.iplaysoft.com/', '#tech#', ''],
        ['小众软件', 'https://www.appinn.com/', '#tech#', ''],
        
        ['☆126', 'https://mail.126.com/', '#pim#', '[t/m/139]'],
        ['☆百度网盘', 'https://pan.baidu.com/', '#pim#', '[t/w][135/w][parentshare@126/parentshare]'],
        ['☆有道云', 'http://note.youdao.com/', '#pim#', '[t@126/m]'],
        ['☆印象笔记', 'https://www.yinxiang.com/', '#pim#', '[t/m]'],
        ['☆石墨文档', 'https://shimo.im/desktop', '#pim#', '[t@126/Wg]'],
        ['☆新浪微博', 'https://weibo.cn/', '#pim#', '[t/Wg/139]'],
        ['为知', 'http://www.wiz.cn/', '#pim#', '[t@126/t]'],
        ['wps', 'http://www.wps.cn/', '#pim#', '[t@125/w]'],
        ['hotmail', 'https://outlook.live.com/owa/', '#pim#', '[tf_z/M.6]'],
        ['市民信箱', 'http://www.eshimin.com/index.jsp', '#pim#', '[t/m]'],
        ['腾讯', 'https://www.qq.com/', '#pim#', '[M.6]'],
        ['360', 'https://www.360.cn/', '#tech#', '[t@126/t]'],
        ['UC浏览器', 'http://www.uc.cn/', '#pim#', '[sina]'],

        ['兰图绘', 'http://www.ldmap.net', '#travel#', '[t@126/t]'],
        ['12306', 'http://www.12306.cn/mormhweb/', '#travel#', '[t/w/t@126]'],
        ['去哪儿', 'https://www.qunar.com/', '#travel#', '[t/w/1@126]'],
        ['蚂蜂窝', 'http://www.mafengwo.cn/', '#travel#', '[t@126/t]'],
        ['春秋', 'https://www.ch.com/', '#travel#', '[135/5]'],
        ['携程', 'http://www.ctrip.com/', '#travel#', '[135/7861]'],
        ['同程', 'https://www.ly.com/', '#travel#', '[139/139]'],
        ['亚航', 'https://www.airasia.com/zh/cn?cid=1', '#travel#', '[t/M.1]'],
        ['图虫', 'https://tuchong.com/', '#travel#', '[139]'],
        ['中国徒步网', 'http://www.chinawalking.net.cn/', '#travel#', ''],
        ['上海展会', 'http://shanghai.eshow365.com/', '#travel#', ''],
        ['东航', 'http://www.ceair.com/', '#travel#', '[139/后8]'],
        
        ['知乎', 'https://www.zhihu.com/signin?next=%2F', '#life#', '[139]'],
        ['mp4ba', 'http://mp4ba.com', '#media#', ''],
        ['电影天堂', 'http://www.dytt8.net/index.htm', '#media#', ''],
        ['天天美剧', 'http://www.ttmeiju.vip/', '#media#', '[t/t/t@126]'],
        ['BT之家', 'http://www.btbtt.com/', '#media#', ''],
        ['喜马拉雅听书', 'http://ximalaya.com', '#media#', '[sina]'],
        
        ['大众点评', 'http://www.dianping.com/', '#buy#', '[x@hot/5]'],
        ['淘宝', 'https://www.taobao.com/', '#buy#', '[t@hot/M.6/M.3]'],
        ['京东', 'https://www.jd.com/', '#buy#', '[t/M.6/M.3]'],
        ['华为商城', 'https://www.vmall.com/', '#buy#', '[139][内购：hw/M.1]'],
        ['小米', 'http://mi.com', '#buy#', '[139/2/139@126]'],
        ['自如网', 'http://sh.ziroom.com/', '#life#', '[139/后8]'],
        ['浦发', 'https://www.spdb.com.cn/', '#money#', '[1110385279/2]'],
        ['建行', 'http://www.ccb.com/cn/home/indexv3.html', '#money#', '[t/z2]'],
        ['农行', 'http://www.abchina.com/cn/', '#money#', '[139/M.1]'],
        ['中国银行', 'http://www.boc.cn/', '#money#', '[t/m.1]'],
        
        ['猎聘网', 'https://www.liepin.com/', '#job#', '[t@126/t]'],
        ['LinkedIn', 'https://www.linkedin.com/feed/', '#job#', '[1@126/139]'],
        ['个人信用信息服务', 'https://ipcrs.pbccrc.org.cn/', '#life#', '[t/Wg]'],
        ['社保', 'http://rsj.sh.gov.cn/sbsjb/wzb/226.jsp', '#life#', '[2]'],
        ['交警', 'https://sh.122.gov.cn/', '#life#', '[z:139][x:w.n23]'],
        ['上海医保', 'http://ybj.sh.gov.cn/xxcx/search02_01.jsp', '#life#', '[2][5]'],
        ['住房公积金', 'https://persons.shgjj.com/gjjweb/#/app', '#life#', '[t/m][c.a/5]'],
        ['挂号网', 'https://www.guahao.com/', '#life#', '[t@126/t]'],
        ['上海图书馆', 'http://www.libnet.sh.cn/zxtsg/', '#life#', '[13229348]'],
        
        ['ProcessOn', 'https://www.processon.com/', '#tech#', '[t@126/Wg]'],
        ['jsform', 'https://www.bangboss.com/', '#pim#', '[t@126/Wg]'],
        ['pinbox', 'https://withpinbox.com/items', '#pim#', '[t@126/t]'],
        ['好网角', 'https://www.wang1314.com/', '#pim#', '[sina]'],
        ['github', 'https://github.com/', '#tech#', '[t/wengu]'],
        ['LeetCode', 'https://leetcode-cn.com/', '#tech#', '[t/t/t@126]'],
        ['微软软件', 'http://msdn.itellyou.cn/', '#tech#', ''],
        ['高德地图API', 'http://lbs.amap.com/console/show/picker', '#travel#', '[t/t]'],
        ['mp3合并', 'https://audio-joiner.com/cn/', '#media#', ''],
        ['图标下载', 'https://www.easyicon.net/', '#tech#', ''],
        ['MBTI职业性格', 'http://www.apesk.com/mbti/dati.asp', '#job#', ''],
        ['DDNS-PubYun-3322', 'http://pubyun.com/', '#tech#', '[t/t]'],
        
        ['Testing Map', 'http://thetestingmap.org/', '#tech#', ''],
        ['软件测试的两张藏宝图和三个层次', 'https://blog.csdn.net/kerryzhu/article/details/4134379', '#tech#', ''],
        ['2013流行Python项目', 'https://www.iteye.com/news/28717-2013-top-python-projects', '#tech#', ''],
        ['Android 手机自动化测试工具', 'https://www.zhihu.com/question/19716849', '#tech#', ''],
        ['Devops Tools', 'https://www.jianshu.com/p/3b5e1fc2a54b', '#tech#', ''],
        
        ['上图-zz', 'http://www.library.sh.cn/', '#zz#', '[13958481/zzid]'],
        ['六师附小[无法访问]', 'http://www.lsfx.pudong-edu.sh.cn/infoweb/', '#zz#', '[zpc/5]'],
        ['打字练习', 'https://www.keybr.com/', '#zz#', ''],
        ['打字练习', 'http://www.dazima.cn/flash/', '#zz#', ''],
        ]
    return '<title>URL</title><style>td {font-size: 4vw;}</style><table>' + \
        ''.join('<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>'%(i[1],i[0],i[2],i[3]) for i in us) \
        + '</table>'''
        
#########################################

@app.route('/map')
def map():
    return render_template('map.html')

#########################################

@app.route('/notify')
def notify():
    with open('notify', 'w') as f:
        f.write(str(datetime.now()))
    return 'ok'
# curl 106.13.188.142:6789/notify
# service cron restart
# http://c.biancheng.net/view/1092.html

@app.route('/getnotify')
def getnotify():
    with open('notify', 'r') as f:
        return f.readline()

##########################################

class FlightCtrip:
    conf = get_conf()
    url_template = conf['旅游']['携程机票']
    city = conf['旅游']['机场代码']
    sh_city = ['上海', 'SHA']
    
    @classmethod
    def getprice(cls, dcitycode, acitycode, date):
        try:
            url = cls.url_template % (dcitycode, acitycode)
            req = urlopen(url).read().decode('gbk')
            return str(json.loads(req)['Prices'][date])
        except:
            return 'NA'
            
    @classmethod
    def getprice_all(cls, fromdate, backdate):
        ret = []
        for k, v in cls.city.items():
            fromprice = cls.getprice(cls.sh_city[1], v, fromdate)
            backprice = cls.getprice(v, cls.sh_city[1], backdate)
            ret.append([k, fromprice, backprice])
        return ret
            
    @classmethod
    def getpricetab(cls, fromdate, backdate):
        all_data = cls.getprice_all(fromdate, backdate)
        ret = '<table><tr><td></td><td>'+fromdate+'</td><td>'+backdate+'</td></tr>'
        for a_data in all_data:
            a_data[0] = '<a href="/flights_city?input_text=%s">%s</a>'%(a_data[0],a_data[0])
            ret += '<tr><td>' + '</td><td>'.join(a_data) + '</td></tr>'
        ret += '</table>'
        return Markup(ret)
        
    @classmethod
    def getprice_onecity(cls, acity):
        try:
            acitycode = cls.city[acity]
            go_url = cls.url_template%(cls.sh_city[1], acitycode)
            go_req = urlopen(go_url).read().decode('gbk')
            go_price = json.loads(go_req)['Prices']
            
            back_url = cls.url_template%(acitycode, cls.sh_city[1])
            back_req = urlopen(back_url).read().decode('gbk')
            back_price = json.loads(back_req)['Prices']
            
            dates = sorted(set(go_price.keys()) | set(back_price.keys()))
            ret = '<table><tr><td>日期</td><td>去</td><td>回</td></tr>'
            for adate in dates:
                ret += '<tr><td>'+adate+'</td><td>'+str(go_price.get(adate))+'</td><td>'+str(back_price.get(adate))+'</td></tr>'
            ret += '</table>'
            return Markup(ret)
        except:
            return 'NA'
        
@app.route('/flights', methods=['GET'])
def get_flights():
    inputText = request.args.get("input_text", default='')
    if '' == inputText:
        resText = ''
    else:
        dates = inputText.split(',')
        resText = FlightCtrip.getpricetab(dates[0].strip(),dates[1].strip())
    return render_template('query.html', query_url='/flights', input_text=inputText, res_text=resText, 
        hint='2020-01-03,2020-01-05')

@app.route('/flights_city', methods=['GET'])
def get_flights_city():
    inputText = request.args.get("input_text", default='')
    if '' == inputText:
        resText = ''
    else:
        resText = FlightCtrip.getprice_onecity(inputText)
    return render_template('query.html', query_url='/flights_city', input_text=inputText, res_text=resText, 
        hint='北京')

#######################################

@app.route('/fund')
def index():
    return '<title>FUND</title><style>td {font-size: 4vw;}</style><table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/realtime':'指数实时', '/history':'基金历史', '/line':'购买记录'}\
        .items()]) + '</td></tr></table>'
        
@app.route('/')
def home():
    return '<title>HOME</title><style>td {font-size: 4vw;}</style><table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/fund':'基金', '/url':'网址', '/flights':'航班-多城市', '/flights_city':'航班-单城市', 'https://tillfall.github.io/map.html':'地图', '/getnotify':'检查同步时间'}\
        .items()]) + '</td></tr></table><hr>version: ' + __version__

#########################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)

    # req = urlopen('https://tillfall.github.io/conf.json').read().decode('utf-8')
    # reqjson = json.loads(req)
    # print(reqjson['基金']['基金购买记录'])