# -*- coding:utf-8 -*-
from flask import Flask
from urllib.request import urlopen

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
    index_ids = 'sh000001,sz399005,sz399906,sz399901'
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

@app.route("/")
def realtime_value():
    return RealtimeValue.get_all()

#########################################

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6789)