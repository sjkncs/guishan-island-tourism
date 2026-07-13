# -*- coding: utf-8 -*-
"""
小红书 QR 码登录脚本
生成二维码 -> 用户扫码 -> 自动提取完整Cookie（含web_session）
"""
import sys, os, time, json

sys.stdout.reconfigure(encoding='utf-8')

# 切换到 XHS_ALL_IN_ONE 目录
XHS_DIR = r'E:\几乎所有社交媒体的逆向工程\XHS_ALL_IN_ONE'
os.chdir(XHS_DIR)
sys.path.insert(0, XHS_DIR)

from apis.xhs_pc_login_apis import XHSLoginApi

def main():
    login_api = XHSLoginApi()
    
    # Step 1: 生成初始Cookie
    print("[1/4] 生成初始Cookie...")
    cookies = login_api.generate_init_cookies()
    print(f"  a1: {cookies.get('a1', '')[:20]}...")
    print(f"  webId: {cookies.get('webId', '')[:20]}...")
    print(f"  sec_poison_id: {cookies.get('sec_poison_id', 'N/A')[:20]}...")
    print(f"  gid: {cookies.get('gid', 'N/A')[:20]}...")
    
    # Step 2: 生成二维码
    print("\n[2/4] 生成登录二维码...")
    success, msg, data = login_api.generate_qrcode(cookies)
    if not success:
        print(f"  失败: {msg}")
        return
    
    qr_url = data['qr_url']
    qr_id = data['qr_id']
    code = data['code']
    cookies = data['cookies']
    
    print(f"  QR URL: {qr_url[:50]}...")
    print(f"  QR ID: {qr_id}")
    
    # Step 3: 保存二维码图片
    import qrcode
    img = qrcode.make(qr_url)
    qr_path = r'C:\Users\Administrator\.qoderwork\workspace\mritsdpuqphp34kx\outputs\xhs_login_qr.png'
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    img.save(qr_path)
    print(f"\n  二维码已保存到: {qr_path}")
    print("  请用小红书APP扫描此二维码登录！")
    
    # Step 4: 轮询扫码状态
    print("\n[3/4] 等待扫码...")
    max_wait = 120  # 2分钟超时
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        time.sleep(3)
        success, msg, cookies = login_api.check_qrcode_status(qr_id, code, cookies)
        elapsed = int(time.time() - start_time)
        
        if '验证成功' in msg:
            print(f"\n  [{elapsed}s] 登录成功!")
            break
        elif '过期' in msg:
            print(f"\n  [{elapsed}s] 二维码已过期，请重新运行脚本")
            return
        else:
            print(f"  [{elapsed}s] {msg}...", end='\r')
    else:
        print(f"\n  超时({max_wait}s)，请重新运行脚本")
        return
    
    # Step 5: 提取完整Cookie
    print(f"\n[4/4] 提取完整Cookie...")
    
    # 获取 web_session
    web_session = cookies.get('web_session', '')
    if web_session:
        print(f"  web_session: {web_session[:20]}... (OK)")
    else:
        print("  web_session: 未获取到 (可能登录失败)")
        return
    
    # 构建完整Cookie字符串
    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
    print(f"\n  Cookie总长度: {len(cookie_str)}")
    print(f"  包含字段: {list(cookies.keys())}")
    
    # 验证Cookie有效性
    print("\n  验证Cookie...")
    success, msg, user_info = login_api.get_user_info(cookies)
    if success:
        print(f"  用户: {user_info}")
    else:
        print(f"  验证失败: {msg}")
    
    # 保存Cookie
    env_path = r'E:\珠海桂山岛案例\数据采集\scripts\.env'
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(f'XHS_COOKIES={cookie_str}\n')
    print(f"\n  Cookie已保存到: {env_path}")
    
    # 同时保存到 XHS_ALL_IN_ONE 的 .env
    xhs_env = os.path.join(XHS_DIR, '.env')
    with open(xhs_env, 'w', encoding='utf-8') as f:
        f.write(f'COOKIES={cookie_str}\n')
    print(f"  同时保存到: {xhs_env}")
    
    print("\n  登录完成！现在可以使用Spider_XHS采集桂山岛评论了。")
    return cookie_str

if __name__ == "__main__":
    main()
