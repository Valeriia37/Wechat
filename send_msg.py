import asyncio
import websockets
import json
import datetime
import time
from wxauto import *
import logging
import configparser


config = configparser.ConfigParser()
try:
    config.read("config.ini", encoding='utf-8')
except:
    config.read("config.ini", encoding='utf-8-sig')

print(f'Config: {config.__dict__["_sections"]}')


async def send_msg():
    url = f"{config['SERVER']['link']}{config['SERVER']['client_num_for_send_msg']}"
    while True:
        try:
            wx = WeChat()
            wx.GetSessionList()
            print('Connected wechat.')
            async with websockets.connect(url, ping_interval=None) as websocket:
                print('Connected server.')
                while True:
                    # print(f'Group name - {who}')
                    try:
                        print('Waiting for recive msg from server...')
                        data = await websocket.recv()
                    except Exception as e:
                        logging.error(f'Recive msg: {e}')
                        break
                    try:
                        data = json.loads(data)
                        print(f'Get data: {data}')
                    except Exception as e:
                        greeting = {'type': 2, 'status_code': 500, 'msg': str(e)}
                        greeting = json.dumps(greeting)
                        await websocket.send(greeting)
                        logging.info(f'>>> {greeting}')
                        continue
                    if 'userName' in data.keys() and 'msg' in data.keys() and 'groupName' in data.keys():
                        print('Sending msg...')
                        wx.UiaAPI.SwitchToThisWindow()
                        wx.ChatWith(data['groupName'])
                        wx.EditMsg.SendKeys('{Ctrl}a', waitTime=0)
                        wx.EditMsg.SendKeys(f"@{data['userName']}", waitTime=0)
                        try:
                            _ = wx.UiaAPI.PaneControl(Name='ChatContactMenu')
                            wx.EditMsg.SendKeys('{Enter}', waitTime=0)
                        except Exception as e:
                            print(f'Warning: no {data["userName"]} name in the list')
                        wx.EditMsg.SendKeys(f"  {data['msg']}", waitTime=0)
                        wx.EditMsg.SendKeys('{Enter}', waitTime=0)
                        print('Msg was sended.')
                        # wx.SendMsg(f"@{data['userName']}  {data['msg']}")
                        logging.info(f"Get massage: groupName = {data['groupName']} @{data['userName']}  {data['msg']}")
                        greeting = {'groupName': data['groupName'], 'type': 2, 'status_code': 200, 'msg': '发送成功'}
                        logging.info(f'>>> {greeting}')
                    else: 
                        greeting = {'groupName': data['groupName'], 'type': 2, 'status_code': 500, 'msg': 'No groupName, userName or msg info'}
                        logging.error(f'>>> {greeting}')
                    greeting = json.dumps(greeting)
                    await websocket.send(greeting)
                    print(f">>> {greeting}")
        except Exception as e:
            logging.error(f'Recive msg: {e}')
            
                

if __name__ == "__main__":
    asyncio.run(send_msg())