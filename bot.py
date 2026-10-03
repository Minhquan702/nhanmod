"""Standalone Telegram bot + its own Mini App HTTP server."""
import asyncio,logging,os,signal
from contextlib import suppress
from pathlib import Path
from aiohttp import web
from telegram import BotCommand,InlineKeyboardButton,InlineKeyboardMarkup,WebAppInfo,MenuButtonWebApp
from telegram.ext import Application,CommandHandler
from web_server import make_app,JOBS,save_job,public_origin,STATS

ROOT=Path(__file__).resolve().parent

def app_url():return public_origin()+'/webapp/'

def launch_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton('✦ MỞ MOD SKIN AOV',web_app=WebAppInfo(url=app_url()))]])

async def start(update,context):
    if update.effective_chat.type!='private':
        await update.effective_message.reply_text('Mở cuộc trò chuyện riêng với bot để tạo file skin.');return
    await update.effective_message.reply_text('✦ TD MOD · MOD SKIN AOV\n\nThư viện skin của bạn ngay trong Telegram.\nChọn skin → chọn thiết bị & hiệu ứng → tạo file → làm nhiệm vụ → tải ZIP.\n\n📦 Tối đa 15 skin, mỗi tướng 1 skin.\n🕘 Lịch sử gắn với tài khoản Telegram.\n\nChạm nút bên dưới để bắt đầu.',reply_markup=launch_keyboard())

async def help_command(update,context):
    await update.effective_message.reply_text('1. Mở TD MOD và chọn skin.\n2. Vào Đã chọn, chọn Android / iOS / Cả 2 và sáng đậm.\n3. Bấm Tạo file, chọn có hoặc không nút bấm + hạ địch, xác nhận.\n4. Đợi hoàn tất, làm nhiệm vụ để mở tải.\n5. Xem lại file trong Lịch sử (mặc định 24 giờ).\n\nTải đủ Cần thiết trong trận và Bối cảnh ngoại vi trong game. Thoát hẳn game trước khi giải nén và ghi đè.',reply_markup=launch_keyboard())

async def admin_command(update,context):
    ids={int(x) for x in os.getenv('BOT_ADMIN_IDS','8287067985').split(',') if x.strip().isdigit()}
    if update.effective_user.id not in ids:return
    d=STATS.snapshot(JOBS)
    await update.effective_message.reply_text(f"📊 THỐNG KÊ BOT\nNgười dùng: {d['total']['visitors']}\nYêu cầu: {d['total']['created']}\nThành công: {d['total']['done']}\nLỗi: {d['total']['error']}\nMở tải: {d['total']['download']}\nĐang tạo: {d['running']} · Chờ: {d['queued']}\n\nQuản lý thông báo, ảnh/video, link và nhạc tại:\n{public_origin()}/admin\nĐăng nhập bằng BOT_ADMIN_PASSWORD.")

async def notifications(bot):
    while True:
        for jid,job in list(JOBS.items()):
            uid=job.get('telegram_user_id')
            if not uid or job['state'] not in ('done','error') or (job.get('expires') and job['expires']<time_now()):continue
            phase='unlocked' if job.get('task_complete') else job['state']
            if phase in job.get('telegram_notified',[]):continue
            if time_now()-job.get('notification_retry',0)<60:continue
            text={'done':'✅ File đã tạo xong! Mở Lịch sử trong TD MOD và làm nhiệm vụ để tải ZIP.','unlocked':'🔓 Đã mở khóa file! Mở Lịch sử để tải lại bất cứ lúc nào trước khi hết hạn.','error':'⚠️ Tạo file chưa thành công. Mở Lịch sử để xem lỗi và thử lại.'}[phase]
            try:
                await bot.send_message(uid,text,reply_markup=launch_keyboard())
                job.setdefault('telegram_notified',[]).append(phase)
            except Exception:
                job['notification_retry']=time_now()
                logging.warning('Telegram notification unavailable for job %s',jid)
            save_job(jid)
        await asyncio.sleep(5)

def time_now():
    import time
    return time.time()

async def main():
    token=os.getenv('BOT_TOKEN','').strip()
    if not token:raise RuntimeError('Thiếu BOT_TOKEN trong Variables.')
    public_origin() # Refuse a misconfigured bot before accepting jobs.
    application=Application.builder().token(token).build()
    for name in ('start','mod','webapp','choosehero','run','history','settings'):
        application.add_handler(CommandHandler(name,start))
    application.add_handler(CommandHandler('help',help_command))
    application.add_handler(CommandHandler('admin',admin_command))
    runner=web.AppRunner(make_app());await runner.setup()
    notifier=None
    try:
        await web.TCPSite(runner,'0.0.0.0',int(os.getenv('PORT','8080'))).start()
        async with application:
            await application.bot.set_my_commands([BotCommand('start','Mở TD MOD'),BotCommand('history','Mở lịch sử file'),BotCommand('help','Cách sử dụng'),BotCommand('admin','Quản lý bot')])
            await application.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text='TD MOD',web_app=WebAppInfo(url=app_url())))
            await application.start()
            try:
                await application.updater.start_polling(drop_pending_updates=False)
                notifier=asyncio.create_task(notifications(application.bot))
                stop=asyncio.Event();loop=asyncio.get_running_loop()
                for sig in (signal.SIGINT,signal.SIGTERM):
                    with suppress(NotImplementedError):loop.add_signal_handler(sig,stop.set)
                await stop.wait()
            finally:
                if notifier:
                    notifier.cancel();await asyncio.gather(notifier,return_exceptions=True)
                if application.updater.running:await application.updater.stop()
                await application.stop()
    finally:await runner.cleanup()

if __name__=='__main__':
    os.chdir(ROOT);logging.basicConfig(level=logging.INFO)
    # HTTP clients must not print bot-token URLs into deployment logs.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(main())
