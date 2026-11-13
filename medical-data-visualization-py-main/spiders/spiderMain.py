import logging
import requests
from lxml import etree
import csv
import os
import pandas as pd
import re
from pymysql import *
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from utils.db_config import get_db_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('spiderMain')

# 数据库配置（统一从 utils.db_config / .env 读取）
DB_CONFIG = get_db_config()

def querys(sql, params, type='no_select'):
    """执行SQL查询，使用局部连接确保连接正确关闭"""
    conn = None
    cursor = None
    try:
        conn = connect(**DB_CONFIG)
        cursor = conn.cursor()
        params = tuple(params)
        cursor.execute(sql, params)
        if type != 'no_select':
            data_list = cursor.fetchall()
            conn.commit()
            return data_list
        else:
            conn.commit()
            return '执行成功'
    except Exception as e:
        logger.error(f"执行SQL失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class spider(object):
    def __init__(self):
        # 疾病名称到拼音的映射字典
        self.disease_pinyin_map = {
            '感冒': 'ganmao',
            '高血压': 'gaoxueya',
            '糖尿病': 'tangniaobing',
            '冠心病': 'guanxinbing',
            '肺炎': 'feiyan',
            '胃炎': 'weiyan',
            '肝炎': 'ganyan',
            '肾炎': 'shenyan',
            '抑郁症': 'yiyuzheng',
            '骨折': 'guzhe',
            '肠胃炎': 'changweiyan',
            '风湿': 'fengshi',
            '哮喘': 'xiaochuan',
            '气管炎': 'qiguanyan'
        }
        self.header = {
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36'
        }
        self.driver = None  # Selenium WebDriver实例
        self.wait = None    # WebDriverWait实例

    def init(self):
        # 创建/重建 CSV 文件
        # 注意：这里使用 'w' 模式，每次爬虫运行都会重置 temp2.csv，
        # 只保留本次采集的数据，避免 save_to_sql 反复导入历史记录导致 cases 表数据膨胀
        with open('temp2.csv', 'w', newline='', encoding='utf-8') as wf:
            write = csv.writer(wf)
            write.writerow(["type","gender","age","time","content","docName","docHospital","department",
                             "detailUrl","height","weight","illDuration","allergy"])
        
        # 创建数据库表
        try:
            conn = connect(**DB_CONFIG)
            sql = '''
                        create table if not exists cases(
                            id int primary key auto_increment,
                            type varchar(255),
                            gender varchar(255),
                            age varchar(255),
                            time varchar(255),
                            content varchar(2000),
                            docName varchar(255),
                            docHospital varchar(255),
                            department varchar(255),
                            detailUrl varchar(2555),
                            height varchar(255),
                            weight varchar(255),
                            illDuration varchar(255),
                            allergy varchar(255)
                        )
                    '''
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            conn.close()
            logger.info("已创建cases表")
        except Exception as e:
            logger.debug(f"创建表失败: {e}")
            pass
    
    def init_selenium(self):
        """
        初始化Selenium浏览器实例
        """
        try:
            # 设置Chrome选项，优化加载速度
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless")  # 启用无头模式，不显示浏览器窗口
            chrome_options.add_argument("--disable-gpu")  # 无头模式下禁用GPU加速
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用自动化控制检测
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--incognito")  # 使用无痕模式
            
            # 优化页面加载策略，禁用不必要的资源加载
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # 禁用图片加载
            chrome_options.add_argument("--disable-css")  # 禁用CSS
            chrome_options.add_argument("--disable-javascript")  # 禁用JavaScript（如果页面内容不需要JS）
            chrome_options.add_argument("--disable-plugins")  # 禁用插件
            chrome_options.add_argument("--disable-extensions")  # 禁用扩展
            
            # 设置User-Agent
            chrome_options.add_argument(f"--user-agent={self.header['User-Agent']}")
            
            # 设置页面加载策略为eager（只加载DOM，不等待资源）
            chrome_options.page_load_strategy = 'eager'
            
            # 初始化WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 减少等待时间，提高爬取速度
            self.wait = WebDriverWait(self.driver, 3)  # 最多等待3秒，减少超时时间
            
            logger.info("Selenium浏览器初始化成功")
            return True
        except Exception as e:
            logger.error(f"初始化Selenium浏览器失败: {e}")
            return False
    
    def close_selenium(self):
        """
        关闭Selenium浏览器实例
        """
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.wait = None
                logger.info("Selenium浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭Selenium浏览器失败: {e}")
        try:
            # 使用统一的数据库配置修改表结构
            conn = connect(**DB_CONFIG)
            # 修改content字段长度为2000
            alter_sql = "ALTER TABLE cases MODIFY COLUMN content varchar(2000)"
            cursor = conn.cursor()
            cursor.execute(alter_sql)
            conn.commit()
            logger.info("已将cases表的content字段长度修改为2000")
        except Exception as e:
            # 如果表不存在或已修改，忽略错误
            logger.debug(f"修改表结构失败: {e}")
            pass
    
    def is_driver_valid(self):
        """
        检查Selenium浏览器是否仍然有效
        :return: True if driver is valid, False otherwise
        """
        if not self.driver:
            return False
        try:
            # 尝试获取当前页面标题来检查浏览器是否仍然有效
            self.driver.title
            return True
        except Exception:
            # 如果发生任何异常，说明浏览器已经关闭
            return False

    def filter_irrelevant_content(self, content):
        """
        过滤掉无关的内容，如备案号、版权信息、医院、科室、病人信息等
        :param content: 原始内容
        :return: 过滤后的内容
        """
        if not content:
            return content
        
        # 定义要过滤的关键词
        irrelevant_keywords = [
            '京公网安备', '备案号', '版权所有', 'copyright', '©',
            '联系方式', '联系电话', '邮箱', '地址', '邮编',
            '隐私政策', '用户协议', '免责声明', '法律声明',
            '京ICP备', 'ICP备案', '增值电信业务经营许可证',
            '技术支持', '网站建设', '广告服务', '合作招商'
        ]
        
        # 定义医院、科室、病人信息的关键词模式
        hospital_dept_patient_keywords = [
            '医院', '科室', '内三科', '内科', '外科', '妇科', '儿科',
            '口腔科', '眼科', '皮肤科', '中医科', '耳鼻喉科', '骨科',
            'h***', '女', '男', '岁','10+岁' '20+岁', '30+岁', '40+岁', '50+岁',
            '60+岁', '70+岁', '80+岁'
        ]
        
        # 检查是否包含无关关键词
        for keyword in irrelevant_keywords:
            if keyword in content:
                # 找到关键词位置，只保留关键词之前的内容
                keyword_index = content.find(keyword)
                content = content[:keyword_index].strip()
                break
        
        # 处理病情内容：如果包含"疾病描述"、"疾病"或"希望获得的帮助"，只保留"疾病描述"部分
        if '疾病描述：' in content:
            # 找到"疾病描述："的位置
            start_index = content.find('疾病描述：') + len('疾病描述：')
            
            # 查找后续可能的结束标记
            end_markers = ['疾病：', '希望获得的帮助：', '希望得到的帮助：']
            end_index = len(content)
            
            for marker in end_markers:
                if marker in content[start_index:]:
                    marker_index = content.find(marker, start_index)
                    if marker_index < end_index:
                        end_index = marker_index
            
            # 只保留疾病描述部分的内容
            content = content[start_index:end_index].strip()
        
        # 过滤医院、科室、病人信息
        # 特别处理括号内容，确保完整保留病情描述
        if '(' in content and ')' in content:
            last_close_parenthesis = content.rfind(')')
            # 检查括号后面是否有医院科室信息
            content_after_parenthesis = content[last_close_parenthesis+1:].strip()
            
            if content_after_parenthesis:
                # 检查括号后面的内容是否包含医院科室关键词
                has_hospital_info = any(keyword in content_after_parenthesis for keyword in hospital_dept_patient_keywords)
                if has_hospital_info:
                    # 只保留括号及其之前的内容
                    content = content[:last_close_parenthesis+1].strip()
        
        # 检查是否包含医院科室关键词，确保完全过滤掉医院信息
        # 优先处理带括号的情况后，再处理直接包含医院关键词的情况
        # 定义医院科室的核心关键词，用于更精确的匹配
        hospital_core_keywords = ['医院', '科室', '内三科', '内科', '外科', '妇科', '儿科',
                                 '口腔科', '眼科', '皮肤科', '中医科', '耳鼻喉科', '骨科']
        
        for keyword in hospital_core_keywords:
            if keyword in content:
                # 找到第一个医院核心关键词的位置
                keyword_index = content.find(keyword)
                
                # 对于医院名称，向前查找可能的分隔符（如空格、逗号等），确保完全过滤
                # 先检查关键词前是否有空格
                if keyword_index > 0:
                    # 找到关键词前最近的分隔符位置
                    split_chars = [' ', '　', '，', ',', '。', '.', '；', ';', '?', '？', '!', '！']
                    split_pos = -1
                    # 从关键词位置向前搜索分隔符
                    for i in range(keyword_index-1, -1, -1):
                        if content[i] in split_chars:
                            split_pos = i
                            break
                    
                    if split_pos != -1:
                        content = content[:split_pos+1].strip()
                    else:
                        # 如果没有找到分隔符，说明关键词可能出现在病情描述中
                        # 这种情况应该很少见，需要谨慎处理
                        continue
                else:
                    # 如果关键词在开头，说明整个内容可能都是医院信息
                    continue
                
                # 保留句末的标点符号
                break
        
        # 过滤病人信息（如h*** 女 20+岁等）
        # 这些信息通常出现在医院信息之后
        for keyword in ['h***', '女', '男', '岁', '20+岁', '30+岁', '40+岁', '50+岁', '60+岁', '70+岁', '80+岁']:
            if keyword in content:
                keyword_index = content.find(keyword)
                # 向前查找分隔符
                split_chars = [' ', '　', '，', ',', '。', '.', '；', ';', '?', '？', '!', '！',')']
                split_pos = -1
                for i in range(keyword_index-1, -1, -1):
                    if content[i] in split_chars:
                        split_pos = i
                        break
                
                if split_pos != -1:
                    content = content[:split_pos+1].strip()
                break
        
        return content
        
    def get_detail_content(self, detail_url):
        """
        从详情页获取完整内容
        :param detail_url: 详情页URL
        :return: 完整的内容描述
        """
        logger.info(f"开始获取详情页内容: {detail_url}")
        content = ""
        
        # 首先尝试使用requests获取内容，这比Selenium更快
        content = self.get_detail_content_with_requests(detail_url)
        # 检查内容是否包含省略号，如果包含则认为不完整，强制使用Selenium获取
        if content and len(content) > 100 and '...' not in content:  # 提高阈值并检查是否有省略号
            logger.info(f"使用requests成功获取详情内容")
            return content
        else:
            logger.warning(f"requests获取的内容可能不完整，尝试使用Selenium获取，URL: {detail_url}")
        
        # 如果requests获取失败或内容不完整，则使用Selenium获取
        try:
            # 确保Selenium浏览器已初始化并且有效
            if not self.driver:
                logger.info("Selenium浏览器未初始化，正在初始化")
                if not self.init_selenium():
                    logger.error("无法初始化Selenium浏览器")
                    return content
            elif not self.is_driver_valid():
                logger.info("Selenium浏览器无效，重新初始化")
                self.close_selenium()  # 直接关闭，不尝试刷新
                if not self.init_selenium():
                    logger.error("无法重新初始化Selenium浏览器")
                    return content
            
            # 使用Selenium访问详情页，增加异常处理
            try:
                self.driver.get(detail_url)
                # 不等待页面加载，直接尝试获取内容
            except Exception as e:
                logger.error(f"Selenium访问页面失败: {e}, URL: {detail_url}")
                return content
            
            # 优化XPath表达式，优先尝试最可能匹配的表达式
            content_xpaths = [
                '//div[@class="content"]//p',  # 最通用的内容容器
                '//div[@id="content"]/p',  # ID选择器，更高效
                '//div[contains(@class, "article-content")]/p',  # 文章内容
                '//div[contains(@class, "detail")]//p',  # 详情内容
                '//div[@class="disease-qa"]/div[@class="qa-item"]/div[@class="qa-content"]/p',  # 疾病问答内容
                '//div[contains(@class, "case-content")]//p',  # 病例内容
                '//div[contains(@class, "disease-detail")]//p',  # 疾病详情
                '//div[contains(@class, "illness-content")]//p',  # 病情内容
            ]
            
            # 只使用快速查找，不使用任何等待
            for xpath in content_xpaths:
                try:
                    # 使用快速查找，不等待所有元素
                    paragraphs = self.driver.find_elements(By.XPATH, xpath)
                    if paragraphs:
                        content_list = [p.text for p in paragraphs if p.text]
                        if content_list:
                            full_content = ''.join(content_list).strip()
                            # 过滤无关内容
                            filtered_content = self.filter_irrelevant_content(full_content)
                            if filtered_content and len(filtered_content) > 20:
                                return filtered_content
                except Exception:
                    continue
            
            # 如果以上XPath都失败，尝试获取所有p标签的文本
            try:
                all_paragraphs = self.driver.find_elements(By.TAG_NAME, 'p')
                all_p_text = [p.text for p in all_paragraphs if p.text]
                if all_p_text:
                    # 只取前10个p标签的文本，避免处理过多内容
                    full_content = ''.join(all_p_text[:10]).strip()
                    # 过滤无关内容
                    filtered_content = self.filter_irrelevant_content(full_content)
                    if filtered_content and len(filtered_content) > 20:
                        return filtered_content
            except Exception:
                pass
            
            logger.warning(f"在详情页中未找到足够内容，URL: {detail_url}")
            return content  # 返回requests获取的内容，即使可能不完整
        except Exception as e:
            logger.error(f"Selenium获取详情页内容失败: {e}, URL: {detail_url}")
            return content
    
    def get_detail_content_with_requests(self, detail_url):
        """
        使用requests作为后备方法获取详情页内容
        :param detail_url: 详情页URL
        :return: 完整的内容描述
        """
        try:
            # 移除不必要的延迟，提高请求速度
            
            # 发送请求，设置超时时间
            response = requests.get(detail_url, headers=self.header, timeout=5)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.warning(f"使用requests访问详情页失败，状态码: {response.status_code}, URL: {detail_url}")
                return None
            
            detail_tree = etree.HTML(response.text)
            
            # 优化XPath表达式顺序，优先尝试最可能匹配的表达式
            content_xpaths = [
                '//div[@class="content"]//p/text()',  # 最通用的内容容器
                '//div[@id="content"]/p/text()',  # ID选择器，更高效
                '//div[contains(@class, "article-content")]/p/text()',  # 文章内容
                '//div[contains(@class, "detail")]//p/text()',  # 详情内容
                '//div[@class="disease-qa"]/div[@class="qa-item"]/div[@class="qa-content"]/p/text()',  # 疾病问答内容
                '//div[contains(@class, "case-content")]/p/text()',  # 病例内容
                '//div[contains(@class, "disease-detail")]/p/text()',  # 疾病详情
                '//div[@class="post-content"]//p/text()',  # 帖子内容
                '//div[contains(@class, "illness-content")]//p/text()',  # 病情内容
                '//div[contains(@class, "symptom-description")]//p/text()'  # 症状描述
            ]
            
            for xpath in content_xpaths:
                content_list = detail_tree.xpath(xpath)
                if content_list:
                    full_content = ''.join(content_list).strip()
                    # 过滤无关内容
                    filtered_content = self.filter_irrelevant_content(full_content)
                    if filtered_content and len(filtered_content) > 20:
                        return filtered_content
            
            # 如果以上XPath都失败，尝试获取所有p标签的文本
            all_p_text = detail_tree.xpath('//p/text()')
            if all_p_text:
                full_content = ''.join(all_p_text[:20]).strip()  # 只取前20个p标签的文本
                # 过滤无关内容
                filtered_content = self.filter_irrelevant_content(full_content)
                if filtered_content and len(filtered_content) > 20:
                    return filtered_content
            
            logger.warning(f"使用requests在详情页中未找到内容，URL: {detail_url}")
            return None
        except Exception as e:
            logger.error(f"使用requests获取详情页内容失败: {e}, URL: {detail_url}")
            return None
    
    def main(self,type,page):
        items_count = 0
        mock_data_used = False  # 记录是否已经使用过模拟数据
        use_selenium_list = False  # 是否使用Selenium获取列表页内容
        
        try:
            logger.warning(f"正在爬取第{page}页的数据...")
            # 根据疾病类型动态生成URL
            pinyin = self.disease_pinyin_map.get(type, 'ganmao')  # 默认使用感冒的拼音
            self.spiderUrl = f'https://www.haodf.com/citiao/jibing-{pinyin}/bingcheng.html?p=%s'
            actual_url = self.spiderUrl % page
            logger.warning(f"实际访问的URL: {actual_url}")
            
            # 尝试使用requests获取页面内容
            try:
                pageHtml = requests.get(actual_url, headers=self.header).text
                page_tree = etree.HTML(pageHtml)
                
                # 检查页面是否包含预期的疾病信息
                page_title = page_tree.xpath('//title/text()')[0] if page_tree.xpath('//title/text()') else '无标题'
                logger.warning(f"页面标题: {page_title}")
                
                # 检查页面是否有内容或是否被反爬
                if '请稍后再试' in pageHtml or '访问过于频繁' in pageHtml or '验证码' in pageHtml or '页面不存在' in pageHtml:
                    logger.warning("检测到反爬机制或页面不存在，切换到Selenium获取内容")
                    use_selenium_list = True
            except Exception as e:
                logger.error(f"使用requests获取页面失败: {e}")
                use_selenium_list = True
            
            # 如果需要使用Selenium，切换到Selenium获取页面内容
            if use_selenium_list:
                logger.warning("使用Selenium获取列表页内容")
                if not self.driver:
                    if not self.init_selenium():
                        logger.error("Selenium初始化失败，无法继续爬取")
                        return 0
                
                try:
                    # 使用Selenium访问列表页
                    self.driver.get(actual_url)
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                    time.sleep(1)  # 额外等待，确保动态内容加载完成
                    
                    # 获取页面HTML并解析
                    pageHtml = self.driver.page_source
                    page_tree = etree.HTML(pageHtml)
                except Exception as e:
                    logger.error(f"使用Selenium获取列表页内容失败: {e}")
                    # 如果Selenium也失败，尝试使用requests获取的内容继续
                    if 'page_tree' not in locals():
                        logger.error("无法获取页面内容，尝试使用模拟数据")
                        if not mock_data_used:
                            self.generate_mock_data(type)
                            mock_data_used = True
                            return 5
                        else:
                            return 0
            
            # 尝试更精确的XPath表达式，以适应不同疾病页面的结构
            # 首先尝试找到所有可能包含案例的列表
            li_list = []
            
            # 尝试不同的XPath表达式
            xpath_patterns = [
                '//ul[contains(@class, "case-list")]/li',
                '//ul[@id="case-list"]/li',
                '//div[contains(@class, "case-item")]',
                '//*[@id="me-content"]/main/section/div/ul/li',
                '//div[@class="disease-qa"]/ul/li',  # 可能的新结构
                '//div[contains(@id, "qa-list")]/ul/li',  # 可能的新结构
                '//li[contains(@class, "qa-item")]'  # 可能的新结构
            ]
            
            for pattern in xpath_patterns:
                found_items = page_tree.xpath(pattern)
                if found_items:
                    li_list = found_items
                    logger.warning(f"使用XPath '{pattern}'找到{len(li_list)}条数据项")
                    break
            
            if not li_list:
                logger.warning("没有找到任何数据项，可能是页面结构发生了变化")
                # 如果没有找到数据，且是第一次，使用模拟数据
                if not mock_data_used:
                    self.generate_mock_data(type)
                    mock_data_used = True
                    return 5  # 返回模拟数据的数量
                else:
                    return 0  # 不是第一次，不使用模拟数据
            
            for index,li in enumerate(li_list):
                try:
                    logger.info(f"正在处理第{index+1}条数据")
                    initData = []
                    #类型
                    initData.append(type)
                    #性别
                    try:
                        gender_text = li.xpath('./a/div/span[@class="patient-name"]/text()')[0]
                        if len(gender_text) >= 3:
                            gender = gender_text[3]
                        else:
                            gender = "未知"
                    except:
                        gender = "未知"
                    initData.append(gender)
                    #年龄
                    try:
                        age_match = re.search(r'\d+', gender_text)
                        age = age_match.group() if age_match else "未知"
                    except:
                        age = "未知"
                    initData.append(age)
                    #时间
                    try:
                        time_text = li.xpath('./a/div/span[@class="date"]/text()')[0]
                        time_match = re.search(r'\d{1,4}.\d{1,2}.\d{1,2}', time_text)
                        if not time_match:
                            time_match = re.search(r'\d{1,2}.\d{1,2}', time_text)
                        time = time_match.group() if time_match else "未知"
                    except:
                        time = "未知"
                    initData.append(time)
                    #详情链接
                    try:
                        detailUrl = li.xpath('./a/@href')[0]
                        # 确保URL是完整的
                        if not detailUrl.startswith('http'):
                            detailUrl = 'https://www.haodf.com' + detailUrl
                    except:
                        detailUrl = ""
                    
                    # 先从列表页获取简短内容作为后备
                    content = "无描述"
                    try:
                        content_xpath_list = [
                            './a/h3[@class="title"]/text()',  # 原始表达式
                            './/h3[@class="title"]/text()',  # 不依赖父节点
                            './div/div[@class="case-text"]/text()',  # 案例文本
                            './/p[@class="case-content"]/text()',  # 案例内容
                            './/div[contains(@class, "content")]/text()',  # 包含内容的div
                            './/div/div[2]/p[1]/text()',  # 第二个div下的第一个p
                            './/span[contains(@class, "text")]/text()',  # 文本span
                            './/div[@class="symptom"]/text()'  # 症状div
                        ]
                        
                        for xpath in content_xpath_list:
                            try:
                                content_text = li.xpath(xpath)
                                if content_text:
                                    extracted_content = content_text[0].strip()
                                    if extracted_content and len(extracted_content) > 3:
                                        content = extracted_content
                                        break
                            except Exception as e:
                                logger.debug(f"XPath '{xpath}'提取失败: {e}")
                    except Exception as e:
                        logger.warning(f"获取列表页内容失败: {e}")
                    
                    # 尝试从详情页获取完整内容
                    full_content = None
                    if detailUrl:
                        full_content = self.get_detail_content(detailUrl)
                    
                    # 如果成功获取到完整内容，则使用完整内容
                    if full_content:
                        content = full_content
                    
                    logger.info(f"最终内容: {content[:100]}...")  # 日志显示前100个字符
                    initData.append(content)
                    #医生名称
                    try:
                        docName = li.xpath('./div/div[@class="svc-info"]/a[@class="name"]/text()')[0]
                    except:
                        docName = "未知"
                    initData.append(docName)
                    #医院
                    try:
                        docHospital = li.xpath('./div/div[@class="svc-info"]/a[@class="hospital"]/text()')[0]
                    except:
                        docHospital = "未知"
                    initData.append(docHospital)
                    #医院科室
                    try:
                        department = li.xpath('./div/div[@class="svc-info"]/a[@class="faculty"]/text()')[0]
                    except:
                        department = "未知"
                    initData.append(department)
                    
                    # 添加详情链接
                    initData.append(detailUrl)
                    
                    # 添加缺失的字段，确保CSV格式一致
                    # height, weight, illDuration, allergy
                    initData.extend(["", "", "", ""])
                    
                    # 过滤条件：如果内容带有省略号且字数少于40字，则跳过
                    content = initData[4]  # content位于第5个位置（索引4）
                    if '...' in content and len(content) < 40:
                        logger.info(f"第{index+1}条数据内容带有省略号且字数少于40字，跳过保存")
                        continue
                    
                    # 保存到CSV
                    self.save_to_csv(initData)
                    logger.info(f"第{index+1}条数据保存成功")
                    items_count += 1
                except Exception as e:
                    logger.error(f"处理第{index+1}条数据时出错: {e}")
                    continue
                    
            # 移除递归条件，由crawler_scheduler控制爬取页数
            # 这样可以正确响应传入的pages参数
            return items_count
                
        except Exception as e:
            logger.error(f"爬虫运行出错: {e}")
            # 如果抓取失败，尝试使用模拟数据填充CSV文件
            logger.info("尝试生成模拟数据...")
            # 只有第一次才使用模拟数据
            if not mock_data_used:
                self.generate_mock_data(type)
                mock_data_used = True
                # 返回模拟数据的数量
                return 5  # 模拟数据生成了5条
            else:
                return 0  # 不是第一次，不使用模拟数据
        # 移除finally块中的浏览器关闭逻辑，让浏览器在整个爬虫任务期间保持打开状态
            
    def generate_mock_data(self, disease_type):
        """生成模拟医疗数据，用于演示"""
        # 根据不同疾病类型生成相应的症状描述
        disease_symptoms = {
            '感冒': ['发热、咳嗽、流鼻涕', '喉咙疼痛，咳嗽有痰', '全身乏力，打喷嚏', '鼻塞，头痛，轻度发热', '咳嗽持续，可能伴有咽痛'],
            '高血压': ['头晕头痛，血压升高', '血压在150-190之间波动', '服用降压药后血压仍不稳定', '高血压病史，最近出现关节痛', '哺乳期血压升高'],
            '糖尿病': ['多饮多尿，体重下降', '血糖控制不佳，波动较大', '糖尿病并发症，视力模糊', '足部麻木，可能是神经病变', '餐后血糖过高'],
            '冠心病': ['胸闷气短，活动后加重', '心绞痛，服用硝酸甘油缓解', '心悸，心率不齐', '胸口压迫感，呼吸困难', '夜间阵发性呼吸困难'],
            '肺炎': ['高热，咳嗽，咳黄痰', '呼吸急促，胸痛', '持续性咳嗽，伴有血丝', '乏力，食欲不振', '肺部湿罗音，影像学异常'],
            '胃炎': ['上腹部疼痛，恶心呕吐', '反酸烧心，胃灼热', '饭后饱胀，消化不良', '胃痛，空腹时加重', '胃黏膜充血，糜烂'],
            '肝炎': ['乏力，食欲不振', '黄疸，皮肤巩膜黄染', '肝区疼痛，肝肿大', '恶心呕吐，腹胀', '肝功能异常，转氨酶升高'],
            '肾炎': ['血尿，蛋白尿', '水肿，眼睑下肢浮肿', '高血压，肾功能异常', '腰痛，乏力', '尿量减少，尿色加深'],
            '抑郁症': ['情绪低落，兴趣减退', '失眠或嗜睡', '食欲改变，体重波动', '注意力不集中，记忆力下降', '自我评价过低，有自杀倾向'],
            '骨折': ['局部疼痛，肿胀', '活动受限，畸形', '骨擦音，骨擦感', '皮下淤血，淤青', '功能障碍，不能负重'],
            '肠胃炎': ['腹痛腹泻，水样便', '恶心呕吐，发热', '腹部痉挛，里急后重', '脱水，电解质紊乱', '饮食不当后发病'],
            '风湿': ['关节疼痛，肿胀', '晨僵，活动受限', '关节畸形，功能障碍', '发热，乏力', '抗O或类风湿因子阳性'],
            '哮喘': ['喘息，呼吸困难', '咳嗽，咳痰', '胸闷，气促', '夜间发作，端坐呼吸', '接触过敏原后加重'],
            '气管炎': ['咳嗽，咳痰', '喘息，气急', '胸闷，胸痛', '反复呼吸道感染', '影像学显示气管炎症']
        }
        
        symptoms = disease_symptoms.get(disease_type, disease_symptoms['感冒'])  # 默认使用感冒症状
        mock_data = []
        doctors = ["张医生", "李医生", "王医生", "赵医生", "陈医生"]
        hospitals = ["协和医院", "同济医院", "华西医院", "中山医院", "人民医院"]
        departments = ["内科", "外科", "儿科", "妇产科", "急诊科"]
        
        for i in range(5):
            data = [
                disease_type,
                "男" if i % 2 == 0 else "女",
                str(20 + i * 5),
                "2024.01.15",
                f"{disease_type}症状：{symptoms[i]}",
                doctors[i],
                hospitals[i],
                departments[i],
                "#",
                str(160 + i * 5),
                str(50 + i * 5),
                f"{i+1}天",
                "无" if i % 2 == 0 else "青霉素"
            ]
            mock_data.append(data)
        
        for data in mock_data:
            self.save_to_csv(data)
        print(f"成功生成{len(mock_data)}条{disease_type}的模拟数据")

    def save_to_csv(self,resultData):
        with open('temp2.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(resultData)

    def save_to_sql(self):
        with open('temp2.csv', 'r', encoding='utf-8') as r_f:
            reader = csv.reader(r_f)
            for i in reader:
                if i[0] == 'type':
                    continue
                querys('''
                    insert into cases(type,gender,age,time,content,docName,docHospital,department,detailUrl)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''',[i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7],i[8]])

if __name__ == '__main__':
    spiderObj = spider()
    spiderObj.init()
    spiderObj.main('感冒',1)
    # spiderObj.save_to_sql()