"""Run with:  python3 -m unittest discover playground/price-drop-alert/tests"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import price_tracker as pt  # noqa: E402


class ParsePrice(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(pt.parse_price("₹1,299"), 1299)
        self.assertEqual(pt.parse_price("Rs. 2,49,999.50"), 249999.5)
        self.assertEqual(pt.parse_price("$19.99"), 19.99)
        self.assertEqual(pt.parse_price(799), 799)
        self.assertIsNone(pt.parse_price("Out of stock"))
        self.assertIsNone(pt.parse_price(None))


class ExtractPrice(unittest.TestCase):
    def test_jsonld_nested_offers(self):
        data = {"@graph": [{"@type": "Product", "offers": [{"price": "1,499"}, {"price": "1399"}]}]}
        page = f'<script type="application/ld+json">{json.dumps(data)}</script>'
        self.assertEqual(pt.extract_price(page), (1399, "json-ld"))

    def test_bad_jsonld_falls_through_to_meta(self):
        page = ('<script type="application/ld+json">{oops</script>'
                '<meta property="product:price:amount" content="999.00">')
        self.assertEqual(pt.extract_price(page), (999, "meta tag"))

    def test_itemprop(self):
        self.assertEqual(pt.extract_price('<span itemprop="price" content="450">₹450</span>')[0], 450)

    def test_amazon_and_myntra_patterns(self):
        self.assertEqual(pt.extract_price('<span class="a-price-whole">3,199<span>')[0], 3199)
        self.assertEqual(pt.extract_price('window.__myx = {"price":{"mrp":2999,"discounted":1499}}')[0], 1499)

    def test_custom_pattern_wins(self):
        page = '<meta property="product:price:amount" content="999"><b id="deal">Deal ₹777</b>'
        self.assertEqual(pt.extract_price(page, r'id="deal">Deal ₹([\d,]+)'), (777, "custom pattern"))

    def test_not_found(self):
        self.assertEqual(pt.extract_price("<html>no price here</html>"), (None, None))


class DecideAlert(unittest.TestCase):
    def test_any_drop(self):
        self.assertIsNone(pt.decide_alert({"last_price": None}, 100))
        self.assertIsNone(pt.decide_alert({"last_price": 100}, 100))
        self.assertIsNone(pt.decide_alert({"last_price": 100}, 120))
        self.assertEqual(pt.decide_alert({"last_price": 100}, 90), "price dropped")

    def test_target(self):
        item = {"target_price": 500, "last_price": 700}
        self.assertIsNone(pt.decide_alert(item, 600))            # dropped, but above target
        self.assertIsNotNone(pt.decide_alert(item, 500))         # crossed target
        item["last_price"] = 480
        self.assertIsNone(pt.decide_alert(item, 480))            # no repeat ping at same price
        self.assertIsNotNone(pt.decide_alert(item, 450))         # fell further


class CheckAll(unittest.TestCase):
    def test_flow_updates_history_and_notifies(self):
        pages = iter(['<meta property="og:price:amount" content="{}">'.format(p) for p in (1000, 800)])
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.json")
            pt.save_watchlist(path, {"items": [{"id": 1, "name": "Shoe", "url": "http://x",
                                                "target_price": None, "last_price": None, "history": []}]})
            with mock.patch.object(pt, "NOTIFIERS", []), redirect_stdout(io.StringIO()):
                self.assertEqual(pt.check_all(path, fetcher=lambda url: next(pages)), [])
                alerts = pt.check_all(path, fetcher=lambda url: next(pages))
            self.assertEqual(len(alerts), 1)
            item = pt.load_watchlist(path)["items"][0]
            self.assertEqual([h["price"] for h in item["history"]], [1000, 800])
            self.assertEqual(item["lowest_price"], 800)

    def test_fetch_error_is_recorded_not_raised(self):
        def boom(url):
            raise OSError("network down")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.json")
            pt.save_watchlist(path, {"items": [{"id": 1, "name": "X", "url": "http://x", "history": []}]})
            with redirect_stdout(io.StringIO()):
                pt.check_all(path, fetcher=boom)
            self.assertEqual(pt.load_watchlist(path)["items"][0]["last_error"], "network down")


class Notify(unittest.TestCase):
    def test_broken_channel_does_not_stop_others(self):
        def broken(*a):
            raise RuntimeError("nope")
        with mock.patch.object(pt, "NOTIFIERS", [broken, lambda *a: "ok"]), redirect_stdout(io.StringIO()):
            self.assertEqual(pt.notify("t", "m"), ["ok"])


if __name__ == "__main__":
    unittest.main()
