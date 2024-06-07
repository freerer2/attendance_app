import os
import base64
import hashlib
from Crypto.Cipher import AES # 대칭키를 사용하기 위한 모듈 임포트
from dotenv import load_dotenv

load_dotenv()

BS = 16 # blocksize를 16바이트로 고정시켜야 함(AES의 특징)

# AES에서는 블럭사이즈가 128bit 즉 16byte로 고정되어 있어야 하므로 문자열을 encrypt()함수 인자로 전달시
# 입력 받은 데이터의 길이가 블럭사이즈의 배수가 아닐때 아래와 같이 패딩을 해주어야 한다.
# 패딩: 데이터의 길이가 블럭사이즈의 배수가 아닐때 마지막 블록값을 추가해 블록사이즈의 배수로 맞추어 주는 행위
pad = (lambda s: s+ (BS - len(s) % BS) * chr(BS - len(s) % BS).encode())
unpad = (lambda s: s[:-ord(s[len(s)-1:])])


class AESCipher:
    key = hashlib.sha256(os.getenv('CRYPT_KEY').encode()).digest()

    @staticmethod
    def encrypt(message):  # 암호화 함수
        message = message.encode() # 문자열 인코딩
        raw = pad(message)  # 인코딩된 문자열을 패딩처리
        cipher = AES.new(AESCipher.key, AES.MODE_CBC, AESCipher.__iv().encode('utf8'))  # AES 암호화 알고리즘 처리(한글처리를 위해 encode('utf8') 적용)
        enc = cipher.encrypt(raw) # 패딩된 문자열을 AES 알고리즘으로 암호화
        return base64.b64encode(enc).decode('utf-8') # 암호화된 문자열을 base64 인코딩 후 리턴

    @staticmethod
    def decrypt(enc):  # 복호화 함수 -> 암호화의 역순으로 진행
        enc = base64.b64decode(enc)  # 암호화된 문자열을 base64 디코딩 후
        cipher = AES.new(AESCipher.key, AES.MODE_CBC, AESCipher.__iv().encode('utf8'))  # AES암호화 알고리즘 처리(한글처리를 위해 encode('utf8') 적용)
        dec = cipher.decrypt(enc)  # base64 디코딩된 암호화 문자열을 복호화
        return unpad(dec).decode('utf-8') # 복호화된 문자열에서 패딩처리를 풀고(unpading) 리턴

    @staticmethod
    def __iv():
        return chr(0) * 16