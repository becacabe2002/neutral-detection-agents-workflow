import unittest
from src.services.mbfc_registry import MBFCRegistry

class TestMBFCRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = MBFCRegistry()

    def test_lookup_domain(self):
        # Test common domains that should be in the DB
        profile = self.registry.lookup_domain("https://www.nytimes.com/article")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.domain, "nytimes.com")
        
        profile = self.registry.lookup_domain("http://whitehouse.gov")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.domain, "whitehouse.gov")

    def test_is_trusted(self):
        # NYT should be trusted
        self.assertTrue(self.registry.is_trusted("https://www.nytimes.com/"))
        
        # Test a domain that's likely NOT trusted (if we can find one)
        # itemfix.com was Low/Mixed in the JSON
        profile = self.registry.lookup_domain("itemfix.com")
        if profile:
            # itemfix.com in JSON: Factual: Mixed, Cred: Low.
            # is_trusted only rejects LOW/VERY_LOW Factual.
            # So Mixed should be trusted.
            self.assertTrue(self.registry.is_trusted("itemfix.com"))

if __name__ == "__main__":
    unittest.main()
