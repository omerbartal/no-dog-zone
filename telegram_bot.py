#!/usr/bin/env python3
import telegram
import time
import subprocess
import json
import threading
import traceback

from log import logger

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode

import params


class TelegramBot:
    def __init__(self, user, chat_id):
        self.lock = threading.Lock()
        self.user = user
        self.chat_id = chat_id
        self.last_update_id = None
        self.menu = None
        self.token = params.params.get('telegram_token', None)
        self.warned = False

        if self.token is None:
            logger.warning('missing telegram_token parameter, telegram bot disabled')
            self.enabled = False
            self.warned = True
            return
        
        self.bot = telegram.Bot(token=self.token)
        self.enabled = True
        
            
    def send_menu(self, options=None, text='options:'):

        if not self.enabled:
            return

        if self.chat_id is None:
            if not self.warned:
                logger.warning('missing chat id (telegram_admin / telegram_chat_id)) parameter, telegram bot disabled')
            self.warned = True
            return
        
        if options is None:
            options = self.menu

        if options is None:
            return
        
        markup = []
        for o in options:
            markup.append([InlineKeyboardButton(o, callback_data=o)])

        with self.lock:
            self.bot.send_message(
                text=text,
                chat_id=self.chat_id,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(markup)
            )
        
        
    def send_message(self, message):
        if not self.enabled:
            return

        if self.chat_id is None:
            if not self.warned:
                logger.warning('missing chat id (telegram_admin / telegram_chat_id)) parameter, telegram bot disabled')
            self.warned = True
            return
        
        if self.user is None:
            user_name = 'admin'
        else:
            user_name = self.user

        message = user_name + ':' + message
            
        for retry in range(3):
            try:
                with self.lock:
                    self.bot.send_message(chat_id=self.chat_id,
                                          text=message)
                break
            except KeyboardInterrupt:
                raise
            except:
                if retry == 2:
                    raise
                time.sleep(1)

    def iter_updates(self):
        if not self.enabled:
            return
        
        with self.lock:
            updates = self.bot.get_updates()

        for u in updates:
            u = u.to_dict()
            if u['update_id'] is not None:
                
                if self.last_update_id is not None:
                    if u['update_id'] <= self.last_update_id:
                        continue
                
                self.last_update_id = u['update_id']
                
            yield u
                
    def read_chat_ids(self):
        ret = []
        for u in self.iter_updates():
            try:
                ret.append(u.message.chat_id)
            except Exception:
                pass
        return ret

    def upload_video(self, filename, timeout=None):
        if not self.enabled:
            return
        
        return self.upload_file(filename=filename, timeout=timeout, tag='video', api='sendVideo')
    
    def upload_file(self, filename, timeout=None, tag='document', api='sendDocument'):
        if self.chat_id is None:
            if not self.warned:
                logger.warning('missing chat id (telegram_admin / telegram_chat_id)) parameter, telegram bot disabled')
            self.warned = True
            return
        
        if not self.enabled:
            return
        

        p = subprocess.Popen(['curl',
                              '-F', f'name={tag}',
                              '-F', f'{tag}=@"{filename}"',
                              # '-H', "Content-Type:multipart/form-data",
                              f'https://api.telegram.org/bot{self.token}/{api}?chat_id={self.chat_id}'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        try:
            stdout, stderr = p.communicate(timeout=timeout)
        except TimeoutExpired:
            return False
        finally:
            if p.poll() is None:
                p.kill()
        
        #print((stdout, stderr, p.poll()))
        if p.poll() == 0:
            ret = json.loads(stdout)
            return ret.get('ok', False)

        else:
            return False

    def init_updates(self):
        if not self.enabled:
            return
        
        for u in self.iter_updates():
            pass

    def iter_button_cbs(self):
        if not self.enabled:
            return
        

        # {
        #     'callback_query': {
        #         'data': 'opt2', 'message': {
        #             'group_chat_created': False, 'chat': {
        #                 'title': 'detect dog', 'id': -4001157865, 'type': 'group', 'all_members_are_administrators': True},
        #             'caption_entities': [],
        #             'channel_chat_created': False,
        #             'supergroup_chat_created': False,
        #             'photo': [],
        #             'delete_chat_photo': False,
        #             'new_chat_photo': [],
        #             'reply_markup': {
        #                 'inline_keyboard': [
        #                     [
        #                         {'text': 'opt1',
        #                          'callback_data': 'opt1'}
        #                     ],
        #                     [
        #                         {'text': 'opt2',
        #                          'callback_data': 'opt2'}
        #                     ],
        #                     [
        #                         {'text': 'opt3',
        #                          'callback_data': 'opt3'}
        #                     ]
        #                 ]
        #             },
        #             'new_chat_members': [],
        #             'message_id': 28,
        #             'date': 1694899227,
        #             'text': 'options:',
        #             'entities': [],
        #             'from': {
        #                 'first_name': 'detect_dog',
        #                 'is_bot': True,
        #                 'id': 6537007071,
        #                 'username': 'detect_dog_bot'
        #             }
        #         },
        #         'id': '435731657692483407',
        #         'chat_instance': '-1130289195196729875',
        #         'from': {
        #             'first_name': 'Omer',
        #             'language_code': 'en',
        #             'last_name': 'Bartal',
        #             'is_bot': False,
        #             'id': 101451682}
        #     },
        #     'update_id': 212471405}

        
        for u in self.iter_updates():
            if 'callback_query' in u:
                yield u['callback_query']['data']
    
        
_chat = None
def get_chat():
    global _chat

    if _chat is None:
        _chat = TelegramBot('bot', params.params.get('telegram_chat_id', None))

    return _chat


_admin = None
def get_admin():
    global _admin

    if _admin is None:
        _admin = TelegramBot('bot', params.params.get('telegram_admin', None))

    return _admin

class BotThread(threading.Thread):
    def __init__(self):
        super(BotThread, self).__init__()
        self.daemon = True
        self.start()

    def button_pressed(self, data):
        logger.debug(data)
        
    def run(self):
        while True:
            try:
                get_chat().init_updates()
                break
            except Exception:
                logger.exception('telegram bot unexpected exception')
                traceback.print_exc()

            time.sleep(5)
                
        while True:
            try:
                for cb in get_chat().iter_button_cbs():
                    self.button_pressed(cb)
            except telegram.error.NetworkError:
                pass
            except Exception:
                logger.exception('telegram bot unexpected exception')
                traceback.print_exc()
            time.sleep(1)
                
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest='read_chat_ids', action='store_true', default=False, help="read chat ids")
    parser.add_argument('-u', dest='updates', action='store_true', default=False, help="updates")
    parser.add_argument('-t', dest='test_message', action='store', default=None, help="send a test message to chat id")
    parser.add_argument('-f', dest='upload_file', action='store', default=None, help="")
    parser.add_argument("--params", action="store", default='params.json')
    args = parser.parse_args()

    if args.params is None:
        parser.error('params missing')
        
    params.load_params(args.params)
    
    if args.updates:
        bot = TelegramBot(None, None)
        for u in bot.iter_updates():
            print(u)
    
    if args.read_chat_ids:
        bot = TelegramBot(None, None)
        for i in bot.read_chat_ids():
            print(i)

    if args.test_message:
        bot = TelegramBot(None, args.test_message)
        # bot.send_message('test message')
        bot.send_menu(['opt1', 'opt2', 'opt3'])
        BotThread()
        while True:
            time.sleep(1)

    if args.upload_file is not None:
        bot = get_chat()
        bot.upload_file(args.upload_file)
        
    
