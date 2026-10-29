#!/usr/bin/env python3
"""Format original English seed text with verified local image links.

No translation, model inference, annotation, or source dataset mutation occurs.
Only explicit numbered image placeholders in source text are replaced.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "data/seeds/formal_v3_seed_bank.json"
OUTPUT = ROOT / "data/review/formal_v3_readable_original_en.json"
IMAGE_PLACEHOLDER = re.compile(r"(?P<prefix>\bImage\s*(?P<number>\d+)\s*:\s*)<ImageHere>", re.I)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_images(seed: dict[str, Any], mmdu: dict[Any, Any], mmds: dict[Any, Any]) -> list[dict[str, Any]]:
    dataset = seed["source"]["datasets"][0]
    source_id = seed["source"]["source_ids"][0]
    if dataset == "MMDU":
        members = [value.lstrip("/") for value in mmdu[source_id]["image"]]
        image_folder = ROOT / "data/raw/images/mmdu"
        basis = "Original MMDU image array, numbered from 1."
    else:
        members = []
        for turn in mmds[source_id]["conversations"]:
            if turn.get("role") == "user":
                for image in turn.get("image") or []:
                    if image not in members:
                        members.append(image)
        image_folder = ROOT / "data/raw/images/mmds"
        basis = "First appearance of distinct images in original MMDS user turns."
    selected = {image for packet in seed["evidence_packets"] for image in packet["images"]}
    result = []
    for index, member in enumerate(members, start=1):
        local = image_folder / Path(member).name
        if not local.is_file():
            raise FileNotFoundError(f"Source image missing: {seed['seed_id']} image {index}")
        relative = local.relative_to(ROOT).as_posix()
        result.append({
            "source_image_number": index,
            "source_archive_member": member,
            "image_url": local.resolve().as_uri(),
            "project_relative_path": relative,
            "included_in_experiment_evidence": relative in selected,
            "mapping_basis": basis,
        })
    return result


def replace_images(text: str, images: list[dict[str, Any]], counter: list[int]) -> str:
    urls = {image["source_image_number"]: image["image_url"] for image in images}

    def substitute(match: re.Match[str]) -> str:
        number = int(match["number"])
        if number not in urls:
            raise ValueError(f"Original source does not contain image {number}")
        counter[0] += 1
        return match["prefix"] + urls[number]

    linked = IMAGE_PLACEHOLDER.sub(substitute, text)
    if "<ImageHere>" in linked or "<此处为图片>" in linked:
        raise ValueError("Unresolved unnumbered image placeholder; will not guess its target")
    # Prove all source text outside the placeholder spans is unchanged.
    cursor = 0
    expected = []
    for match in IMAGE_PLACEHOLDER.finditer(text):
        expected.append(text[cursor:match.end() - len("<ImageHere>")])
        expected.append(urls[int(match["number"])])
        cursor = match.end()
    expected.append(text[cursor:])
    assert linked == "".join(expected)
    return linked


def link_nested(value: Any, images: list[dict[str, Any]], counter: list[int]) -> Any:
    if isinstance(value, str):
        return replace_images(value, images, counter)
    if isinstance(value, list):
        return [link_nested(item, images, counter) for item in value]
    if isinstance(value, dict):
        return {key: link_nested(item, images, counter) for key, item in value.items()}
    return value


def local_uri_path(uri: str) -> Path:
    parsed = urlparse(uri)
    assert parsed.scheme == "file"
    decoded = unquote(parsed.path)
    if re.match(r"^/[A-Za-z]:/", decoded):
        decoded = decoded[1:]
    return Path(decoded)


def main() -> None:
    guarded = [BANK_PATH, ROOT / "data/processed/formal_v3.jsonl"] + [
        ROOT / f"data/review/formal_v3_seed_review_reviewer_{name}.jsonl" for name in ("a", "b")
    ]
    before = {str(path): checksum(path) for path in guarded}
    bank = read_json(BANK_PATH)
    mmdu = {row["id"]: row for row in read_json(ROOT / "data/raw/mmdu/benchmark.json")}
    mmds = {}
    with (ROOT / "data/raw/mmds/mmds.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                mmds[row["id"]] = row
    counts = [0]
    records = []
    selected_fields = (
        "seed_id", "scene_type", "split", "risk_category", "risk_subcategory", "benign_subcategory",
        "topic", "dialogue_atoms", "dialogue_outline", "final_request", "source",
    )
    for seed in bank["harmful"] + bank["benign"]:
        images = source_images(seed, mmdu, mmds)
        record = {key: copy.deepcopy(seed[key]) for key in selected_fields if key in seed}
        for key in ("topic", "dialogue_atoms", "dialogue_outline", "final_request"):
            if key in record:
                record[key] = link_nested(record[key], images, counts)
        record["source_images"] = images
        record["experiment_evidence_packets"] = [
            {"packet_id": packet["packet_id"], "image_urls": [(ROOT / name).resolve().as_uri() for name in packet["images"]]}
            for packet in seed["evidence_packets"]
        ]
        records.append(record)

    assert len(records) == 144
    assert len({record["seed_id"] for record in records}) == 144
    total_images = sum(len(record["source_images"]) for record in records)
    for record in records:
        for image in record["source_images"]:
            assert local_uri_path(image["image_url"]).is_file()
    output = {
        "dataset": "formal_v3",
        "format": "readable_original_english_with_local_image_links",
        "created_on": "2026-10-29",
        "record_count": len(records),
        "reading_guide": {
            "text": "Original English seed text. Only explicit numbered image placeholders have been replaced with verified local file URLs.",
            "dialogue": "Benign records use dialogue_outline and final_request; risk records use dialogue_atoms. Field names and original labels are preserved.",
            "image_links": "Open file URLs locally. Spaces in paths are URL-encoded. Links depend on the project remaining at its current absolute location.",
            "image_numbering": "source_images follows the original source's image order, not the smaller experiment evidence bundle.",
            "evidence": "included_in_experiment_evidence identifies images retained in the current experiment. Extra source reference images do not modify the experiment dataset.",
            "review": "No translations, generated answers, ratings, or review input fields are included. Source classifications still require human review.",
        },
        "source": {
            "seed_bank": "data/seeds/formal_v3_seed_bank.json",
            "seed_bank_sha256": before[str(BANK_PATH)],
            "image_metadata": ["data/raw/mmdu/benchmark.json", "data/raw/mmds/mmds.jsonl"],
        },
        "checks": {
            "harmful_count": 80, "benign_count": 64,
            "source_image_links": total_images,
            "image_placeholders_replaced": counts[0],
            "unresolved_image_placeholders": 0,
            "image_files_exist": True,
            "source_text_changed_only_at_placeholders": True,
        },
        "records": records,
    }
    serialized = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    assert "<ImageHere>" not in serialized
    assert "<此处为图片>" not in serialized
    OUTPUT.write_text(serialized, encoding="utf-8", newline="\n")
    assert before == {str(path): checksum(path) for path in guarded}
    print(json.dumps({"output": str(OUTPUT), "records": len(records), "image_links": total_images,
                      "replaced_placeholders": counts[0], "unresolved_placeholders": 0,
                      "source_and_reviewer_files_unchanged": True, "bytes": OUTPUT.stat().st_size,
                      "sha256": checksum(OUTPUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
