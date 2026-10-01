import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from detector import detect


class DetectorTest(unittest.TestCase):
    def test_turnstile_sitekey(self):
        result = detect({
            "url": "https://www.nodeseek.com/signIn.html",
            "html": '<div class="cf-turnstile" data-sitekey="0x4AAAAAAAaNy7leGjewpVyR"></div>',
        })
        self.assertEqual(result["primary"]["type"], "turnstile")
        self.assertTrue(result["primary"]["solvable"])
        self.assertEqual(result["primary"]["siteKey"], "0x4AAAAAAAaNy7leGjewpVyR")

    def test_cloudflare_challenge(self):
        result = detect({"html": "<title>Just a moment...</title><script src='/cdn-cgi/challenge-platform/h/b/orchestrate'></script>"})
        self.assertEqual(result["primary"]["type"], "cloudflare_challenge")

    def test_recaptcha_v3(self):
        result = detect({"html": '<script src="https://www.google.com/recaptcha/api.js?render=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></script>'})
        self.assertEqual(result["primary"]["type"], "recaptcha_v3")

    def test_recaptcha_v2(self):
        result = detect({"html": '<div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></div>'})
        self.assertEqual(result["primary"]["type"], "recaptcha_v2")

    def test_hcaptcha(self):
        result = detect({"html": '<div class="h-captcha" data-sitekey="10000000-ffff-ffff-ffff-000000000001"></div><script src="https://js.hcaptcha.com/1/api.js"></script>'})
        self.assertEqual(result["primary"]["type"], "hcaptcha")
        self.assertFalse(result["primary"]["solvable"])

    def test_funcaptcha(self):
        result = detect({"html": '<script src="https://client-api.arkoselabs.com/v2/api.js"></script>'})
        self.assertEqual(result["primary"]["type"], "funcaptcha")

    def test_explicit_type(self):
        result = detect({"type": "AntiTurnstileTaskProxyLess", "websiteKey": "0x4AAAAAAAaNy7leGjewpVyR", "websiteURL": "https://www.nodeseek.com/signIn.html"})
        self.assertEqual(result["primary"]["type"], "turnstile")


if __name__ == "__main__":
    unittest.main()
