import os
import traceback
from dotenv import load_dotenv

from random import randint
import time

# 구글 웹드라이버를 사용하기 위한 추가구문
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common import ElementClickInterceptedException
from selenium.common import ElementNotInteractableException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver import Keys

# 캡차 처리
import pytesseract
from PIL import Image
import numpy as np
import uuid
import cv2
import re

#암복호화
from util.crypt import AESCipher
from util.db_helper import db_helper
from util.log import Log

load_dotenv()


class Attendance(object):
    # 옵션 생성
    options = Options()
    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ko")
    options.add_argument('--start-fullscreen')
    options.add_argument('--window-size=1920x1080')

    def __init__(self, domain_accnt_data):
        self.domain_accnt_data = domain_accnt_data
        self.sleep = randint(int(os.getenv('MIN_RANDOM_VAL')), int(os.getenv('MAX_RANDOM_VAL')))
        self.try_cnt = 0
        self.attend_try_cnt = 0
        self.browser = None

        self.domain_seq_id = self.domain_accnt_data["domain_seq_id"]
        self.domain_accnt_id = self.domain_accnt_data["domain_accnt_id"]

        with db_helper.get_resource_rdb() as (cursor, _):
            cursor.execute(os.getenv('UPDATE_ATNDNC_STTS_CD'), ('2', self.domain_seq_id, self.domain_accnt_id,))

            cursor.execute(os.getenv('ACT_LIST'), (self.domain_seq_id,'N',))
            self.act_list = cursor.fetchall()

            cursor.execute(os.getenv('ACT_LIST'), (self.domain_seq_id,'Y',))
            self.retry_act_list = cursor.fetchall()

        self.log = Log(self.domain_seq_id, self.domain_accnt_id)
        self.log.print("Attendance 초기화 완료")

    def run(self):
        self.log.print("Attendance Run")
        self.log.print(f"{self.sleep} 초 대기")

        run_done_f = False  # 출석 실행 플래그
        while not run_done_f:
            if not self.try_cnt == 0:
                self.log.print(f"Attendance {str(self.try_cnt)}회 재시도 중")

            try:
                time.sleep(self.sleep)

                service = Service()
                self.browser = webdriver.Chrome(service=service, options=Attendance.options)
                self.browser.set_window_position(0, 0)
                self.browser.maximize_window()

                for idx, act_data in enumerate(self.act_list):
                    self.browser.implicitly_wait(10)
                    try:
                        self.run_action(act_data)
                    except Exception as e:
                        self.browser.quit()
                        raise e

                retry_f = True  # 출석 실행 플래그
                while retry_f:

                    if not self.attend_try_cnt == 0:
                        self.log.print(f"출석 {str(self.attend_try_cnt)}회 재시도 중")

                    for idx, act_data in enumerate(self.retry_act_list):
                        self.browser.implicitly_wait(10)
                        try:
                            self.run_action(act_data)
                            retry_f = False  # 행동 완료시 반복 미실행

                        except Exception as e:
                            if self.attend_try_cnt < 20:
                                self.attend_try_cnt += 1

                                if e.args[0] == "Captcha Error":
                                    self.log.print("출석 실패, 재시도 합니다.")
                                    self.browser.quit()
                                    retry_f = True  # 행동 에러시 반복

                                else:
                                    self.browser.quit()
                                    raise e

                            else:
                                self.browser.quit()
                                self.log.print("출석 횟수 20회 초과 종료")
                                raise e

                self.browser.quit()
                self.log.print("출석체크 완료")

                with db_helper.get_resource_rdb() as (cursor, _):
                    cursor.execute(os.getenv('UPDATE_ATNDNC_STRT_DTTM'), (self.domain_seq_id,self.domain_accnt_id,self.domain_seq_id,self.domain_accnt_id,))

                self.log.print("Attendance 완료")
                run_done_f = True

            except Exception as e:
                self.log.print(str(e))
                self.log.print(str(traceback.print_exc()))
                self.log.print("Attendance Exception, 재시도 합니다.")

                if self.try_cnt < 5:
                    self.try_cnt += 1

                    run_done_f = False
                    self.sleep = randint(1, 10)
                else:
                    run_done_f = True
                    self.log.print("Attendance 재시도 횟수 5회 초과 종료")

                    with db_helper.get_resource_rdb() as (cursor, _):
                        cursor.execute(os.getenv('UPDATE_ATNDNC_STTS_CD'), ('9', self.domain_seq_id, self.domain_accnt_id,))

    def run_action(self, act_data):
        act_typ_cd = act_data["act_typ_cd"]
        act_dtl = act_data["act_dtl"]

        functios = {
            "move": self.move_url,
            "input": self.input_value,
            "click": self.click_element,
            "confirm": self.confirm_alert,
            "captcha": self.pass_captcha,
            "if_captcha": self.if_pass_captcha
        }

        func = functios[act_typ_cd]
        func(act_dtl)

    def move_url(self, act_dtl):
        self.log.print(f"move_url : param: {act_dtl}")
        url = self.domain_accnt_data["domain_addrs"]+act_dtl["location"]
        self.browser.get(url)
        self.log.print(f"move_url : {url}로 이동 완료")

    def input_value(self, act_dtl, path="xpath"):
        self.log.print(f"input_value : param: {act_dtl}")
        xpath = act_dtl[path]
        el_input_value = ""

        if act_dtl.get("value"):
            el_input_value = act_dtl["value"]
        else:
            if act_dtl.get("column"):
                el_input_value = self.domain_accnt_data[act_dtl["column"]]

        log_value = el_input_value

        if act_dtl.get("decrypt"):
            if act_dtl["decrypt"] == "Y":
                decrypt = AESCipher.decrypt(el_input_value)  # 3.암호화된 메시지를 AES 대칭키 암호화 방식으로 복호화
                el_input_value = decrypt

        el = self.browser.find_elements("xpath", xpath)[0]

        el.send_keys(el_input_value)
        self.log.print(f"input_value : {xpath}에 {log_value} 입력 완료")

    def click_element(self, act_dtl, path="xpath"):
        self.log.print(f"click_element : param: {act_dtl}, {path}")
        xpath = act_dtl[path]
        try:
            el = self.browser.find_elements("xpath", xpath)[0]
            try:
                el.click()
                self.log.print(f"click_element : {xpath} 클릭 완료")
            except ElementNotInteractableException:
                el.send_keys(Keys.ENTER)
                self.log.print(f"click_element : {xpath} 엔터해서 클릭 완료")
            except ElementClickInterceptedException:
                self.browser.execute_script("arguments[0].click();", el)
                self.log.print(f"click_element : {xpath} 자바스크립트 클릭 완료")

            time.sleep(2)

        except Exception as e:
            raise e

    def confirm_alert(self, act_dtl):
        self.log.print(f"confirm_alert")
        alert = self.browser.switch_to.alert
        alert.accept()
        self.log.print(f"confirm_alert : 얼럿창 확인완료")

    def pass_captcha(self, act_dtl):
        #pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        self.log.print(f"pass_captcha : param: {act_dtl}")
        el = self.browser.find_elements("xpath", act_dtl["img_xpath"])[0]
        target_uuid = str(uuid.uuid1())

        img_name = target_uuid + ".png"
        el.screenshot(img_name)

        img = np.array(Image.open(img_name))

        norm_img = np.zeros((img.shape[0], img.shape[1]))

        img = cv2.normalize(img, norm_img, 0, 255, cv2.NORM_MINMAX)
        img = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY)[1]
        # print(type(cv2.THRESH_BINARY), cv2.THRESH_BINARY)
        img = cv2.GaussianBlur(img, (1, 1), 0)

        text = pytesseract.image_to_string(img)
        text = re.sub('[^a-zA-Z0-9]', " ", text).strip().replace(" ", "")

        os.remove(img_name)
        print(img_name + " 추출결과 : " + text)

        act_dtl["value"] = text
        self.input_value(act_dtl, "input_xpath")

        self.click_element(act_dtl, "click_xpath")

        alert = self.browser.switch_to.alert
        alert_text = alert.text
        alert.accept()

        print("얼럿 : " + alert_text)

        self.log.print(f"pass_captcha : 캡차 문자{text} 입력 완료. {alert_text}")

        if alert_text != act_dtl["complate_msg"]:
            raise Exception("Captcha Error")

    def if_pass_captcha(self, act_dtl):
        try:
            self.log.print(f"if_pass_captcha : param: {act_dtl}")
            if len(self.browser.find_elements("xpath", act_dtl["img_xpath"])) > 0:
                self.pass_captcha(act_dtl)
        except UnexpectedAlertPresentException:
            self.log.print(f"if_pass_captcha : 캡차 없음")
            return
