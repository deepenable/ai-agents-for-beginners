"""Regression cases for the supplier checker, not official platform tests."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from check_lab_delivery import (
    heading_anchors,
    inspect_course,
    links,
    local_target,
    manifest_files,
    unique_object,
    valid_path,
    without_fences,
    without_inline_code,
)


def manifest():
    return {
        "schemaVersion": 1,
        "courseId": "sample",
        "title": {"zh-CN": "Sample"},
        "summary": {"zh-CN": "Sample summary"},
        "defaultLocale": "zh-CN",
        "labs": [{
            "id": "lesson-00",
            "title": {"zh-CN": "Lab"},
            "requires": [],
            "chapters": [{
                "id": "first",
                "title": {"zh-CN": "Chapter"},
                "files": {"zh-CN": "chapter.md"},
            }],
        }],
        "assets": [],
    }


class ManifestTests(unittest.TestCase):
    def test_minimum_manifest(self):
        self.assertEqual(manifest_files(manifest()), (["course.json", "chapter.md"], []))

    def test_unknown_metadata_and_boolean_schema_are_rejected(self):
        for field, value in (("schemaVersion", True), ("deliveryCommit", "abc")):
            with self.subTest(field=field):
                sample = manifest()
                sample[field] = value
                self.assertTrue(manifest_files(sample)[1])

    def test_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            json.loads('{"id":"first","id":"second"}', object_pairs_hook=unique_object)

    def test_global_ids_and_paths(self):
        sample = manifest()
        second = copy.deepcopy(sample["labs"][0])
        second["id"] = "lesson-01"
        second["chapters"][0]["files"]["zh-CN"] = "CHAPTER.md"
        sample["labs"].append(second)
        errors = manifest_files(sample)[1]
        self.assertTrue(any("globally duplicate" in item for item in errors))
        self.assertTrue(any("case-colliding" in item for item in errors))

    def test_paths_are_ascii_and_windows_safe(self):
        for path in ("../x.md", "a/./x.md", "a\\x.md", "/x.md", "CON.md",
                     "nul/x.md", "a./x.md", "a/%20.md", "a/lesson one.md", "\u8bfe.md"):
            with self.subTest(path=path):
                self.assertFalse(valid_path(path))
        self.assertTrue(valid_path("chapters/00-setup.zh-CN.md"))

    def test_requires_and_duration(self):
        sample = manifest()
        sample["labs"][0]["requires"] = ["azure-account"]
        sample["labs"][0]["durationMinutes"] = True
        self.assertEqual(len(manifest_files(sample)[1]), 2)

    def test_file_limit_and_file_directory_collision(self):
        sample = manifest()
        sample["assets"] = ["chapter.md/image.png"] + [
            f"image-{number}.png" for number in range(200)
        ]
        errors = manifest_files(sample)[1]
        self.assertTrue(any("collision" in item for item in errors))
        self.assertTrue(any("exceeds 200" in item for item in errors))


class MarkdownTests(unittest.TestCase):
    def test_fenced_and_inline_html_are_examples(self):
        text = "# One\n```html\n<h1>Two</h1>\n```\nUse `<b>` inline.\n"
        plain = without_inline_code(without_fences(text))
        self.assertNotIn("<h1>", plain)
        self.assertNotIn("<b>", plain)
        self.assertEqual(len(heading_anchors(plain)[0]), 1)

    def test_unclosed_fence(self):
        with self.assertRaises(ValueError):
            without_fences("# One\n```python\nprint(1)")

    def test_heading_duplicates_and_unicode(self):
        _, anchors = heading_anchors("# \u73af\u5883\u51c6\u5907\n## Run\n## Run\n## Run-1\n")
        self.assertEqual(anchors, {"\u73af\u5883\u51c6\u5907", "run", "run-1", "run-1-1"})

    def test_inline_reference_and_nested_image_links(self):
        result = list(links(
            "[doc](next.md#run)\n![image](assets/a.png)\n"
            "[reference][ref]\n[ref]: next.md\n"
            "[![thumb](assets/a.png)](https://example.org/video)\n"
        ))
        self.assertIn((False, "next.md#run"), result)
        self.assertIn((True, "assets/a.png"), result)
        self.assertIn((False, "next.md"), result)

    def test_local_links_cannot_escape(self):
        self.assertEqual(local_target("chapters/a.md", "../assets/a.png"), ("assets/a.png", ""))
        self.assertEqual(local_target("chapters/a.md", "#run"), ("chapters/a.md", "run"))
        for destination in ("../../outside.md", "../a.md?x=1", "/outside.md", "..\\outside.md"):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                local_target("chapters/a.md", destination)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sample = manifest()
        self.write_manifest()
        (self.root / "chapter.md").write_text("# One\n\n## Run\n\nDo it.\n", encoding="utf-8")

    def write_manifest(self):
        (self.root / "course.json").write_text(json.dumps(self.sample), encoding="utf-8")

    def inspect(self):
        return inspect_course(self.root, check_sources=False)

    def test_real_package_totals(self):
        result = self.inspect()
        self.assertTrue(result["supplierChecksPassed"])
        self.assertEqual(result["officialValidation"], "not-run")
        self.assertEqual(result["declaredFiles"], 2)
        self.assertEqual(result["declaredBytes"], sum(path.stat().st_size for path in self.root.iterdir()))

    def test_html_broken_anchor_and_remote_image(self):
        (self.root / "chapter.md").write_text(
            "# One\n\n<div>bad</div>\n[bad](#missing)\n![bad](https://example.org/a.png)\n",
            encoding="utf-8",
        )
        result = self.inspect()
        self.assertFalse(result["supplierChecksPassed"])
        for message in ("raw HTML", "nonexistent heading", "remote image"):
            self.assertTrue(any(message in error for error in result["errors"]))

    def test_real_image_signature_and_decode(self):
        self.sample["assets"] = ["figure.png"]
        self.write_manifest()
        Image.new("RGB", (3, 3), "white").save(self.root / "figure.png", format="PNG")
        (self.root / "chapter.md").write_text("# One\n\n![Figure](figure.png)\n", encoding="utf-8")
        self.assertTrue(self.inspect()["supplierChecksPassed"])
        Image.new("RGB", (3, 3), "white").save(self.root / "figure.png", format="JPEG")
        self.assertTrue(any("signature" in error for error in self.inspect()["errors"]))

    def test_wrong_case_and_undeclared_files(self):
        self.sample["labs"][0]["chapters"][0]["files"]["zh-CN"] = "Chapter.md"
        self.write_manifest()
        result = self.inspect()
        self.assertFalse(result["supplierChecksPassed"])
        self.assertTrue(any("wrong case" in error for error in result["errors"]))

    def test_hardlinks_rejected(self):
        os.link(self.root / "chapter.md", self.root / "copy.md")
        result = self.inspect()
        self.assertTrue(any("hard-linked" in error for error in result["errors"]))

    def test_credentials_in_links_rejected(self):
        (self.root / "chapter.md").write_text(
            "# One\n[bad](https://user:password@example.org/x)\n"
            "[bad](https://example.org/x?api_key=example)\n",
            encoding="utf-8",
        )
        result = self.inspect()
        self.assertEqual(len(result["errors"]), 2)

    def test_bare_http_rejected_but_code_example_allowed(self):
        (self.root / "chapter.md").write_text(
            "# One\nhttp://example.org/plain\n\n`http://localhost:8000`\n",
            encoding="utf-8",
        )
        errors = self.inspect()["errors"]
        self.assertEqual(len(errors), 1)
        self.assertIn("unsafe external URL", errors[0])


if __name__ == "__main__":
    unittest.main()
