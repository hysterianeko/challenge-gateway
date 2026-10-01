import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from detector import detect
from solvers.click import _grid_size, _split_grid
from solvers.labels import is_click_question, parse_question


class FakeImage:
    def __init__(self, width, height):
        self.size = (width, height)
        self.crops = []

    def crop(self, box):
        self.crops.append(box)
        w = box[2] - box[0]
        h = box[3] - box[1]
        return FakeImage(w, h)


class QuestionParseTest(unittest.TestCase):
    def test_chinese_traffic_light(self):
        parsed = parse_question("请选出所有红绿灯")
        self.assertEqual(parsed["names"], ["traffic light"])
        self.assertEqual(parsed["indexes"], [9])
        self.assertTrue(is_click_question("请选出所有红绿灯"))

    def test_aws_grid_bus(self):
        parsed = parse_question("aws:grid:bus")
        self.assertEqual(parsed["names"], ["bus"])

    def test_vehicle_maps_multiple(self):
        parsed = parse_question("Select all images with vehicles")
        self.assertEqual(parsed["names"], ["car", "truck", "bus"])

    def test_unsupported_stairs(self):
        parsed = parse_question("选出所有楼梯")
        self.assertEqual(parsed["names"], [])
        self.assertEqual(parsed["unsupported"], "楼梯")


class DetectorClickTest(unittest.TestCase):
    def test_aws_with_images_uses_click(self):
        result = detect({
            "html": "captcha.awswaf.com",
            "question": "选出所有汽车",
            "images": ["aaa"],
        })
        self.assertEqual(result["primary"]["type"], "aws_waf")
        self.assertEqual(result["primary"]["solver"], "click")
        self.assertTrue(result["primary"]["solvable"])

    def test_explicit_classification(self):
        result = detect({
            "type": "AwsWafClassification",
            "question": "bus",
            "queries": ["aaa", "bbb"],
        })
        self.assertEqual(result["primary"]["type"], "aws_classification")
        self.assertEqual(result["primary"]["solver"], "click")

    def test_hcaptcha_images_solvable(self):
        result = detect({
            "html": '<div class="h-captcha" data-sitekey="10000000-ffff-ffff-ffff-000000000001"></div><script src="https://js.hcaptcha.com/1/api.js"></script>',
            "images": ["aaa"],
            "question": "car",
        })
        self.assertEqual(result["primary"]["solver"], "click")
        self.assertTrue(result["primary"]["solvable"])

    def test_plain_ocr_image_stays_ocr(self):
        result = detect({"image": "aaa"})
        self.assertEqual(result["primary"]["type"], "image_to_text")
        self.assertEqual(result["primary"]["solver"], "ocr")


class GridSplitTest(unittest.TestCase):
    def test_grid_size_from_count(self):
        self.assertEqual(_grid_size({}, 9), (3, 3))
        self.assertEqual(_grid_size({"rows": 2, "columns": 4}, 8), (2, 4))

    def test_split_3x3(self):
        image = FakeImage(90, 90)
        tiles = _split_grid(image, 3, 3)
        self.assertEqual(len(tiles), 9)
        self.assertEqual(tiles[0].size, (30, 30))
        self.assertEqual(image.crops[0], (0, 0, 30, 30))
        self.assertEqual(image.crops[-1], (60, 60, 90, 90))


if __name__ == "__main__":
    unittest.main()
