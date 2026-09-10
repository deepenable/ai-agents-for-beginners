"""Supplier-side checks for this zh-CN delivery, NOT the platform v1 validator.

Uses the standard library and Pillow (already a course dependency). It checks
the constrained Markdown used by this package, not every CommonMark extension.
It never executes notebooks, contacts cloud services, or fetches external URLs.
"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import unicodedata
from urllib.parse import parse_qsl, unquote, urlsplit

from PIL import Image


SOURCE_SHA = "25b7985f3b2dc37a84f4a7387ccd3c9f0e5b1595"
SOURCE_PREFIX = (
    "https://github.com/deepenable/ai-agents-for-beginners/blob/"
    + SOURCE_SHA + "/"
)
REPO = Path(__file__).absolute().parent.parent
ID = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?\Z")
SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)
IMAGE_FORMATS = {
    ".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
    ".webp": "WEBP", ".gif": "GIF",
}
MIB = 1024 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def valid_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 240:
        return False
    return all(
        SEGMENT.fullmatch(part) and not part.endswith(".")
        and not RESERVED.match(part)
        for part in value.split("/")
    )


def manifest_files(manifest):
    """Return declarations and errors without touching the filesystem."""
    errors = []
    files = []

    def fields(value, required, optional, where):
        if not isinstance(value, dict):
            errors.append(f"{where}: expected object")
            return False
        missing = set(required) - value.keys()
        extra = value.keys() - set(required) - set(optional)
        if missing or extra:
            errors.append(f"{where}: missing={sorted(missing)}, extra={sorted(extra)}")
        return not missing

    def localized(value, maximum, where):
        if not isinstance(value, dict) or set(value) != {"zh-CN"}:
            errors.append(f"{where}: this delivery requires only zh-CN")
            return
        text = value["zh-CN"]
        if not isinstance(text, str) or not 1 <= len(text) <= maximum or not text.strip():
            errors.append(f"{where}: invalid text length/content")

    def identifier(value, where):
        if not isinstance(value, str) or not ID.fullmatch(value):
            errors.append(f"{where}: invalid stable ASCII id")

    if not fields(manifest, (
        "schemaVersion", "courseId", "title", "summary", "defaultLocale",
        "labs", "assets",
    ), (), "course"):
        return files, errors
    if type(manifest["schemaVersion"]) is not int or manifest["schemaVersion"] != 1:
        errors.append("schemaVersion: expected integer 1")
    identifier(manifest["courseId"], "courseId")
    if manifest["defaultLocale"] != "zh-CN":
        errors.append("defaultLocale: expected zh-CN")
    localized(manifest["title"], 200, "course.title")
    localized(manifest["summary"], 2000, "course.summary")
    lab_ids, chapter_ids = set(), set()
    labs = manifest["labs"]
    if not isinstance(labs, list) or not labs:
        errors.append("labs: expected nonempty array")
        labs = []
    for lab_index, lab in enumerate(labs):
        where = f"labs[{lab_index}]"
        if not fields(lab, ("id", "title", "chapters"), ("durationMinutes", "requires"), where):
            continue
        identifier(lab["id"], where)
        if isinstance(lab["id"], str):
            if lab["id"] in lab_ids:
                errors.append(f"{where}: duplicate lab id")
            lab_ids.add(lab["id"])
        localized(lab["title"], 200, where + ".title")
        duration = lab.get("durationMinutes")
        if "durationMinutes" in lab and (
            type(duration) is not int or not 1 <= duration <= 10080
        ):
            errors.append(f"{where}: durationMinutes out of range")
        requires = lab.get("requires", [])
        if not isinstance(requires, list) or any(
            item not in ("workshop-credentials", "github-copilot")
            for item in requires
        ):
            errors.append(f"{where}: invalid requires")
        elif len(set(requires)) != len(requires):
            errors.append(f"{where}: duplicate requires")
        chapters = lab["chapters"]
        if not isinstance(chapters, list) or not chapters:
            errors.append(f"{where}: expected nonempty chapters")
            continue
        for chapter in chapters:
            if not fields(chapter, ("id", "title", "files"), (), where + ".chapter"):
                continue
            identifier(chapter["id"], where + ".chapter.id")
            if isinstance(chapter["id"], str):
                if chapter["id"] in chapter_ids:
                    errors.append(f"{where}: globally duplicate chapter id")
                chapter_ids.add(chapter["id"])
            localized(chapter["title"], 200, where + ".chapter.title")
            mapping = chapter["files"]
            if not isinstance(mapping, dict) or set(mapping) != {"zh-CN"}:
                errors.append(f"{where}: chapter files must contain only zh-CN")
                continue
            name = mapping["zh-CN"]
            if not valid_path(name) or not name.endswith(".md"):
                errors.append(f"{where}: invalid chapter path {name!r}")
            else:
                files.append(name)
    assets = manifest["assets"]
    if not isinstance(assets, list):
        errors.append("assets: expected array")
        assets = []
    for name in assets:
        if not valid_path(name) or PurePosixPath(name).suffix not in IMAGE_FORMATS:
            errors.append(f"assets: invalid image path {name!r}")
        else:
            files.append(name)
    files.insert(0, "course.json")
    folded = [name.casefold() for name in files]
    if len(folded) != len(set(folded)):
        errors.append("declarations: duplicate or case-colliding paths")
    for name in folded:
        if any(str(parent) in folded for parent in PurePosixPath(name).parents if str(parent) != "."):
            errors.append(f"declarations: file/directory collision {name}")
    if len(files) > 200:
        errors.append(f"declarations: {len(files)} files exceeds 200")
    return files, errors


def without_fences(text):
    result = []
    marker = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if marker is None and match:
            marker = match[1]
            result.append("")
        elif marker is not None:
            if match and match[1][0] == marker[0] and len(match[1]) >= len(marker) and not match[2].strip():
                marker = None
            result.append("")
        else:
            result.append(line)
    if marker is not None:
        raise ValueError("unclosed code fence")
    return "\n".join(result)


def without_inline_code(text):
    return re.sub(r"(`+)(.+?)\1", lambda m: " " * len(m[0]), text)


def heading_anchors(text):
    used = set()
    anchors = set()
    headings = re.findall(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", text, re.M)
    for _, title in headings:
        title = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", title)
        title = title.replace("`", "").replace("*", "")
        slug = "".join(
            char for char in title.lower()
            if char in ("-", "_", " ") or unicodedata.category(char)[0] in ("L", "N", "M")
        ).replace(" ", "-")
        candidate, suffix = slug, 0
        while candidate in used:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        used.add(candidate)
        anchors.add(candidate)
    return headings, anchors


def links(text):
    """Read inline and reference Markdown links in the package's plain subset."""
    definitions = {
        match[1].strip().casefold(): match[2]
        for match in re.finditer(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)", text, re.M)
    }
    pattern = re.compile(
        r"(!?)\[([^\]\n]*)\](?:\(([^()\s]+)(?:\s+\"[^\"]*\")?\)|\[([^\]\n]*)\])"
    )
    for match in pattern.finditer(text):
        destination = match[3]
        if destination is None:
            label = (match[4] or match[2]).strip().casefold()
            if label not in definitions:
                raise ValueError(f"undefined reference link: {label}")
            destination = definitions[label]
        yield bool(match[1]), destination
    for match in re.finditer(r"<(https://[^>]+)>", text):
        yield False, match[1]
    # Bare URLs also autolink under GFM; reject insecure schemes outside code.
    for match in re.finditer(r"(?<![<(])(?:https?|ftp)://[^\s<>()]+", text):
        yield False, match[0].rstrip(").,;")
    # Shortcut references are supported only when a definition is present.
    for match in re.finditer(r"(!?)\[([^\]\n]+)\](?![\[(\:])", text):
        label = match[2].strip().casefold()
        if label in definitions:
            yield bool(match[1]), definitions[label]


