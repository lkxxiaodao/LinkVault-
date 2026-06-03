import datetime
import json
from collections import defaultdict
from data.history_repo import HistoryRepo
from data.bookmark_repo import BookmarkRepo
from data.schedule_repo import ScheduleRepo
from data.database import get_connection
from infra.config import HABIT_ANALYSIS_DAYS, HABIT_CONSECUTIVE_DAYS, HABIT_TIME_SLOT_HOURS


class HabitSuggestion:
    def __init__(self, bookmark, hour_range, consecutive_days, suggestion_time):
        self.bookmark = bookmark
        self.hour_range = hour_range
        self.consecutive_days = consecutive_days
        self.suggestion_time = suggestion_time


class HabitAnalyzer:
    @staticmethod
    def record_open(bookmark_id, via='manual'):
        HistoryRepo.record(bookmark_id, via)

    @staticmethod
    def is_enabled():
        conn = get_connection()
        row = conn.execute(
            'SELECT value FROM settings WHERE key = ?', ('habit_analysis_enabled',)
        ).fetchone()
        conn.close()
        return row and row['value'] == '1'

    @staticmethod
    def analyze():
        if not HabitAnalyzer.is_enabled():
            return []

        records = HistoryRepo.get_recent(HABIT_ANALYSIS_DAYS)
        if not records:
            return []

        grouped = defaultdict(list)
        for r in records:
            bookmark_id = r['bookmark_id']
            opened_at = r['opened_at']
            dt = datetime.datetime.strptime(opened_at, '%Y-%m-%d %H:%M:%S')
            date_key = dt.strftime('%Y-%m-%d')
            hour_slot = (dt.hour // HABIT_TIME_SLOT_HOURS) * HABIT_TIME_SLOT_HOURS
            grouped[(bookmark_id, hour_slot)].append(date_key)

        suggestions = []
        for (bookmark_id, hour_slot), dates in grouped.items():
            unique_dates = sorted(set(dates))
            if len(unique_dates) < HABIT_CONSECUTIVE_DAYS:
                continue

            consecutive = 1
            max_consecutive = 1
            for i in range(1, len(unique_dates)):
                d1 = datetime.datetime.strptime(unique_dates[i - 1], '%Y-%m-%d').date()
                d2 = datetime.datetime.strptime(unique_dates[i], '%Y-%m-%d').date()
                if (d2 - d1).days == 1:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 1

            if max_consecutive < HABIT_CONSECUTIVE_DAYS:
                continue

            if HabitAnalyzer._already_has_schedule_for_bookmark(bookmark_id, hour_slot):
                continue

            bookmark = BookmarkRepo.get_by_id(bookmark_id)
            if not bookmark:
                continue

            suggestion_time = f"{hour_slot:02d}:00"
            suggestions.append(
                HabitSuggestion(bookmark, (hour_slot, hour_slot + HABIT_TIME_SLOT_HOURS),
                                max_consecutive, suggestion_time)
            )

        return suggestions

    @staticmethod
    def _already_has_schedule_for_bookmark(bookmark_id, hour_slot):
        schedules = ScheduleRepo.get_all()
        for s in schedules:
            sched_hour = s['hour']
            if abs(sched_hour - hour_slot) <= 1:
                sched_bookmarks = ScheduleRepo.get_bookmarks(s['id'])
                if any(b['id'] == bookmark_id for b in sched_bookmarks):
                    return True
        return False