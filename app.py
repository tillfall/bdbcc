# -*- coding:utf-8 -*-
from flask import Flask, request, render_template
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
        ret = '<table border="1"><tr><th>id</th><th>指数名称</th><th>指数</th><th>涨幅</th><th>成交量</th></tr>'
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
    
    my_funds = '110022,110003,003318'.split(',')
    inputdatefmt = '%y%m%d'
    urldatefmt = '%Y-%m-%d'
    
    def parse_args(self, argstr):
    # <110023,600320;>190204,190504,190807
        secs = argstr.split(';')
        if len(secs) == 2:
            self.funds = self.my_funds + secs[0].split(',')
            self.dates = secs[1].split(',')
        elif len(secs) == 1:
            self.funds = self.my_funds
            self.dates = secs[0].split(',')
        else:
            raise Exception(argstr)
            
        self.dates.sort()
        self.startdate = datetime.strptime(self.dates[0], self.inputdatefmt)
        self.startdate = self.startdate - timedelta(days=10)  # 10天前，以免遇到节假日
        self.startdate = datetime.strftime(self.startdate, self.urldatefmt)
        self.enddate = datetime.strftime(datetime.now(), self.urldatefmt)  # 今天，并且加入查询列表
        self.dates.append(datetime.strftime(datetime.now(), self.inputdatefmt))

    def get_one(self, fundid):
        url = self.url_template%(fundid, self.startdate, self.enddate)
        logging.debug(url)
        req = Request(url=url, headers=self.headers) 
        return urlopen(req).read().decode('utf-8')
        
    # TODO
    def get_all(self, argstr):
        self.parse_args(argstr)
        return self.get_one('110022')
        
    
@app.route('/history', methods=['GET'])
def history_value():
    inputText = request.args.get("input_text", default='')
    if '' == inputText:
        resText = ''
    else:
        resText = HistoryValue().get_all(inputText)
    return render_template('query.html', query_url='/history', input_text=inputText, res_text=resText)

##########################################

@app.route('/')
def index():
    return '<table><tr><td>' + '</td></tr><tr><td>'.join(['<a href="%s">%s</a>'%(k,v) for k, v in \
        {'/realtime':'指数实时', '/history':'基金历史'}\
        .items()]) + '</td></tr></table>'

#########################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)