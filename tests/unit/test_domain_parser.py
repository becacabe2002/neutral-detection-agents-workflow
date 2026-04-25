import unittest
from src.utils.domain_parser import canonicalize_domain

class TestDomainParser(unittest.TestCase):
    def test_canonicalize_domain(self):
        self.assertEqual(canonicalize_domain("http://www.nytimes.com/path"), "nytimes.com")
        self.assertEqual(canonicalize_domain("https://www.nytimes.com"), "nytimes.com")
        self.assertEqual(canonicalize_domain("www.nytimes.com"), "nytimes.com")
        self.assertEqual(canonicalize_domain("nytimes.com"), "nytimes.com")
        self.assertEqual(canonicalize_domain("http://nytimes.com/"), "nytimes.com")
        self.assertEqual(canonicalize_domain("https://edition.cnn.com/world"), "edition.cnn.com")
        self.assertEqual(canonicalize_domain("http://whitehouse.gov"), "whitehouse.gov")

if __name__ == "__main__":
    unittest.main()
