"""Behavioral fixtures for portable artifact validation."""
import tempfile
from pathlib import Path
import unittest
import zipfile

from verify_walkthrough import verify


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'report'
        self.root.mkdir()
        (self.root / 'image.png').write_bytes(b'fixture')
        (self.root / 'index.html').write_text('<img src="image.png">')

    def test_portable_and_zip_parity(self):
        archive = self.root.parent / 'report.zip'
        with zipfile.ZipFile(archive, 'w') as bundle:
            for p in self.root.iterdir():
                bundle.write(p, 'report/' + p.name)
        self.assertEqual(verify(self.root, 'index.html', archive), [])
        (self.root / 'image.png').write_bytes(b'changed')
        self.assertTrue(verify(self.root, 'index.html', archive))

    def test_missing_remote_and_escaped_dependencies(self):
        for url in ('missing.png', 'https://example.test/a.png', '/image.png', '%2e%2e/out.png'):
            with self.subTest(url=url):
                (self.root / 'index.html').write_text(f'<img src="{url}">')
                self.assertTrue(verify(self.root, 'index.html'))

    def test_rejects_symlinks_and_outside_entry(self):
        (self.root / 'link.png').symlink_to(self.root / 'image.png')
        self.assertTrue(verify(self.root, 'index.html'))
        self.assertTrue(verify(self.root, '../other.html'))

    def test_credentials_are_reported_without_values(self):
        secret = 'PRIVATE-CAPABILITY-VALUE'
        (self.root / 'notes.txt').write_text('https://example.test/reset?token=' + secret)
        errors = verify(self.root, 'index.html')
        self.assertTrue(errors)
        self.assertNotIn(secret, str(errors))

    def test_extra_archive_member_is_rejected(self):
        archive = self.root.parent / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('../outside.txt', 'unexpected')
        self.assertTrue(verify(self.root, 'index.html', archive))


if __name__ == '__main__':
    unittest.main()
