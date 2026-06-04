import subprocess
import os
import json
import webbrowser
import winreg

BROWSER_DEFINITIONS = {
    'chrome': {
        'name': 'Google Chrome',
        'exe': 'chrome.exe',
        'reg_keys': [
            (winreg.HKEY_CURRENT_USER, r'Software\Google\Chrome'),
        ],
    },
    'edge': {
        'name': 'Microsoft Edge',
        'exe': 'msedge.exe',
    },
    'firefox': {
        'name': 'Mozilla Firefox',
        'exe': 'firefox.exe',
        'reg_keys': [
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Mozilla\Mozilla Firefox'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Mozilla\Mozilla Firefox'),
        ],
    },
    'qq': {
        'name': 'QQ浏览器',
        'exe': 'QQBrowser.exe',
        'reg_uninstall_names': ['QQBrowser'],
    },
    '360safe': {
        'name': '360安全浏览器',
        'exe': '360se.exe',
        'reg_uninstall_names': ['360se', '360安全浏览器'],
    },
    '360speed': {
        'name': '360极速浏览器',
        'exe': '360chrome.exe',
        'reg_uninstall_names': ['360Chrome', '360极速浏览器'],
    },
    'brave': {
        'name': 'Brave Browser',
        'exe': 'brave.exe',
    },
    'opera': {
        'name': 'Opera Browser',
        'exe': 'opera.exe',
        'reg_keys': [
            (winreg.HKEY_CURRENT_USER, r'Software\Opera Software'),
        ],
    },
    'vivaldi': {
        'name': 'Vivaldi',
        'exe': 'vivaldi.exe',
        'reg_keys': [
            (winreg.HKEY_CURRENT_USER, r'Software\Vivaldi'),
        ],
    },
    'sogou': {
        'name': '搜狗浏览器',
        'exe': 'SogouExplorer.exe',
        'reg_uninstall_names': ['SogouExplorer', '搜狗浏览器', '搜狗高速浏览器'],
    },
    'maxthon': {
        'name': '傲游浏览器',
        'exe': 'Maxthon.exe',
        'reg_uninstall_names': ['Maxthon', '傲游浏览器'],
    },
    'uc': {
        'name': 'UC浏览器',
        'exe': 'UCBrowser.exe',
        'reg_uninstall_names': ['UCBrowser', 'UC浏览器'],
    },
    'chromium': {
        'name': 'Chromium',
        'exe': 'chrome.exe',
        'reg_uninstall_names': ['Chromium'],
    },
    'yandex': {
        'name': 'Yandex Browser',
        'exe': 'browser.exe',
        'reg_keys': [
            (winreg.HKEY_CURRENT_USER, r'Software\Yandex'),
        ],
    },
}

COMMON_INSTALL_ROOTS = [
    r'C:\Program Files',
    r'C:\Program Files (x86)',
    r'D:\Program Files',
    r'D:\Program Files (x86)',
    r'E:\Program Files',
    r'E:\Program Files (x86)',
]

LOCAL_APPDATA_ROOTS = []


def _get_local_appdata_roots():
    if LOCAL_APPDATA_ROOTS:
        return LOCAL_APPDATA_ROOTS
    roots = []
    try:
        roots.append(os.environ.get('LOCALAPPDATA', ''))
    except Exception:
        pass
    try:
        userprofile = os.environ.get('USERPROFILE', '')
        if userprofile:
            roots.append(os.path.join(userprofile, 'AppData', 'Local'))
    except Exception:
        pass
    LOCAL_APPDATA_ROOTS.extend([r for r in roots if r])
    return LOCAL_APPDATA_ROOTS


class BrowserLauncher:
    _cached_browsers = None

    @staticmethod
    def open_url(url, browser_path=None):
        if browser_path and os.path.exists(browser_path):
            subprocess.Popen([browser_path, url])
        else:
            webbrowser.open(url)

    @staticmethod
    def _scan_all_browsers():
        installed = {}
        _scan_app_paths_registry(installed)
        _scan_uninstall_registry(installed)
        _scan_filesystem(installed)
        _load_custom_browsers(installed)
        return installed

    @staticmethod
    def get_installed_browsers():
        if BrowserLauncher._cached_browsers is None:
            BrowserLauncher._cached_browsers = BrowserLauncher._scan_all_browsers()
        return BrowserLauncher._cached_browsers

    @staticmethod
    def refresh_browser_cache():
        """强制刷新浏览器缓存（安装新浏览器后调用）"""
        BrowserLauncher._cached_browsers = BrowserLauncher._scan_all_browsers()

    @staticmethod
    def get_custom_browsers():
        from core.config_manager import ConfigManager
        raw = ConfigManager.get('custom_browsers', '[]')
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def add_custom_browser(name, path):
        browsers = BrowserLauncher.get_custom_browsers()
        for b in browsers:
            if b['path'].lower() == path.lower():
                b['name'] = name
                break
        else:
            browsers.append({'name': name, 'path': path})
        from core.config_manager import ConfigManager
        ConfigManager.set('custom_browsers', json.dumps(browsers, ensure_ascii=False))

    @staticmethod
    def remove_custom_browser(path):
        browsers = BrowserLauncher.get_custom_browsers()
        browsers = [b for b in browsers if b['path'].lower() != path.lower()]
        from core.config_manager import ConfigManager
        ConfigManager.set('custom_browsers', json.dumps(browsers, ensure_ascii=False))


