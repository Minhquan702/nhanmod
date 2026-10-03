"""Server-side Mini App authentication. Never trust initDataUnsafe."""
import hashlib,hmac,json,time
from urllib.parse import parse_qsl

def validate_init_data(raw,token,max_age=86400):
    if not raw or not token or len(raw)>16384:raise ValueError('Mở ứng dụng từ nút trong bot Telegram.')
    pairs=parse_qsl(raw,keep_blank_values=True,strict_parsing=True)
    if len({k for k,v in pairs})!=len(pairs):raise ValueError('Dữ liệu Telegram không hợp lệ.')
    fields=dict(pairs);received=fields.pop('hash','')
    check='\n'.join(f'{k}={v}' for k,v in sorted(fields.items()))
    secret=hmac.new(b'WebAppData',token.encode(),hashlib.sha256).digest()
    expected=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,received):raise ValueError('Phiên Telegram không hợp lệ.')
    now=time.time();date=int(fields.get('auth_date','0'))
    if date>now+60 or now-date>max_age:raise ValueError('Phiên đã hết hạn. Đóng ứng dụng rồi mở lại từ bot.')
    user=json.loads(fields.get('user','{}'))
    if type(user.get('id')) is not int or user['id']<=0:raise ValueError('Không xác định được tài khoản Telegram.')
    return user

def owner_session(user_id,token):
    return hmac.new(token.encode(),f'tdmod-bot-owner:{user_id}'.encode(),hashlib.sha256).hexdigest()[:48]