def local_target(document, destination):
    parsed = urlsplit(destination)
    if parsed.query or "\\" in parsed.path or "%" in parsed.path:
        raise ValueError(f"invalid local link: {destination}")
    if parsed.path.startswith("/"):
        raise ValueError(f"absolute local link: {destination}")
    parts = list(PurePosixPath(document).parent.parts)
    if parsed.path:
        for part in parsed.path.split("/"):
            if part == "..":
                if not parts:
                    raise ValueError(f"link escapes course root: {destination}")
                parts.pop()
            elif part not in ("", "."):
                parts.append(part)
        target = "/".join(parts)
    else:
        target = document
    return target, unquote(parsed.fragment)


def filesystem_errors(root, files):
    errors = []
    for ancestor in (root, *root.parents):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            errors.append(f"linked/reparse course ancestor: {ancestor.name}")
    actual = []
    for entry in root.rglob("*"):
        info = entry.lstat()
        name = entry.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            errors.append(f"linked/reparse entry: {name}")
        if not valid_path(name):
            errors.append(f"invalid filesystem path: {name}")
        if entry.is_file():
            actual.append(name)
            if info.st_nlink != 1:
                errors.append(f"hard-linked file: {name}")
        elif not entry.is_dir():
            errors.append(f"not an ordinary file/directory: {name}")
    if len({name.casefold() for name in actual}) != len(actual):
        errors.append("filesystem case collision")
    for name in sorted(set(files) - set(actual)):
        errors.append(f"missing file or wrong case: {name}")
    for name in sorted(set(actual) - set(files)):
        errors.append(f"undeclared file inside course root: {name}")
    return errors


