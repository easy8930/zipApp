from pathlib import Path
import tempfile
import unittest
import zipfile
from archive_core import compress, extract


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_roundtrip(self):
        folder = self.root / '日本語'
        folder.mkdir()
        (folder / '空').mkdir()
        (folder / '文書.txt').write_text('こんにちは', encoding='utf-8')
        (folder / 'binary').write_bytes(bytes(range(256)))
        archive = self.root / 'output.zip'
        compress([folder], archive)
        extract(archive, self.root / 'result')
        self.assertEqual((self.root / 'result/日本語/文書.txt').read_text(encoding='utf-8'), 'こんにちは')
        self.assertEqual((self.root / 'result/日本語/binary').read_bytes(), bytes(range(256)))
        self.assertTrue((self.root / 'result/日本語/空').is_dir())

    def test_unsafe_paths(self):
        for name in ['../escape', '/absolute', 'C:/file', 'a\\..\\escape', 'CON.txt', 'file:stream', 'trail.']:
            with self.subTest(name=name):
                archive = self.root / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr(name, 'bad')
                with self.assertRaises(ValueError):
                    extract(archive, self.root / 'result')
                self.assertFalse((self.root / 'result').exists())

    def test_no_overwrite(self):
        archive = self.root / 'a.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('a', 'data')
        with self.assertRaises(ValueError):
            extract(archive, self.root)

    def test_bad_archive_cleanup(self):
        archive = self.root / 'bad.zip'
        archive.write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile):
            extract(archive, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())

    def test_source_preserved(self):
        source = self.root / 'data'
        source.write_text('original')
        with self.assertRaises(ValueError):
            compress([source], source)
        self.assertEqual(source.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
