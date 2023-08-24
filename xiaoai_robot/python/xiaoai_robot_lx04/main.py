from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.uix.image import Image
from kivy.clock import Clock
from jnius import autoclass
from threading import Thread
from time import sleep
import os
import requests
import random
import pypinyin

Builder.load_string("""
<ExampleApp>:
    orientation: "vertical"
    BoxLayout:
        orientation: 'horizontal'
        Image:
            id: gif
            source: app.get_current_image()
            size_hint: (1, 1)
            allow_stretch: True
            anim_delay: 0.1
            anim_loop: 0
""")

class ExampleApp(App, BoxLayout):
    gif_list = ['eye.gif']  # 初始显示 "eye.gif"
    eye_index = 0
    gif_index = 0
    prev_time = None
    bluetooth_connected = False
    playing_gif = False
    prev_contx = False
    contx=" "
    numb=0

    def build(self):
        Clock.schedule_interval(self.check_log, 0.2)  # 每隔0.2秒检查log文件

        # 创建一个线程对象，用于在后台发送数据
        self.thread = Thread(target=self.send_data)
        self.thread.start()

        return self
    
    # 定义一个函数，接受一个字符串作为参数，返回该字符串的拼音
    def get_pinyin(self):
      # 使用pypinyin库的lazy_pinyin方法，将汉字转换为拼音列表
      pinyin_list = pypinyin.lazy_pinyin(self.contx)
      # 使用join方法，将拼音列表连接成一个字符串
      pinyin_str = "".join(pinyin_list)
      # 返回拼音字符串
      return pinyin_str
    
    def get_current_image(self):
        if self.playing_gif:
            return self.gif_list[self.gif_index]
        else:
            return self.gif_list[self.eye_index]

    def next_image(self):
        self.playing_gif = False
        self.root.ids.gif.source = self.get_current_image()

    def check_log(self, dt):
        file_path = "/storage/emulated/0/Android/data/com.xiaomi.micolauncher/files/log/mico.log"

        # 打开并读取该文件的内容
        with open(file_path, "r") as f:
            content = f.read()
            # 使用rfind方法在文件内容中反向查找“小爱同学”这个关键词
            index = content.rfind("小爱同学")
            if index != -1:
                # 获取该关键词前面的时间信息
                time = content[index - 410:index - 395]
                # 与之前记录的时间进行比较
                if time != self.prev_time:
                    # 如果不一致，就说明发生了新的事件
                    print("new event")
                    self.prev_time = time
                    self.bluetooth_connected = True
                    #Clock.schedule_once(self.play_gif, 0.2)  # 等待0.5秒后播放gif
            index2 = content.rfind("MSG_ASR_FINAL_RESULT:")
            if index2 != -1:
                # 获取该关键词前面的内容信息
                end_index2 = content.find("\n", index2)
                self.contx = content[index2 +21:end_index2]
                # 与之前记录的内容进行比较
                if self.contx != self.prev_contx:
                    # 如果不一致，就说明发生了新的事件
                    print(self.contx)
                    self.prev_contx = self.contx
                    Clock.schedule_once(self.play_gif, 0)  # 等待0秒后播放gif

    def send_data(self):
        # 获取Android蓝牙适配器对象
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        # 获取已配对的蓝牙设备列表
        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        # 创建一个UUID对象，用于创建蓝牙套接字
        UUID = autoclass('java.util.UUID')
        # 给socket变量赋一个初始值None
        self.socket = None
        # 遍历已配对的蓝牙设备，找到名为ESP32的设备
        for device in paired_devices:
            if device.getName() == 'ESP32':
                # 创建一个RFCOMM蓝牙套接字，用于和ESP32通信
                self.socket = device.createRfcommSocketToServiceRecord(
                    UUID.fromString("00001101-0000-1000-8000-00805F9B34FB"))
                break

        if self.socket is not None:
            self.output_stream = self.socket.getOutputStream()

            # 连接蓝牙套接字
            self.socket.connect()
            while True:
                if self.bluetooth_connected:
                    # 在此处添加发送数据的逻辑
                    # 例如，定时发送其他数据给ESP32
                    gif_name = '1\n'
                    self.output_stream.write(gif_name.encode('utf-8'))
                    self.output_stream.flush()
                    self.bluetooth_connected = False
                if self.bluetooth_connected==False and random.randint(1, 699999)==3:
                    # 在此处添加发送数据的逻辑
                    # 例如，定时发送其他数据给ESP32
                    gif_name = '2\n'
                    self.output_stream.write(gif_name.encode('utf-8'))
                    self.output_stream.flush()

    def play_gif(self, dt):
        # 下载并显示 GIF 图片
        keyword = self.get_pinyin()  # 您可以根据需要替换为其他关键词
        print(keyword)
        self.download_and_show_gif(keyword)
        Clock.schedule_once(self.stop_gif, 9)  # 播放9秒后停止gif

    def stop_gif(self, dt):
        self.next_image()
        self.delete_downloaded_gif()

    def download_and_show_gif(self, pinyin):
        response = requests.get("https://www.soogif.com/gif/" + pinyin + ".html")
        if response.status_code == 200:
            try:
                gif_url = response.text.split('data-original="')[random.randint(1, 32)].split('"')[0]
                gif_data = requests.get(gif_url).content
                gif_filename = pinyin +str(self.numb)+ ".gif"
                with open(gif_filename, "wb") as f:
                    f.write(gif_data)
                    print(gif_filename)
                self.gif_list.append(gif_filename)
                self.playing_gif = True
                self.numb=self.numb+1
                if self.numb>7000:
                    self.numb=0
                self.gif_index = len(self.gif_list) - 1
                self.root.ids.gif.source = self.get_current_image()
            except IndexError:
                print("没有找到符合关键词的动图")
        else:
            print("请求失败，状态码为" + str(response.status_code))

    def delete_downloaded_gif(self):
        if len(self.gif_list) > 1:
            gif_to_delete = self.gif_list.pop(1)
            try:
                os.remove(gif_to_delete)
                print("删除成功")
            except Exception as e:
                print("删除失败:", str(e))


if __name__ == "__main__":
    ExampleApp().run()
