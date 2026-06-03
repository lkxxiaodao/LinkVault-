import unittest
from infra.encryption import encrypt_data, decrypt_data, MAGIC, VERSION


class TestEncryption(unittest.TestCase):
    def setUp(self):
        self.password = 'test_password_123'
        self.test_data = {
            'bookmarks': [
                {'id': 1, 'title': 'GitHub', 'url': 'https://github.com'},
                {'id': 2, 'title': 'Google', 'url': 'https://google.com'},
            ],
            'folders': [
                {'id': 1, 'name': 'Dev', 'parent_id': None},
            ],
            'version': 1,
        }

    def test_encrypt_decrypt_roundtrip_simple(self):
        data = {'key': 'value', 'number': 42}
        encrypted = encrypt_data(data, self.password)
        decrypted = decrypt_data(encrypted, self.password)
        self.assertEqual(decrypted, data)

    def test_encrypt_decrypt_roundtrip_complex(self):
        encrypted = encrypt_data(self.test_data, self.password)
        decrypted = decrypt_data(encrypted, self.password)
        self.assertEqual(decrypted, self.test_data)

    def test_encrypt_produces_bytes(self):
        encrypted = encrypt_data(self.test_data, self.password)
        self.assertIsInstance(encrypted, bytes)

    def test_encrypt_has_magic_header(self):
        encrypted = encrypt_data(self.test_data, self.password)
        self.assertTrue(encrypted.startswith(MAGIC))

    def test_encrypt_file_format_structure(self):
        encrypted = encrypt_data(self.test_data, self.password)
        self.assertEqual(encrypted[:4], MAGIC)
        self.assertGreater(len(encrypted), 4 + 4 + 12)

    def test_wrong_password_raises(self):
        encrypted = encrypt_data(self.test_data, self.password)
        with self.assertRaises(Exception):
            decrypt_data(encrypted, 'wrong_password')

    def test_invalid_magic_header(self):
        invalid_data = b'XXXX' + b'\x00' * 100
        with self.assertRaises(ValueError) as ctx:
            decrypt_data(invalid_data, self.password)
        self.assertIn('linkvault', str(ctx.exception))

    def test_empty_dict(self):
        data = {}
        encrypted = encrypt_data(data, self.password)
        decrypted = decrypt_data(encrypted, self.password)
        self.assertEqual(decrypted, data)

    def test_unicode_data(self):
        data = {'name': '中文测试', 'url': 'https://例子.com'}
        encrypted = encrypt_data(data, self.password)
        decrypted = decrypt_data(encrypted, self.password)
        self.assertEqual(decrypted, data)

    def test_different_passwords_produce_different_output(self):
        data = {'key': 'value'}
        enc1 = encrypt_data(data, 'password_a')
        enc2 = encrypt_data(data, 'password_b')
        self.assertNotEqual(enc1, enc2)

    def test_same_data_produces_different_ciphertext(self):
        data = {'key': 'value'}
        enc1 = encrypt_data(data, self.password)
        enc2 = encrypt_data(data, self.password)
        self.assertNotEqual(enc1, enc2)

    def test_large_data(self):
        data = {'items': [{'id': i, 'name': f'item_{i}' * 10} for i in range(100)]}
        encrypted = encrypt_data(data, self.password)
        decrypted = decrypt_data(encrypted, self.password)
        self.assertEqual(decrypted, data)

    def test_decrypt_truncated_data_raises(self):
        encrypted = encrypt_data(self.test_data, self.password)
        truncated = encrypted[:len(encrypted) // 2]
        with self.assertRaises(Exception):
            decrypt_data(truncated, self.password)