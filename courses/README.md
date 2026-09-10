# Lab course delivery

The Simplified Chinese delivery adapts **all 19 source modules (00–18)** for the lab platform's *实验手册交付规范 v1*. Original lessons, notebooks, examples, and translations remain independently usable.

| Item | Location |
| --- | --- |
| Importable course root | `courses/ai-agents-for-beginners` |
| Manifest | [course.json](ai-agents-for-beginners/course.json) |
| Learner entry | [学习路线](ai-agents-for-beginners/chapters/00-overview.zh-CN.md) |
| Supplier handoff and acceptance status | [交付说明](ai-agents-for-beginners-delivery.zh-CN.md) |

Only the manifest and its declared Markdown/images belong to the importable root. Handoff records and the supplier's generated report are intentionally outside it. The course delivers `zh-CN` only and requests no platform-distributed credentials or Copilot invitations. Learners supply their own approved development resources; cloud calls can incur charges.

## Local supplier checks

From the repository root, using Python with Pillow (already listed in `requirements.txt`):

```powershell
python -m unittest discover -s scripts -p test_check_lab_delivery.py
python .\scripts\check_lab_delivery.py .\courses\ai-agents-for-beginners --report .\courses\ai-agents-for-beginners-supplier-check.json
```

These checks cover this package's schema fields, declared paths/files, conservative Markdown rules, local links/anchors, image signatures/decoding, size limits, source-file pins, and 00–18 coverage. They do not execute lessons or verify external link availability and are **not the official platform validator**. The generated `supplierChecksPassed` field must not be presented as publication approval.

The recipient must supply the complete v1 platform validation project and run its documented validation, page preview, and teaching rehearsal on the final committed snapshot. Select an actual commit containing this package for publication; the source baseline is not a publishing snapshot, and opening a PR is not publication approval.

## Maintaining the delivery

Edit the Chinese chapters directly; they are reviewed adaptations, not regenerated translations. Keep stable course/lab/chapter IDs. When adding an image, copy an authorized ordinary binary file under `assets`, register it in `course.json`, record its provenance in the handoff, and rerun the supplier checks. Do not use filesystem links, Git LFS, remote images, or account screenshots.

When updating the source baseline, reconcile each chapter against the changed code before updating pinned URLs and `SOURCE_SHA` in `scripts/check_lab_delivery.py`. Use the generated coverage and file hashes to review changes. Never replace source pins with an invented SHA or treat the baseline SHA as the future delivery commit.
