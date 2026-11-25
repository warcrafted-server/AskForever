import hashlib

from askforever.app import selfupdate


def _release(tag, *, draft=False, assets=True):
    version = tag[1:]
    name = f'AskForever-Setup-{version}.exe'
    files = ([{'name': name, 'browser_download_url': f'https://example/{name}'},
              {'name': name + '.sha256',
               'browser_download_url': f'https://example/{name}.sha256'}]
             if assets else [])
    return {'tag_name': tag, 'draft': draft, 'assets': files}


def _linux_release(tag, *, draft=False, assets=True, html_url=None):
    version = tag[1:]
    name = f'askforever-{version}-linux-x86_64.tar.gz'
    files = ([{'name': name, 'browser_download_url': f'https://example/{name}'}]
             if assets else [])
    release = {'tag_name': tag, 'draft': draft, 'assets': files}
    if html_url is not None:
        release['html_url'] = html_url
    return release


def test_parse_version_orders_beta_before_final_and_rejects_invalid():
    assert selfupdate.parse_version('v0.4.0-beta.1') < selfupdate.parse_version('0.4.0-beta.2')
    assert selfupdate.parse_version('0.4.0b1') == selfupdate.parse_version('v0.4.0-beta.1')
    assert selfupdate.parse_version('0.4.0-beta.2') < selfupdate.parse_version('0.4.0')
    assert selfupdate.parse_version('not-a-version') is None
    assert selfupdate.parse_version('0.4') is None


def test_latest_app_release_filters_drafts_tags_and_missing_assets(monkeypatch):
    monkeypatch.setenv('ASKFOREVER_RELEASES_URL', 'https://example/releases')
    releases = [
        _release('v9.0.0', draft=True),
        _release('0.9.0'),
        _release('v0.8.0', assets=False),
        _release('v0.4.0'),
        _release('v0.4.0-beta.1'),
    ]
    called = []

    def fetch(url):
        called.append(url)
        return releases

    result = selfupdate.latest_app_release(fetch, platform='win32')
    assert called == ['https://example/releases']
    assert result == {
        'version': '0.4.0',
        'tag': 'v0.4.0',
        'installer_url': 'https://example/AskForever-Setup-0.4.0.exe',
        'sha256_url': 'https://example/AskForever-Setup-0.4.0.exe.sha256',
    }


def test_latest_app_release_on_linux_requires_the_tarball_and_returns_the_page(
        monkeypatch):
    monkeypatch.setenv('ASKFOREVER_RELEASES_URL', 'https://example/releases')
    releases = [
        _linux_release('v9.0.0', draft=True),
        _linux_release('0.9.0'),
        _linux_release('v0.8.0', assets=False),
        _linux_release('v0.5.0', html_url='https://github.com/warcrafted-server/'
                                          'AskForever/releases/tag/v0.5.0'),
        _linux_release('v0.4.0', html_url='http://insecure.example/release'),
    ]

    result = selfupdate.latest_app_release(lambda url: releases, platform='linux')

    assert result == {
        'version': '0.5.0',
        'tag': 'v0.5.0',
        'page_url': 'https://github.com/warcrafted-server/AskForever/releases/tag/v0.5.0',
    }


def test_latest_app_release_on_linux_ignores_release_without_the_tarball(monkeypatch):
    releases = [
        _release('v0.4.0'),
        _linux_release('v0.3.0', assets=False),
    ]

    assert selfupdate.latest_app_release(lambda url: releases, platform='linux') is None


def test_check_only_returns_newer_valid_version(monkeypatch):
    monkeypatch.setattr(selfupdate, 'latest_app_release', lambda: {
        'version': '0.3.0-beta.5', 'tag': 'v0.3.0-beta.5',
        'installer_url': 'url', 'sha256_url': 'sha',
    })
    assert selfupdate.check('0.3.0b4')['tag'] == 'v0.3.0-beta.5'
    assert selfupdate.check('0.3.0') is None


def test_download_installer_verifies_checksum_and_removes_old_installers(tmp_path):
    content = b'new installer'
    digest = hashlib.sha256(content).hexdigest()
    release = {
        'tag': 'v0.4.0-beta.1',
        'installer_url': 'installer',
        'sha256_url': 'checksum',
    }
    old_installer = tmp_path / 'AskForever-Setup-0.3.0.exe'
    old_installer.write_bytes(b'old')
    payloads = {'installer': content, 'checksum': f'{digest}  installer.exe\n'}

    def download(url, target):
        payload = payloads[url]
        if isinstance(payload, bytes):
            target.write_bytes(payload)
        else:
            target.write_text(payload, encoding='utf-8')

    result = selfupdate.download_installer(release, tmp_path, download)
    assert result.name == 'AskForever-Setup-0.4.0-beta.1.exe'
    assert result.read_bytes() == content
    assert not old_installer.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [result.name]


def test_download_installer_deletes_mismatch_and_raises(tmp_path):
    release = {'tag': 'v0.4.0', 'installer_url': 'installer', 'sha256_url': 'checksum'}

    def download(url, target):
        target.write_text('0000' if url == 'checksum' else 'bad installer', encoding='utf-8')

    try:
        selfupdate.download_installer(release, tmp_path, download)
    except selfupdate.SelfUpdateError as error:
        assert 'mismatch' in str(error)
    else:
        raise AssertionError('checksum mismatch was accepted')
    assert list(tmp_path.iterdir()) == []


