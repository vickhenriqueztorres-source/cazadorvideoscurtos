import copy
import json
from pathlib import Path
import queue
import tempfile
import time
import unittest
from unittest.mock import patch

from core import RESOURCE_DIR, Session, chrome_options, read_config


class ConfigurationTests(unittest.TestCase):
    def test_invalid_configuration_is_rejected(self):
        base = read_config(RESOURCE_DIR / 'config.json')
        variants = []
        for selector in ('*', 'body', 'button', '.profit, button', '[class*="unknown"]', '.profit {display:none}'):
            config = copy.deepcopy(base)
            config['platforms'][0]['targets']['profit'] = [selector]
            variants.append(config)
        config = copy.deepcopy(base)
        config['themes'][0]['colors']['profit'] = '#fff; display: none'
        variants.append(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            for config in variants:
                path.write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaises(ValueError):
                    read_config(path)


class LiveIQOptionTests(unittest.TestCase):
    def test_real_iqoption_load_and_diagnostics(self):
        config = read_config(RESOURCE_DIR / 'config.json')
        snapshot = None
        errors = []
        with tempfile.TemporaryDirectory() as directory:
            with patch('core.DATA_DIR', Path(directory)), patch('core.chrome_options', side_effect=lambda profile: chrome_options(profile, headless=True)):
                session = Session(config, {})
                try:
                    session.command('start')
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        try:
                            kind, value = session.events.get(timeout=1)
                        except queue.Empty:
                            continue
                        if kind == 'error':
                            errors.append(value)
                            break
                        if kind == 'diagnostics' and value.get('readyState') == 'complete':
                            snapshot = value
                            if value.get('platformSurfaceDetected') or '/login' in value.get('url', ''):
                                break
                    self.assertEqual(errors, [])
                    self.assertIsNotNone(snapshot, 'A IQ Option não entregou um documento completo em 60 s.')
                    self.assertTrue(snapshot['url'].startswith('https://iqoption.com/'))
                    self.assertGreater(snapshot['domElements'], 0)
                    self.assertIn(snapshot['renderMode'], ('dom', 'canvas', 'webgl'))
                    self.assertTrue(all(isinstance(w, str) for w in snapshot['warnings']))
                    if snapshot['canvasElements']:
                        self.assertTrue(snapshot['canvasFilterApplied'])
                        self.assertEqual(snapshot['status'], 'active')
                    print('DIAGNÓSTICO IQ OPTION:', json.dumps(snapshot, ensure_ascii=False), flush=True)
                finally:
                    session.command('close')
                    session.thread.join(15)


if __name__ == '__main__':
    unittest.main(verbosity=2)
