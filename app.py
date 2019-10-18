# -*- coding:utf-8 -*-
from flask import Flask, request, render_template, Markup
from urllib.request import urlopen, Request
from datetime import datetime, timedelta

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

app = Flask(__name__)

########################################

class RealtimeValue:
    url_template = 'http://hq.sinajs.cn/list=s_%s'
    # 上证50,000016,中证500,000905，沪深300,000300，上证综指999999，深证成指399001，中小板399005，创业板399006
    index_ids = 'sh000001,sh000905,sz399006,sz399001'
    chart_tmplate = '''<tr><td>
    <img src="http://image.sinajs.cn/newchart/daily/n/%s.gif"></img>
    <img src="http://image.sinajs.cn/newchart/min/n/%s.gif"></img>
    </td></tr>
    '''
    
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
                
    @classmethod
    def get_all(cls):
        ids = cls.index_ids.split(',')
        all_data = [cls.get_one(id) for id in ids]
        ret = '<style>td {font-size: 4vw;}</style><a href="/fund">BACK</a><table border="1"><tr><td>id</td><td>指数名称</td><td>指数</td><td>涨幅</td><td>成交量</td></tr>'
        for data in all_data:
            ret += '<tr><td>' + '</td><td>'.join(data) + '</td></tr>'
        ret += '</table>'
        
        ret += '<table border="1">' + ''.join([cls.chart_tmplate%(id, id) for id in ids]) + '</table>'
        
        return ret

@app.route("/realtime")
def realtime_value():
    return RealtimeValue.get_all()
    
#######################################

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
    
@app.route('/history', methods=['GET'])
def history_value():
    inputText = request.args.get("input_text", default='')
    if '' == inputText:
        resText = HistoryValue().get_all('190101,190401,190701,191001') # 默认查询季度值
    else:
        resText = HistoryValue().get_all(inputText)
    return render_template('query.html', query_url='/history', input_text=inputText, res_text=resText, 
        hint='<110022,110003;>190602,190823')
        
