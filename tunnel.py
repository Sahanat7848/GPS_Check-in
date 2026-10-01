"""
Utility script to share your local GPS Check-in server over HTTPS using ngrok.
Usage:
    python tunnel.py
    python tunnel.py <your_ngrok_authtoken>
"""
import sys
import os
from pyngrok import ngrok, conf

PORT = int(os.getenv("PORT", 5001))

def main():
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    elif os.getenv("NGROK_AUTHTOKEN"):
        token = os.getenv("NGROK_AUTHTOKEN")
        
    if token:
        ngrok.set_auth_token(token)
        print(f"✅ ตั้งค่า Ngrok Auth Token เรียบร้อยแล้ว")
    else:
        # Check if auth token is already configured
        try:
            config = conf.get_default()
            if not config.auth_token:
                print("⚠️ ยังไม่ได้ตั้งค่า Ngrok Auth Token")
                print("สมัครฟรีได้ที่: https://dashboard.ngrok.com/signup")
                print("และรัน: python tunnel.py <YOUR_AUTHTOKEN>\n")
        except Exception:
            pass

    try:
        print(f"🚀 กำลังสร้างลิงก์ HTTPS สาธารณะสำหรับพอร์ต {PORT}...")
        public_url = ngrok.connect(PORT, bind_tls=True).public_url
        print("\n" + "="*60)
        print(f"🎉 ลิงก์ออนไลน์พร้อมแชร์ให้เพื่อนใช้งาน:")
        print(f"👉 หน้าหลัก: {public_url}")
        print(f"👉 ลิงก์เช็กชื่อวิชา CS101: {public_url}/c/CS101")
        print(f"👉 แดชบอร์ดผู้สอน: {public_url}/instructor")
        print("="*60)
        print("💡 หมายเหตุ: กด Ctrl+C เพื่อหยุดการแชร์ลิงก์\n")
        
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
    except KeyboardInterrupt:
        print("\n👋 ปิดการเชื่อมต่อ Tunnel เรียบร้อยแล้ว")
        ngrok.kill()
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        print("แนะนำให้สมัครบัญชีฟรีที่ https://ngrok.com เพื่อรับ Auth Token ฟรีครับ")

if __name__ == "__main__":
    main()
