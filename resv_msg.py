import asyncio
import websockets
import json
import datetime
import time
from wxauto import *
import logging
import configparser
import re

config = configparser.ConfigParser()
try:
    config.read("config.ini", encoding='utf-8')
except:
    config.read("config.ini", encoding='utf-8-sig')


async def time_transform(time_str: str):
    week_dict = {'星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3, '星期五':4, '星期六':5, '星期天':6}
    if '星期' in time_str:
        week_cn = time_str[:3]
        weekday = datetime.datetime.today().weekday()
        if weekday-week_dict[week_cn] < 0:
            time_str = time_str.replace(week_cn, (datetime.datetime.today() - datetime.timedelta(days=weekday+1)).strftime("%Y-%m-%d"))
        elif weekday-week_dict[week_cn] == 0 or weekday-week_dict[week_cn] == 1:
            logging.warning('微信系统时间不规范')
            print('Error')
        else:
            time_str = time_str.replace(week_cn, (datetime.datetime.today() - datetime.timedelta(days=weekday-week_dict[week_cn])).strftime("%Y-%m-%d"))
    elif '年' in time_str:
        data_list = time_str.replace('年', '-').replace('月', '-').replace('日', '-').split('-')
        for i, data in enumerate(data_list):
            if len(data) == 1:
                data_list[i] = '0' + data
        time_str = data_list[0] + '-' + data_list[1] + '-' + data_list[2] + data_list[3]
    elif '昨天' in time_str:
        time_str = time_str.replace('昨天', (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    else:
        time_str = ('0' if len(time_str.split(':')[0]) == 1 else '') + time_str
        time_str = f'{datetime.datetime.today().strftime("%Y-%m-%d")} {time_str}'
    return time_str

async def message_transform(msg_tuple):
    msg_dict = {}
    msg_dict['sender'] = msg_tuple[0]
    if msg_tuple[0] == 'SYS':
        if re.sub('月|年|日|星期|一|二|三|四|五|六|:|-|', ' ', msg_tuple[1]).replace(" ", "").isdigit():
            msg_dict['type'] = 'TIME'
            msg_dict['value'] = await time_transform(msg_tuple[1])
        else:
            msg_dict['type'] = 'OTHER'
            msg_dict['value'] = msg_tuple[1]
    elif msg_tuple[0] == '查看更多消息':
        msg_dict['sender'] = 'SYS'
        msg_dict['type'] = 'OTHER'
        msg_dict['value'] = '查看更多消息'
    elif msg_dict['sender'].lower() == 'time':
        msg_dict['type'] = 'TIME'
        msg_dict['value'] = await time_transform(msg_tuple[1])
    elif '\n引用' in msg_tuple[1]:
        msg_dict['type'] = 'RESPONSE'
        msg_dict['value'] = msg_tuple[1].split('\n引用')[0]
        msg_dict['response_to'] = msg_tuple[1].split('\n引用')[1].split(' 的消息 : ')
    elif '[图片]' in msg_tuple[1]:
        msg_dict['type'] = 'PIC'
    elif '[视频]' in msg_tuple[1]:
        msg_dict['type'] = 'VIDEO'
    elif '[文件]' in msg_tuple[1]:
        msg_dict['type'] = 'DOC'
    elif '[语音]' in msg_tuple[1]:
        msg_dict['type'] = 'VOICE'
    elif '[动画表情]' in msg_tuple[1]:
        msg_dict['type'] = 'ANIMATION'
    else:
        msg_dict['type'] = 'MSG'
        msg_dict['value'] = msg_tuple[1]
        if msg_tuple[2]:
            msg_dict['nick_name'] = msg_tuple[0]
            msg_dict['sender'] = msg_tuple[2]
    return msg_dict

async def GetAllMessage(last_time, wx):
    '''获取当前窗口中加载的所有聊天记录'''
    need_scroll = True
    # проверка на загрузку нужного количества сообщений
    msg_num = 0
    while need_scroll:
        MsgDocker = []
        MsgItems = wx.MsgList.GetChildren()
        if msg_num < len(MsgItems):
            for MsgItem in MsgItems:
                cur_msg = await message_transform(WxUtils.SplitMessage(MsgItem))
                if cur_msg['type'] == 'TIME':
                    if last_time > cur_msg['value']:
                        need_scroll = False
                        break
            if need_scroll:
                msg_num = len(MsgItems)
                wx.LoadMoreMessage()
        else:
            break
    
    for MsgItem in reversed(MsgItems):
        cur_msg = await message_transform(WxUtils.SplitMessage(MsgItem))
        MsgDocker.append(cur_msg)
        if cur_msg['type'] == 'TIME' and last_time >= cur_msg['value']:
            break
    return MsgDocker


async def get_massages():
    url = f"{config['SERVER']['link']}{config['SERVER']['client_num_for_resv_msg']}"
    first_group = config['WECHAT']['group_name'].split(',')[0].strip()
    last_group = config['WECHAT']['group_name'].split(',')[-1].strip()
    delta = datetime.timedelta(seconds=int(config['WECHAT']['delta_time']))
    whos = [i.strip() for i in config['WECHAT']['group_name'].split(',')]
    if config['WECHAT']['last_time'] == "":
        config['WECHAT']['last_time'] = datetime.datetime.today().strftime("%Y-%m-%d %H:%M")
    current_index = 0
    
    while True:
        try:
            wx = WeChat()
            wx.GetSessionList()
            start = datetime.datetime.now()
            async with websockets.connect(url, ping_interval=None) as websocket:
                while True:
                    for who in whos[current_index:]:
                        current_index = whos.index(who)
                        if who == first_group:
                            loop_stime = datetime.datetime.today().strftime("%Y-%m-%d %H:%M")
                        wx.ChatWith(who)
                        msg = await GetAllMessage(config['WECHAT']['last_time'], wx)
            
                        data = {"group_name": who,"msg_list": msg}
                        print(data)
                        file = json.dumps(data)
                        await websocket.send(file)
                        try:
                            response = await websocket.recv()
                        except Exception as e:
                            logging.warning('链接失败')
                            print('Connection failed. Did not resive msg from server.')
                            time.sleep(10)
                            break
                        logging.info(f'>>> {data}')
                        logging.info(f'<<< {response}')
                        logging.info((f'New config: {config.__dict__["_sections"]}'))
                        print(f'>>> {data}')
                        print(f'Config: {config.__dict__["_sections"]}')
                        if who == last_group:
                            config['WECHAT']['last_time'] = loop_stime
                            with open("config.ini", 'w', encoding='utf-8') as configfile:
                                config.write(configfile)
                    if datetime.datetime.now() - start < delta:
                        time.sleep((delta - (datetime.datetime.now() - start)).total_seconds())
                    current_index = 0
        except Exception as e:
            logging.warning('链接失败')
            logging.warning(str(e))
            print('Connection failed. Can not connect server.')
            time.sleep(10)
            continue

if __name__ == "__main__":

    if config['SERVER']['log_level'].lower() == 'info':
        level=logging.INFO
    else:
        level=logging.DEBUG

    logging.basicConfig(filename='LogFile',
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=level)

    asyncio.run(get_massages())