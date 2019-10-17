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
    chart_tmplate = \
    '''
    <tr><td>
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
    return '''<style>td {font-size: 4vw;}</style><table><tr><td><a href="https://www.qq.com/">腾讯</a></td><td>#pim#</td><td>(M.6)</td></tr><tr><td><a href="http://www.abchina.com/cn/">农行</a></td><td>#money#</td><td>(139/M.1)</td></tr><tr><td><a href="https://tuchong.com/">图虫</a></td><td>#travel#</td><td>(139)</td></tr><tr><td><a href="https://github.com/">github</a></td><td>#tech#</td><td>(t/wengu)</td></tr><tr><td><a href="https://pan.baidu.com/">百度网盘</a></td><td>#life#</td><td>(t/w)(135/w)(parentshare@126/parentshare)</td></tr><tr><td><a href="https://ipcrs.pbccrc.org.cn/">个人信用信息服务</a></td><td>#life#</td><td>(t/Wg)</td></tr><tr><td><a href="http://rsj.sh.gov.cn/sbsjb/wzb/226.jsp">社保</a></td><td>#life#</td><td>(2)</td></tr><tr><td><a href="https://sh.122.gov.cn/">交警</a></td><td>#life#</td><td>(z:139)(x:w.n23)</td></tr><tr><td><a href="http://ximalaya.com">喜马拉雅听书</a></td><td>#media#</td><td>(sina)</td></tr><tr><td><a href="https://www.zhihu.com/signin?next=%2F">知乎</a></td><td>#life#</td><td>(139)</td></tr><tr><td><a href="http://www.uc.cn/">UC浏览器</a></td><td>#pim#</td><td>(sina)</td></tr><tr><td><a href="http://mp4ba.com">mp4ba</a></td><td>#media#</td><td></td></tr><tr><td><a href="https://www.wang1314.com/">好网角</a></td><td>#pim#</td><td>(sina)</td></tr><tr><td><a href="http://mi.com">小米</a></td><td>#buy#</td><td>(139/2/139@126)</td></tr><tr><td><a href="https://www.360.cn/">360</a></td><td>#tech#</td><td>(t@126/t)</td></tr><tr><td><a href="http://www.ttmeiju.vip/">天天美剧</a></td><td>#media#</td><td>(t/t/t@126)</td></tr><tr><td><a href="http://www.eshimin.com/index.jsp">市民信箱</a></td><td>#pim#</td><td>(t/m)</td></tr><tr><td><a href="https://www.guahao.com/">挂号网</a></td><td>#life#</td><td>(t@126/t)</td></tr><tr><td><a href="https://www.taobao.com/">淘宝</a></td><td>#buy#</td><td>(t@hot/M.6/M.3)</td></tr><tr><td><a href="https://www.jd.com/">京东</a></td><td>#buy#</td><td>(t/M.6/M.3)</td></tr><tr><td><a href="https://leetcode-cn.com/">LeetCode</a></td><td>#tech#</td><td>(t/t/t@126)</td></tr><tr><td><a href="http://pubyun.com/">DDNS-PubYun-3322</a></td><td>#tech#</td><td>(t/t)</td></tr><tr><td><a href="http://www.library.sh.cn/">上图-zz</a></td><td>#zz#</td><td>(13958481/zzid)</td></tr><tr><td><a href="http://www.lsfx.pudong-edu.sh.cn/infoweb/">六师附小(无法访问)</a></td><td>#zz#</td><td>(zpc/5)</td></tr><tr><td><a href="https://www.linkedin.com/feed/">LinkedIn</a></td><td>#job#</td><td>(1@126/139)</td></tr><tr><td><a href="http://ybj.sh.gov.cn/xxcx/search02_01.jsp">上海医保</a></td><td>#life#</td><td>(2)(5)</td></tr><tr><td><a href="https://persons.shgjj.com/gjjweb/#/app">住房公积金</a></td><td>#life#</td><td>(t/m)(c.a/5)</td></tr><tr><td><a href="http://www.dianping.com/">大众点评</a></td><td>#buy#</td><td>(x@hot/5)</td></tr><tr><td><a href="https://www.liepin.com/">猎聘网</a></td><td>#job#</td><td>(t@126/t)</td></tr><tr><td><a href="http://www.btbtt.com/">BT之家</a></td><td>#media#</td><td></td></tr><tr><td><a href="http://www.wiz.cn/">为知</a></td><td>#pim#</td><td>(t@126/t)</td></tr><tr><td><a href="http://www.wps.cn/">wps</a></td><td>#pim#</td><td>(t@125/w)</td></tr><tr><td><a href="https://mail.126.com/">126</a></td><td>#pim#</td><td>(t/m/139)</td></tr><tr><td><a href="https://outlook.live.com/owa/">hotmail</a></td><td>#pim#</td><td>(tf_z/M.6)</td></tr><tr><td><a href="http://www.12306.cn/mormhweb/">12306</a></td><td>#travel#</td><td>(t/w/t@126)</td></tr><tr><td><a href="https://www.qunar.com/">去哪儿</a></td><td>#travel#</td><td>(t/w/1@126)</td></tr><tr><td><a href="http://www.mafengwo.cn/">蚂蜂窝</a></td><td>#travel#</td><td>(t@126/t)</td></tr><tr><td><a href="https://www.ch.com/">春秋</a></td><td>#travel#</td><td>(135/5)</td></tr><tr><td><a href="https://www.ly.com/">同程</a></td><td>#travel#</td><td>(139/139)</td></tr><tr><td><a href="https://www.airasia.com/zh/cn?cid=1">亚航</a></td><td>#travel#</td><td>(t/m.1)</td></tr><tr><td><a href="http://msdn.itellyou.cn/">微软软件</a></td><td>#tech#</td><td></td></tr><tr><td><a href="http://lbs.amap.com/console/show/picker">高德地图API</a></td><td>#travel#</td><td>(t/t)</td></tr><tr><td><a href="http://www.ceair.com/">东航</a></td><td>#travel#</td><td>(139/后8)</td></tr><tr><td><a href="http://sh.ziroom.com/">自如网</a></td><td>#life#</td><td>(139/后8)</td></tr><tr><td><a href="http://note.youdao.com/">☆有道云</a></td><td>#pim#</td><td>(t@126/m)</td></tr><tr><td><a href="https://www.yinxiang.com/">☆印象笔记</a></td><td>#pim#</td><td>(t/m)</td></tr><tr><td><a href="https://www.spdb.com.cn/">浦发</a></td><td>#money#</td><td>(1110385279/2)</td></tr><tr><td><a href="http://www.ccb.com/cn/home/indexv3.html">建行</a></td><td>#money#</td><td>(t/z2)</td></tr><tr><td><a href="http://www.boc.cn/">中国银行</a></td><td>#money#</td><td>(t/m.1)</td></tr><tr><td><a href="http://www.libnet.sh.cn/zxtsg/">上海图书馆</a></td><td>#life#</td><td>(13229348)</td></tr><tr><td><a href="http://www.ctrip.com/">携程</a></td><td>#travel#</td><td>(135/7861)</td></tr><tr><td><a href="https://audio-joiner.com/cn/">mp3合并</a></td><td>#media#</td><td></td></tr><tr><td><a href="https://www.easyicon.net/">图标下载</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.processon.com/">ProcessOn</a></td><td>#tech#</td><td>(t@126/Wg)</td></tr><tr><td><a href="https://www.bangboss.com/">jsform</a></td><td>#pim#</td><td>(t@126/Wg)</td></tr><tr><td><a href="https://shimo.im/desktop">☆石墨文档</a></td><td>#pim#</td><td>(t@126/Wg)</td></tr><tr><td><a href="http://www.dytt8.net/index.htm">电影天堂</a></td><td>#media#</td><td></td></tr><tr><td><a href="https://www.keybr.com/">打字练习</a></td><td>#zz#</td><td></td></tr><tr><td><a href="http://www.dazima.cn/flash/">打字练习</a></td><td>#zz#</td><td></td></tr><tr><td><a href="https://weibo.cn/">☆新浪微博</a></td><td>#pim#</td><td>(t/Wg/139)</td></tr><tr><td><a href="http://www.apesk.com/mbti/dati.asp">MBTI职业性格</a></td><td>#job#</td><td></td></tr><tr><td><a href="http://www.chinawalking.net.cn/">中国徒步网</a></td><td>#travel#</td><td></td></tr><tr><td><a href="http://shanghai.eshow365.com/">上海展会</a></td><td>#travel#</td><td></td></tr><tr><td><a href="https://www.vmall.com/">华为商城</a></td><td>#buy#</td><td>(139)(内购：hw/M.1)</td></tr><tr><td><a href="http://thetestingmap.org/">Testing Map</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.iplaysoft.com/">异次元软件</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.appinn.com/">小众软件</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://blog.csdn.net/kerryzhu/article/details/4134379">软件测试的两张藏宝图和三个层次</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.iteye.com/news/28717-2013-top-python-projects">2013流行Python项目</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.zhihu.com/question/19716849">Android 手机自动化测试工具</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://www.jianshu.com/p/3b5e1fc2a54b">Devops Tools</a></td><td>#tech#</td><td></td></tr><tr><td><a href="https://withpinbox.com/items">pinbox</a></td><td>#pim#</td><td>(t@126/t)</td></tr></table>'''

##########################################

@app.route('/fund')
def index():
    return '<style>td {font-size: 4vw;}</style><table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/realtime':'指数实时', '/history':'基金历史'}\
        .items()]) + '</td></tr></table>'

#########################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)