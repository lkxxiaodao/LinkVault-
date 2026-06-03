class Notifier:
    @staticmethod
    def show(title, message, on_click=None):
        try:
            from win11toast import toast
            toast(title, message, on_click=on_click)
        except ImportError:
            pass

    @staticmethod
    def show_schedule_notification(schedule_name, urls, titles, bookmark_ids):
        title = f'LinkVault - {schedule_name}'
        if len(urls) == 1:
            message = f'该打开 {titles[0]} 了'
        else:
            message = f'该打开 {len(urls)} 个网址了：{", ".join(titles[:3])}'
            if len(titles) > 3:
                message += f' 等{len(titles)}个'

        def on_click():
            from infra.browser_launcher import BrowserLauncher
            for url in urls:
                BrowserLauncher.open_url(url)

        Notifier.show(title, message, on_click=on_click)