def _scan_app_paths_registry(installed):
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths'),
        (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'),
    ]

    for browser_id, info in BROWSER_DEFINITIONS.items():
        if browser_id in installed:
            continue
        exe_name = info['exe']

        for hkey_root, subkey in roots:
            try:
                with winreg.OpenKey(hkey_root, fr'{subkey}\{exe_name}') as key:
                    path = winreg.QueryValue(key, None)
                    if path and os.path.exists(path):
                        installed[browser_id] = path
                        break
            except OSError:
                continue

    for browser_id, info in BROWSER_DEFINITIONS.items():
        if browser_id in installed:
            continue
        for hkey_root, parent_key in info.get('reg_keys', []):
            try:
                with winreg.OpenKey(hkey_root, parent_key) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            i += 1
                            with winreg.OpenKey(key, subkey_name) as sk:
                                try:
                                    path = winreg.QueryValueEx(sk, 'Path')[0]
                                    full = os.path.join(path, info['exe'])
                                    if os.path.exists(full):
                                        installed[browser_id] = full
                                        break
                                except OSError:
                                    pass
                        except OSError:
                            break
                    if browser_id in installed:
                        break
            except OSError:
                continue


def _scan_uninstall_registry(installed):
    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
        (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
    ]

    reg_data = {}
    for hkey_root, subkey in uninstall_roots:
        try:
            with winreg.OpenKey(hkey_root, subkey) as key:
                i = 0
                while True:
                    try:
                        sk_name = winreg.EnumKey(key, i)
                        i += 1
                        with winreg.OpenKey(key, sk_name) as sk:
                            try:
                                display_name = winreg.QueryValueEx(sk, 'DisplayName')[0]
                                install_loc = winreg.QueryValueEx(sk, 'InstallLocation')[0]
                                if display_name and install_loc:
                                    reg_data[display_name.lower()] = install_loc
                            except OSError:
                                pass
                    except OSError:
                        break
        except OSError:
            continue

    for browser_id, info in BROWSER_DEFINITIONS.items():
        if browser_id in installed:
            continue
        for uninst_name in info.get('reg_uninstall_names', []):
            for display_name, install_loc in reg_data.items():
                if uninst_name.lower() in display_name:
                    full = os.path.join(install_loc, info['exe'])
                    if os.path.exists(full):
                        installed[browser_id] = full
                        break
            if browser_id in installed:
                break


def _scan_filesystem(installed):
    def try_find(roots, browser_id, info):
        if browser_id in installed:
            return
        exe = info['exe']
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirname in os.listdir(root):
                full = os.path.join(root, dirname, exe)
                if os.path.isfile(full):
                    installed[browser_id] = full
                    return
                subdirs_try = [dirname]
                try:
                    subdirs_try = os.listdir(os.path.join(root, dirname))
                except OSError:
                    pass
                for sub in subdirs_try:
                    full2 = os.path.join(root, dirname, sub, exe)
                    if os.path.isfile(full2):
                        installed[browser_id] = full2
                        return

    for browser_id, info in BROWSER_DEFINITIONS.items():
        try_find(COMMON_INSTALL_ROOTS, browser_id, info)

    local_appdata = _get_local_appdata_roots()
    for browser_id, info in BROWSER_DEFINITIONS.items():
        try_find(local_appdata, browser_id, info)


def _load_custom_browsers(installed):
    try:
        from core.config_manager import ConfigManager
        raw = ConfigManager.get('custom_browsers', '[]')
        browsers = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ImportError):
        return
    for b in browsers:
        name = b.get('name', '')
        path = b.get('path', '')
        if name and path and os.path.isfile(path):
            custom_id = f'__custom__{name}'
            installed[custom_id] = path