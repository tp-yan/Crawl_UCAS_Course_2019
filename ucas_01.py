# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os
import requests
import threading

'''
此版本添加了异常捕获，若30秒内，无法跳转到指定页面，则会报错，然后捕获异常，会不断重新发送跳转请求，直到成功
跳转。若在爬虫过程中，页面卡住了，可以手动点击一下浏览器的刷新按钮，可继续爬虫！
'''

# 初始化浏览器，并进入课程资源列表页面
def setUp(url,showBrowser=True):
    '''默认打开浏览器'''
    # myNo = ""  # 也可以在这儿直接输入，
    # myPwd = "" # 然后注释下面两行
    myNo = input("输入账号：")
    myPwd = input("输入密码：")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--diable-gpu")
    driver = None
    if showBrowser:
        driver = webdriver.Chrome()
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    driver.get(url)
    
    username = driver.find_element_by_id("menhuusername")
    pwd = driver.find_element_by_id("menhupassword")
    username.clear()
    pwd.clear()
    username.send_keys(myNo)
    pwd.send_keys(myPwd)
    # 执行登陆
    pwd.send_keys(Keys.RETURN) 
    # 隐式等待 30 秒，若还未载入下一页，则重复登录，在 x0秒内载入，则立即继续执行
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            pwd.send_keys(Keys.RETURN)
        else: # 没有报错，则跳出循环，继续后续操作
            break

    # 点击“课程网站”
    # print("current_url:\n",driver.current_url)
    kecheng = driver.find_element_by_xpath("//li[@class='app-black m-black-col1']/a[@title='课程网站']")
    print("课程网站:\n",kecheng.get_attribute('href'))
    kecheng.click()
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            kecheng.click()
        else:
            break
    

    # 点击“资源”，进入我的工作空间
    print("主页:\n",driver.current_url)
    ziyuan_link = driver.find_element_by_xpath("//li/a[contains(@title,'资源')]")
    print(ziyuan_link.get_attribute('href'))
    ziyuan_link.click()
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            ziyuan_link.click()
        else:
            break

    # 点击其他站点 
    qitazhandian = driver.find_element_by_xpath("//a[@title='从其它站点复制内容']")
    qitazhandian.click()
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            qitazhandian.click()
        else:
            break
    return driver


def get_course_content(dir_button,driver,dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    dir_button.click()
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            dir_button.click()
        else:
            break
    course_name = driver.find_element_by_xpath("//tbody/tr[2]/td[3]/a/span[2]").text.split()[0]
    # 使用 os.path.join 可以解决 Unix与Windows下路径斜杠与反斜杠不一致问题
    parent_dir = os.path.join(dir_path,course_name)
    
    item_list = driver.find_elements_by_xpath("//td[@class='specialLink title']/a[2]")
    while item_list:
        item = item_list.pop(0)
        if item.get_attribute('title') == '文件夹':
            subdir = item.find_element_by_xpath("./span[2]").text
            if subdir in handled_dir:
               continue
            get_course_content(item,driver,parent_dir)
            handled_dir.append(subdir)
            item_list = driver.find_elements_by_xpath("//td[@class='specialLink title']/a[2]")
        else:
            url = item.get_attribute('href')
            name = item.find_element_by_xpath('./span[2]').text
            # 使用多线程下载文件
            T = threading.Thread(target=download_file,args=(url,parent_dir,name))
            # 将主线程设置为 非守护线程，若主线程为守护线程，则主线程结束，子线程也随之立即结束
            T.setDaemon(False)
            T.start()
            download_threadings.append(T)
    
    # 返回上一级
    print(course_name,":",driver.current_url)
    goback = driver.find_element_by_xpath("//ol[@class='breadcrumb']/li[last()-2]")
    goback.click()
    while True:
        try:
            driver.implicitly_wait(30)
        except TimeoutError as err:
            print("跳转页面超时:",err)
            goback.click()
        else:
            break

def start_spider(driver,dir_path):
    '''课程资源文件列表：判断哪些文件夹下有资源，过滤掉空文件夹'''
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        # /..：代表父节点
    course_list = driver.find_elements_by_xpath("//tr/th[@headers='title']/span[2]/a[@title='打开此文件夹']/../../a")
    # 所有非空文件的名称，用于定位元素节点
    course_name_list = [item.text.strip() for item in course_list]
    
    while course_name_list:
        name = course_name_list.pop(0)
        print("================{}=================".format(name))
        # 因为下面递归调用了 driver ，导致其绑定的文档对象改变，故每次根据文件夹名称去定位元素，然后点击跳转到该课程资源页面下
        course = driver.find_element_by_xpath("//a[contains(text(),'{}')]".format(name))
        # 处理一个文件夹下面的资源
        get_course_content(course,driver,dir_path)


def download_file(url,dir_path,name):
    '''使用登录后的cookies+requests库下载资源'''
    print("-----------start download file :{}-------------------".format(name))
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    absolute_path = os.path.join(dir_path,name)
    
    agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36'
    headers = {
        'User-Agent':agent,
        'cookie':cookiestr
        }
    r = requests.get(url,headers=headers)
    try:
        r.raise_for_status()
    except Exception as err:
        print(name," : ",err)

    if os.path.exists(absolute_path):
        os.remove(absolute_path)
    with open(absolute_path,'wb') as f:
        f.write(r.content)
    print("-----------end download file :{}-------------------".format(name))


# 保存使用 selenium 用户登录后的 cookies，以便使用 requests库来下载文件
cookiestr = ""

if __name__ == "__main__":
    # 课程网站登录页
    url = "http://onestop.ucas.ac.cn/home/staff/"
    # 保存资源的根目录
    dir_name = "grc_courses"

    # 管理下载文件的线程
    download_threadings = []
    # 存放所有已处理的子目录，避免递归时，重复进入同一个子目录
    handled_dir = []
    try:
        # driver:浏览器对象
        driver = setUp(url)
    except Exception as err:
        print("无法获取页面内容，爬虫失败，请尝试用带界面的爬虫！",err)
        driver.quit()
        # python程序终止
        os._exit()
    #get the session cookie
    cookie = [item["name"] + "=" + item["value"] for item in driver.get_cookies()]
    #print cookie
    cookiestr = ';'.join(item for item in cookie)
    print("cookiestr:\n",cookiestr)

    # 获取此程序父目录的绝对路径
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    try:
        # 开始爬虫
        start_spider(driver,os.path.join(cur_dir,dir_name))
    except Exception as err:
        print(err)
    else:
        # 主线程等待所有下载线程结束
        for t in download_threadings:
            t.join()
    finally:
        if driver:
            # 关闭浏览器
            driver.quit()
            print("===================爬虫结束====================")
    
    