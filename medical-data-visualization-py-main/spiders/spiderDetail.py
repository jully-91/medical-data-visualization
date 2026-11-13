import re
import time
from pymysql import connect
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from utils.db_config import get_db_config

# 直接实现querys函数以避免模块导入问题（使用统一数据库配置）
cfg = get_db_config(charset='utf8')
conn = connect(**cfg)
cursor = conn.cursor()

def querys(sql, params, type='no_select'):
    try:
        cursor.execute(sql, params)
        if type == 'select':
            return cursor.fetchall()
        conn.commit()
        return True
    except Exception as e:
        print(e)
        conn.rollback()
        return False

# service = Service('./chromedriver.exe')
# browser =webdriver.Chrome(service=service)
# option = webdriver.ChromeOptions()
# browser.get('https://www.baidu.com/')
class spider(object):
    def __init__(self,spiderUrl):
        self.spiderUrl = spiderUrl

    def startBrowser(self):
        # 使用webdriver-manager自动管理ChromeDriver版本
        service = Service(ChromeDriverManager().install())
        option = webdriver.ChromeOptions()
        browser = webdriver.Chrome(service=service, options=option)
        return browser

    def main(self,id):
        browser = self.startBrowser()
        print('列表URL为'+self.spiderUrl)
        browser.get(self.spiderUrl)
        # 添加等待时间确保页面完全加载
        time.sleep(5)
        try:
            # 尝试查找元素，如果找到则继续爬取
            browser.find_element(by=By.XPATH,value='//span[contains(text(),"疾病描述")]/following-sibling::span[1]')
            #身高
            try:
                height = re.findall(r'\d+', browser.find_element(by=By.XPATH,value='//span[contains(text(),"身高体重")]/following-sibling::span[1]').text)[0]
            except:
                height = '无'
            #体重
            try:
                weight = re.findall(r'\d+',browser.find_element(by=By.XPATH,value='//span[contains(text(),"身高体重")]/following-sibling::span[1]').text)[1]
            except:
                weight = '无'
            #患病时间
            try:
                illDuration = browser.find_element(by=By.XPATH,value='//span[contains(text(),"患病时长")]/following-sibling::span[1]').text
            except:
                illDuration = '无'
            #过敏史
            try:
                allergy = re.search(r'([\u4e00-\u9fa5]+)\(',browser.find_element(by=By.XPATH,value='//span[contains(text(),"过敏史")]/following-sibling::span[1]').text).group(1)
            except:
                allergy = '暂无信息'
            print(height,weight,illDuration,allergy)
            querys('UPDATE cases SET height=%s,weight=%s,illDuration=%s,allergy=%s WHERE id = %s',
                   [height,weight,illDuration,allergy,id])
        except Exception as e:
            print(f"爬取失败，错误信息: {str(e)}")
            return '爬取失败'
        finally:
            # 无论成功失败都关闭浏览器
            browser.quit()


if __name__ == '__main__':
    caseList = querys('select * from cases',[],'select')
    for i in caseList[:]:
        spiderObj = spider(i[9])
        spiderObj.main(i[0])

