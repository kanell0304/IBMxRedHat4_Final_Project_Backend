import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from typing import Tuple


class EmailService:

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # 비밀번호 재설정 이메일 발신
    def _create_reset_code_html(self, reset_code: str, username: str) -> str:
        # html폼 으로 css를 적용해서 발신
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body{{font-family: Arial, sans-serif; line-height: 1.6; color: #333;}}
                    .container{{max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;}}
                    .content{{background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}}
                    .code-box{{background-color: #f0f0f0; padding: 20px; margin: 20px 0; text-align: center; border-radius: 8px; border: 2px dashed #4CAF50;}}
                    .code{{font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4CAF50; font-family: monospace;}}
                    .warning{{background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;}}
                    .footer{{margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center;}}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="content">
                        <h2>비밀번호 재설정 인증코드</h2>
                        <p>안녕하세요, <strong>{username}</strong>님!</p>
                        <p>비밀번호 재설정을 위한 인증코드입니다. 아래 코드를 입력해주세요.</p>

                        <div class="code-box">
                            <div class="code">{reset_code}</div>
                        </div>

                        <div class="warning">
                            <strong>주의사항</strong>
                            <ul>
                                <li>1. 이 코드는 <strong>15분간만 유효</strong>합니다.</li>
                                <li>2. 본인이 요청하지 않았다면 이 이메일을 무시하세요.</li>
                                <li>3. 코드를 타인과 공유하지 마세요.</li>
                            </ul>
                        </div>
                    </div>
                    <div class="footer">
                        <p>본 이메일은 'Spaghetti' 에서 자동으로 발송되었습니다.</p>
                        <p>문의사항이 있으시면 {self.gmail_user}로 연락주세요.</p>
                    </div>
                </div>
            </body>
            </html>
            """

    # 인증코드 이메일 발송
    async def send_reset_code_email(self, recipient_email: str, username: str, reset_code: str) -> Tuple[bool, str]:
        try:
            # MIME 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "[Spaghetti] 비밀번호 재설정 인증코드"
            msg['From'] = self.gmail_user
            msg['To'] = recipient_email

            html_content = self._create_reset_code_html(reset_code, username)

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 동기 작업을 별도 스레드에서 실행
            def send_sync():
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.gmail_user, self.gmail_password)
                    server.send_message(msg)

            # 동기 함수를 비동기로 실행
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_sync)

            return True, f"인증코드가 {recipient_email}로 발송되었습니다."

        except Exception as e:
            return False, f"이메일 발송 실패: {str(e)}"

# 싱글톤 인스턴스 생성
email_service = EmailService()
