import threading
import time
import datetime
import schedule
from data.schedule_repo import ScheduleRepo
from data.bookmark_repo import BookmarkRepo
from data.history_repo import HistoryRepo
from infra.browser_launcher import BrowserLauncher
from infra.notifier import Notifier


class ScheduleEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._running = False
                    cls._instance._thread = None
        return cls._instance

    def start(self):
        if self._running:
            return
        self._running = True
        self._load_jobs()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        schedule.clear()

    def reload(self):
        schedule.clear()
        self._load_jobs()

    def _load_jobs(self):
        schedule.clear()
        active_schedules = ScheduleRepo.get_active()
        for sched in active_schedules:
            time_str = f"{sched['hour']:02d}:{sched['minute']:02d}"
            schedule.every().day.at(time_str).do(self._trigger, sched['id'])

    def _run_loop(self):
        while self._running:
            schedule.run_pending()
            time.sleep(1)

    def _should_trigger_today(self, sched):
        repeat_type = sched['repeat_type']
        if repeat_type == 'once':
            return True
        if repeat_type == 'daily':
            return True
        today = datetime.date.today()
        weekday = today.weekday()
        if repeat_type == 'weekdays':
            return weekday < 5
        if repeat_type == 'weekly':
            import json
            days = json.loads(sched.get('repeat_days', '[]'))
            if days:
                return weekday in days
            return weekday == today.weekday()
        if repeat_type == 'biweekly':
            import json
            days = json.loads(sched.get('repeat_days', '[]'))
            if days:
                return weekday in days and today.isocalendar()[1] % 2 == 0
            return today.isocalendar()[1] % 2 == 0
        if repeat_type == 'monthly':
            return today.day == 1
        if repeat_type == 'custom':
            import json
            days = json.loads(sched.get('repeat_days', '[]'))
            return weekday in days
        return False

    def _trigger(self, schedule_id):
        sched = ScheduleRepo.get_by_id(schedule_id)
        if not sched or not sched['is_active']:
            return
        if not self._should_trigger_today(sched):
            return
        bookmarks = ScheduleRepo.get_bookmarks(schedule_id)
        if not bookmarks:
            return
        urls = [b['url'] for b in bookmarks]
        titles = [b['title'] for b in bookmarks]
        for bm in bookmarks:
            BrowserLauncher.open_url(bm['url'], bm.get('default_browser'))
            HistoryRepo.record(bm['id'], 'schedule')
        Notifier.show_schedule_notification(
            schedule_name=sched['name'],
            urls=urls,
            titles=titles,
            bookmark_ids=[b['id'] for b in bookmarks]
        )
        if sched['repeat_type'] == 'once':
            ScheduleRepo.update(schedule_id, is_active=0)
            self.reload()

    @staticmethod
    def add_schedule(name, hour, minute, repeat_type, repeat_days=None, bookmark_ids=None):
        schedule_id = ScheduleRepo.create(name, hour, minute, repeat_type, repeat_days)
        if bookmark_ids:
            for i, bid in enumerate(bookmark_ids):
                ScheduleRepo.add_bookmark(schedule_id, bid, i)
        ScheduleEngine().reload()
        return schedule_id

    @staticmethod
    def update_schedule(schedule_id, **kwargs):
        ScheduleRepo.update(schedule_id, **kwargs)
        ScheduleEngine().reload()

    @staticmethod
    def delete_schedule(schedule_id):
        ScheduleRepo.delete(schedule_id)
        ScheduleEngine().reload()

    @staticmethod
    def toggle_schedule(schedule_id, active):
        ScheduleRepo.update(schedule_id, is_active=1 if active else 0)
        ScheduleEngine().reload()

    @staticmethod
    def open_schedule_bookmarks(schedule_id):
        bookmarks = ScheduleRepo.get_bookmarks(schedule_id)
        for bm in bookmarks:
            BrowserLauncher.open_url(bm['url'], bm.get('default_browser'))
            HistoryRepo.record(bm['id'], 'schedule')