##########################################
@app.route('/url')
def myurl():
    us = [['腾讯', 'https://www.qq.com/', '#pim#', '[M.6]'],
        ['农行', 'http://www.abchina.com/cn/', '#money#', '[139/M.1]'],
        ['图虫', 'https://tuchong.com/', '#travel#', '[139]'],
        ['github', 'https://github.com/', '#tech#', '[t/wengu]'],
        ['百度网盘', 'https://pan.baidu.com/', '#life#', '[t/w][135/w][parentshare@126/parentshare]'],
        ['个人信用信息服务', 'https://ipcrs.pbccrc.org.cn/', '#life#', '[t/Wg]'],
        ['社保', 'http://rsj.sh.gov.cn/sbsjb/wzb/226.jsp', '#life#', '[2]'],
        ['交警', 'https://sh.122.gov.cn/', '#life#', '[z:139][x:w.n23]'],
        ['喜马拉雅听书', 'http://ximalaya.com', '#media#', '[sina]'],
        ['知乎', 'https://www.zhihu.com/signin?next=%2F', '#life#', '[139]'],
        ['UC浏览器', 'http://www.uc.cn/', '#pim#', '[sina]'],
        ['mp4ba', 'http://mp4ba.com', '#media#', ''],
        ['好网角', 'https://www.wang1314.com/', '#pim#', '[sina]'],
        ['小米', 'http://mi.com', '#buy#', '[139/2/139@126]'],
        ['360', 'https://www.360.cn/', '#tech#', '[t@126/t]'],
        ['天天美剧', 'http://www.ttmeiju.vip/', '#media#', '[t/t/t@126]'],
        ['市民信箱', 'http://www.eshimin.com/index.jsp', '#pim#', '[t/m]'],
        ['挂号网', 'https://www.guahao.com/', '#life#', '[t@126/t]'],
        ['淘宝', 'https://www.taobao.com/', '#buy#', '[t@hot/M.6/M.3]'],
        ['京东', 'https://www.jd.com/', '#buy#', '[t/M.6/M.3]'],
        ['LeetCode', 'https://leetcode-cn.com/', '#tech#', '[t/t/t@126]'],
        ['DDNS-PubYun-3322', 'http://pubyun.com/', '#tech#', '[t/t]'],
        ['上图-zz', 'http://www.library.sh.cn/', '#zz#', '[13958481/zzid]'],
        ['六师附小[无法访问]', 'http://www.lsfx.pudong-edu.sh.cn/infoweb/', '#zz#', '[zpc/5]'],
        ['LinkedIn', 'https://www.linkedin.com/feed/', '#job#', '[1@126/139]'],
        ['上海医保', 'http://ybj.sh.gov.cn/xxcx/search02_01.jsp', '#life#', '[2][5]'],
        ['住房公积金', 'https://persons.shgjj.com/gjjweb/#/app', '#life#', '[t/m][c.a/5]'],
        ['大众点评', 'http://www.dianping.com/', '#buy#', '[x@hot/5]'],
        ['猎聘网', 'https://www.liepin.com/', '#job#', '[t@126/t]'],
        ['BT之家', 'http://www.btbtt.com/', '#media#', ''],
        ['为知', 'http://www.wiz.cn/', '#pim#', '[t@126/t]'],
        ['wps', 'http://www.wps.cn/', '#pim#', '[t@125/w]'],
        ['126', 'https://mail.126.com/', '#pim#', '[t/m/139]'],
        ['hotmail', 'https://outlook.live.com/owa/', '#pim#', '[tf_z/M.6]'],
        ['12306', 'http://www.12306.cn/mormhweb/', '#travel#', '[t/w/t@126]'],
        ['去哪儿', 'https://www.qunar.com/', '#travel#', '[t/w/1@126]'],
        ['蚂蜂窝', 'http://www.mafengwo.cn/', '#travel#', '[t@126/t]'],
        ['春秋', 'https://www.ch.com/', '#travel#', '[135/5]'],
        ['同程', 'https://www.ly.com/', '#travel#', '[139/139]'],
        ['亚航', 'https://www.airasia.com/zh/cn?cid=1', '#travel#', '[t/m.1]'],
        ['微软软件', 'http://msdn.itellyou.cn/', '#tech#', ''],
        ['高德地图API', 'http://lbs.amap.com/console/show/picker', '#travel#', '[t/t]'],
        ['东航', 'http://www.ceair.com/', '#travel#', '[139/后8]'],
        ['自如网', 'http://sh.ziroom.com/', '#life#', '[139/后8]'],
        ['☆有道云', 'http://note.youdao.com/', '#pim#', '[t@126/m]'],
        ['☆印象笔记', 'https://www.yinxiang.com/', '#pim#', '[t/m]'],
        ['浦发', 'https://www.spdb.com.cn/', '#money#', '[1110385279/2]'],
        ['建行', 'http://www.ccb.com/cn/home/indexv3.html', '#money#', '[t/z2]'],
        ['中国银行', 'http://www.boc.cn/', '#money#', '[t/m.1]'],
        ['上海图书馆', 'http://www.libnet.sh.cn/zxtsg/', '#life#', '[13229348]'],
        ['携程', 'http://www.ctrip.com/', '#travel#', '[135/7861]'],
        ['mp3合并', 'https://audio-joiner.com/cn/', '#media#', ''],
        ['图标下载', 'https://www.easyicon.net/', '#tech#', ''],
        ['ProcessOn', 'https://www.processon.com/', '#tech#', '[t@126/Wg]'],
        ['jsform', 'https://www.bangboss.com/', '#pim#', '[t@126/Wg]'],
        ['☆石墨文档', 'https://shimo.im/desktop', '#pim#', '[t@126/Wg]'],
        ['电影天堂', 'http://www.dytt8.net/index.htm', '#media#', ''],
        ['打字练习', 'https://www.keybr.com/', '#zz#', ''],
        ['打字练习', 'http://www.dazima.cn/flash/', '#zz#', ''],
        ['☆新浪微博', 'https://weibo.cn/', '#pim#', '[t/Wg/139]'],
        ['MBTI职业性格', 'http://www.apesk.com/mbti/dati.asp', '#job#', ''],
        ['中国徒步网', 'http://www.chinawalking.net.cn/', '#travel#', ''],
        ['上海展会', 'http://shanghai.eshow365.com/', '#travel#', ''],
        ['华为商城', 'https://www.vmall.com/', '#buy#', '[139][内购：hw/M.1]'],
        ['Testing Map', 'http://thetestingmap.org/', '#tech#', ''],
        ['异次元软件', 'https://www.iplaysoft.com/', '#tech#', ''],
        ['小众软件', 'https://www.appinn.com/', '#tech#', ''],
        ['软件测试的两张藏宝图和三个层次', 'https://blog.csdn.net/kerryzhu/article/details/4134379', '#tech#', ''],
        ['2013流行Python项目', 'https://www.iteye.com/news/28717-2013-top-python-projects', '#tech#', ''],
        ['Android 手机自动化测试工具', 'https://www.zhihu.com/question/19716849', '#tech#', ''],
        ['Devops Tools', 'https://www.jianshu.com/p/3b5e1fc2a54b', '#tech#', ''],
        ['pinbox', 'https://withpinbox.com/items', '#pim#', '[t@126/t]'],
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

@app.route('/fund')
def index():
    return '<style>td {font-size: 4vw;}</style><table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/realtime':'指数实时', '/history':'基金历史'}\
        .items()]) + '</td></tr></table>'
        
@app.route('/')
def home():
    return '<style>td {font-size: 4vw;}</style><table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/fund':'基金', '/url':'网址', '/map':'地图', '/getnotify':'检查同步时间'}\
        .items()]) + '</td></tr></table>'

#########################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)