def test_apply_uses_detached_relaunch_arguments(tmp_path):
    calls = []

    def popen(command, **kwargs):
        calls.append((command, kwargs))

    selfupdate.apply(tmp_path / 'installer.exe', popen=popen)
    command, kwargs = calls[0]
    assert command == [str(tmp_path / 'installer.exe'), '/VERYSILENT',
                       '/SUPPRESSMSGBOXES', '/NORESTART', '/RELAUNCH']
    assert kwargs == {'creationflags': 0x8 | 0x200}


def test_updater_waits_for_active_answer_then_installs_and_exits(monkeypatch, tmp_path):
    monkeypatch.setattr(selfupdate.sys, 'frozen', True, raising=False)
    release = {'version': '0.4.0', 'tag': 'v0.4.0'}
    busy_states = iter([True, True, False, False])
    sleeps = []
    applied = []
    exited = []
    holder = {}

    def sleep(seconds):
        sleeps.append(seconds)
        if seconds == 60:
            holder['updater'].stop()

    updater = selfupdate.Updater(
        exit_app=lambda: exited.append(True), is_busy=lambda: next(busy_states),
        first_delay=0, interval=60, check_func=lambda: release,
        download_func=lambda item: tmp_path / 'setup.exe',
        apply_func=lambda path: applied.append(path), sleep=sleep, platform='win32')
    holder['updater'] = updater
    updater.start()
    updater._thread.join(timeout=2)

    assert sleeps == [0, 2, 2, 60]
    assert applied == [tmp_path / 'setup.exe']
    assert exited == [True]


def test_updater_on_linux_announces_once_and_never_downloads(monkeypatch):
    monkeypatch.setattr(selfupdate.sys, 'frozen', True, raising=False)
    statuses = []
    events = []
    monkeypatch.setattr(selfupdate, 'set_status', lambda *a, **k: statuses.append((a, k)))
    monkeypatch.setattr(selfupdate, 'emit', lambda *a, **k: events.append((a, k)))
    release = {
        'version': '0.4.0',
        'tag': 'v0.4.0',
        'page_url': 'https://github.com/warcrafted-server/AskForever/releases/tag/v0.4.0',
    }
    downloaded = []
    applied = []
    exited = []
    holder = {}
    intervals = []

    def sleep(seconds):
        if seconds == 60:
            intervals.append(seconds)
            if len(intervals) == 2:
                holder['updater'].stop()

    updater = selfupdate.Updater(
        exit_app=lambda: exited.append(True), is_busy=lambda: False,
        first_delay=0, interval=60, check_func=lambda: release,
        download_func=lambda item: downloaded.append(item),
        apply_func=lambda path: applied.append(path), sleep=sleep,
        platform='linux')
    holder['updater'] = updater
    updater.start()
    updater._thread.join(timeout=2)

    updates = [call for call in events if call[0][0] == 'update']
    assert len(updates) == 1
    spanish, english = updates[0][0][1], updates[0][0][2]
    for message in (spanish, english):
        assert '0.4.0' in message
        assert release['page_url'] in message
        assert 'install.sh' in message
    assert statuses[-1][1]['ok'] is None
    assert '0.4.0' in statuses[-1][0][1]
    assert downloaded == []
    assert applied == []
    assert exited == []


def test_updater_reports_up_to_date_and_errors(monkeypatch):
    monkeypatch.setattr(selfupdate.sys, 'frozen', True, raising=False)
    statuses = []
    events = []
    monkeypatch.setattr(selfupdate, 'set_status', lambda *a, **k: statuses.append((a, k)))
    monkeypatch.setattr(selfupdate, 'emit', lambda *a, **k: events.append((a, k)))
    holder = {}

    def stop_after_interval(seconds):
        if seconds == 60:
            holder['updater'].stop()

    updater = selfupdate.Updater(
        exit_app=lambda: None, is_busy=lambda: False, first_delay=0, interval=60,
        check_func=lambda: None, sleep=stop_after_interval, platform='win32')
    holder['updater'] = updater
    updater.start()
    updater._thread.join(timeout=2)
    assert statuses[-1][0][2].endswith('up to date')

    holder.clear()
    events.clear()

    def failing_check():
        raise RuntimeError('network failure')

    updater = selfupdate.Updater(
        exit_app=lambda: None, is_busy=lambda: False, first_delay=0, interval=60,
        check_func=failing_check, sleep=stop_after_interval, platform='win32')
    holder['updater'] = updater
    updater.start()
    updater._thread.join(timeout=2)
    assert events[-1][0][0] == 'error'
    assert 'network failure' in events[-1][1]['detail']


def test_updater_disabled_in_development_and_no_update_override(monkeypatch):
    statuses = []
    monkeypatch.setattr(selfupdate.sys, 'frozen', False, raising=False)
    monkeypatch.delenv('ASKFOREVER_SELF_UPDATE', raising=False)
    monkeypatch.delenv('ASKFOREVER_NO_SELF_UPDATE', raising=False)
    monkeypatch.setattr(selfupdate, 'set_status', lambda *a, **k: statuses.append(a))
    updater = selfupdate.Updater(exit_app=lambda: None, is_busy=lambda: False)
    updater.start()
    assert updater._thread is None
    assert 'desactivadas' in statuses[-1][1]

    monkeypatch.setenv('ASKFOREVER_SELF_UPDATE', '1')
    assert selfupdate.Updater._enabled()
    monkeypatch.setenv('ASKFOREVER_NO_SELF_UPDATE', '1')
    assert not selfupdate.Updater._enabled()
    updater.start()
    assert updater._thread is None
