import os, uuid, subprocess
from celery import Celery
import yt_dlp

celery_app = Celery('tasks', broker=os.getenv('REDIS_URL'), backend=os.getenv('REDIS_URL'))

@celery_app.task(bind=True, name="process_download_task")
def process_download_task(self, url: str, start_time: int = None, end_time: int = None):
    self.update_state(state='PROCESSING')
    file_id = str(uuid.uuid4())
    raw_path = f"/app/downloads/{file_id}_raw.mp4"
    final_path = f"/app/downloads/{file_id}.mp4"
    try:
        ydl_opts = {
            'format': 'best', 'outtmpl': raw_path, 'noplaylist': True, 'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        if os.getenv('PROXY_URL'): ydl_opts['proxy'] = os.getenv('PROXY_URL')
        if os.path.exists("/app/worker/cookies.txt"): ydl_opts['cookiefile'] = "/app/worker/cookies.txt"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if start_time is not None and end_time is not None:
            subprocess.run(['ffmpeg', '-y', '-i', raw_path, '-ss', str(start_time), '-to', str(end_time), '-c', 'copy', final_path], check=True)
            if os.path.exists(raw_path): os.remove(raw_path)
        else:
            os.rename(raw_path, final_path)
        return {"status": "success", "url": f"/downloads/{file_id}.mp4"}
    except Exception as e:
        if os.path.exists(raw_path): os.remove(raw_path)
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise e