def inspect_course(root, check_sources=True):
    root = root.absolute()
    for ancestor in (root, *root.parents):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"linked/reparse course ancestor: {ancestor.name}")
    manifest_bytes = (root / "course.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=unique_object)
    files, errors = manifest_files(manifest)
    if errors:
        return {"supplierChecksPassed": False, "officialValidation": "not-run", "errors": errors}
    errors.extend(filesystem_errors(root, files))
    if errors:
        return {"supplierChecksPassed": False, "officialValidation": "not-run", "errors": errors}
    assets = set(manifest["assets"])
    documents, anchors, sizes, hashes = {}, {}, {}, {}
    for name in files:
        path = root / name
        data = path.read_bytes()
        sizes[name] = len(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
        if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
            errors.append(f"{name}: Git LFS pointer")
        if name == "course.json":
            limit = 64 * 1024
        elif name.endswith(".md"):
            limit = 256 * 1024
            body = without_fences(data.decode("utf-8"))
            headings, anchors[name] = heading_anchors(body)
            if sum(level == "#" for level, _ in headings) != 1:
                errors.append(f"{name}: expected exactly one H1")
            if any(len(level) > 3 for level, _ in headings):
                errors.append(f"{name}: delivery uses only H1/H2/H3")
            body = without_inline_code(body)
            without_autolinks = re.sub(r"<https://[^>]+>", "", body)
            if re.search(r"<!--|</?[A-Za-z][^>]*>", without_autolinks):
                errors.append(f"{name}: raw HTML outside code")
            if re.search(r"(?im)^#{1,3}\s+(?:目录|table of contents)\s*$", body):
                errors.append(f"{name}: handwritten table of contents")
            documents[name] = body
        else:
            limit = 2 * MIB
            with Image.open(path) as image:
                if image.format != IMAGE_FORMATS[path.suffix]:
                    errors.append(f"{name}: extension and image signature differ")
                image.verify()
            with Image.open(path) as image:
                for frame in range(getattr(image, "n_frames", 1)):
                    image.seek(frame)
                    image.load()
        if len(data) > limit:
            errors.append(f"{name}: {len(data)} bytes exceeds {limit}")
    if sum(sizes.values()) > 25 * MIB:
        errors.append("total declared bytes exceeds 25 MiB")
    used_assets, source_paths, external_links = set(), set(), set()
    for document, body in documents.items():
        for is_image, destination in links(body):
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                    errors.append(f"{document}: unsafe external URL {destination}")
                if any(re.search(r"token|secret|password|api.?key|signature|^sig$|^code$", key, re.I)
                       for key, _ in parse_qsl(parsed.query)):
                    errors.append(f"{document}: secret-shaped query parameter")
                if is_image:
                    errors.append(f"{document}: remote image")
                external_links.add(destination)
                if destination.startswith(SOURCE_PREFIX):
                    source_paths.add(unquote(parsed.path.split("/" + SOURCE_SHA + "/", 1)[1]))
                elif parsed.netloc.lower() == "github.com" and parsed.path.lower().startswith(
                    "/deepenable/ai-agents-for-beginners/"
                ):
                    errors.append(f"{document}: fork source link not pinned to input SHA")
            else:
                target, fragment = local_target(document, destination)
                if target not in files or target == "course.json":
                    errors.append(f"{document}: undeclared link {destination}")
                elif target in assets:
                    used_assets.add(target)
                    if fragment:
                        errors.append(f"{document}: image cannot have anchor")
                elif is_image:
                    errors.append(f"{document}: image points to non-image")
                elif fragment and fragment not in anchors.get(target, set()):
                    errors.append(f"{document}: nonexistent heading anchor {destination}")
    if assets != used_assets:
        errors.append(f"unused declared assets: {sorted(assets - used_assets)}")
    coverage = {}
    if check_sources:
        source_files = set(subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", SOURCE_SHA],
            cwd=REPO, text=True, encoding="utf-8",
        ).splitlines())
        for source in sorted(source_paths - source_files):
            errors.append(f"source URL is not a tracked file at input SHA: {source}")
        modules = sorted({
            name.split("/")[0] for name in source_files
            if re.match(r"^\d{2}-[^/]+/README\.md$", name)
        })
        expected_ids = [f"lesson-{number:02d}" for number in range(19)]
        if [lab["id"] for lab in manifest["labs"]] != expected_ids:
            errors.append("coverage: expected lesson-00 through lesson-18 in order")
        for module in modules:
            linked = sorted(path for path in source_paths if path.startswith(module + "/"))
            notebooks = {path for path in source_files if path.startswith(module + "/") and path.endswith(".ipynb")}
            coverage[module] = {
                "sourceReadmeLinked": module + "/README.md" in source_paths,
                "sourceNotebooks": len(notebooks),
                "linkedNotebooks": len(notebooks & source_paths),
                "unlinkedNotebooks": sorted(notebooks - source_paths),
                "linkedFiles": linked,
            }
            if not coverage[module]["sourceReadmeLinked"]:
                errors.append(f"coverage: missing source README link for {module}")
            if notebooks - source_paths:
                errors.append(f"coverage: unlinked notebook variants in {module}")
        repo_relative = root.relative_to(REPO).as_posix()
        attributes = subprocess.check_output(
            ["git", "check-attr", "filter", "--", *[repo_relative + "/" + name for name in files]],
            cwd=REPO, text=True, encoding="utf-8",
        )
        if re.search(r": filter: lfs$", attributes, re.M):
            errors.append("declared file configured for Git LFS")
        modes = subprocess.check_output(
            ["git", "ls-files", "--stage", "--", repo_relative],
            cwd=REPO, text=True, encoding="utf-8",
        )
        if re.search(r"^160000 ", modes, re.M):
            errors.append("submodule inside course root")
    return {
        "supplierChecksPassed": not errors,
        "officialValidation": "not-run",
        "teachingRehearsal": "pending",
        "scope": "Supplier zh-CN package checks; not a CommonMark or platform conformance guarantee.",
        "courseId": manifest["courseId"],
        "sourceCommit": SOURCE_SHA,
        "labs": len(manifest["labs"]),
        "chapters": len(documents),
        "images": len(assets),
        "declaredFiles": len(files),
        "declaredBytes": sum(sizes.values()),
        "manifestBytes": len(manifest_bytes),
        "maxMarkdownBytes": max((size for name, size in sizes.items() if name.endswith(".md")), default=0),
        "maxImageBytes": max((sizes[name] for name in assets), default=0),
        "externalLinksInspectedOffline": len(external_links),
        "coverage": coverage,
        "files": [{"path": name, "bytes": sizes[name], "sha256": hashes[name]} for name in files],
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course_root", type=Path)
    parser.add_argument("--report", type=Path, help="Write generated supplier report OUTSIDE the course root.")
    args = parser.parse_args()
    if args.report and args.report.absolute().is_relative_to(args.course_root.absolute()):
        parser.error("--report must be outside the course root")
    try:
        report = inspect_course(args.course_root)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        report = {
            "supplierChecksPassed": False,
            "officialValidation": "not-run",
            "errors": [str(error)],
        }
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.write_text(encoded, encoding="utf-8")
    summary = {key: value for key, value in report.items() if key not in ("files", "coverage")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if report["supplierChecksPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
