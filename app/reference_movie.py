import struct
import logging

logger = logging.getLogger(__name__)


def _find_box(data, box_type, start=0):
    i = start
    while i < len(data) - 8:
        size = struct.unpack(">I", data[i : i + 4])[0]
        if size == 0 or i + size > len(data):
            break
        if data[i + 4 : i + 8] == box_type:
            return i, size
        i += size
    return None, 0


def _set_dref_url(box_data, target_url):
    if len(box_data) < 8:
        return box_data

    size = struct.unpack(">I", box_data[0:4])[0]
    box_type = box_data[4:8]

    if box_type == b"dref":
        version_flags = box_data[8:12]
        entry_count = struct.unpack(">I", box_data[12:16])[0]
        pos = 16
        new_entries = b""
        for _ in range(entry_count):
            if pos + 8 > len(box_data):
                break
            entry_size = struct.unpack(">I", box_data[pos : pos + 4])[0]
            entry_type = box_data[pos + 4 : pos + 8]
            if entry_type == b"url " and entry_size >= 12:
                flags = struct.unpack(">I", box_data[pos + 8 : pos + 12])[0]
                if flags & 0x000001:
                    url_bytes = target_url.encode("utf-8") + b"\x00"
                    new_entry = (
                        struct.pack(">I", 12 + len(url_bytes))
                        + b"url "
                        + b"\x00\x00\x00\x00"
                        + url_bytes
                    )
                    new_entries += new_entry
                else:
                    new_entries += box_data[pos : pos + entry_size]
            else:
                new_entries += box_data[pos : pos + entry_size]
            pos += entry_size
        new_dref_content = (
            version_flags + struct.pack(">I", entry_count) + new_entries
        )
        return (
            struct.pack(">I", 8 + len(new_dref_content)) + b"dref" + new_dref_content
        )

    pos = 8
    result = box_data[:8]
    while pos < size and pos < len(box_data):
        child_size = struct.unpack(">I", box_data[pos : pos + 4])[0]
        if child_size == 0 or pos + child_size > len(box_data):
            break
        child = box_data[pos : pos + child_size]
        modified_child = _set_dref_url(child, target_url)
        result += modified_child
        pos += child_size
    return result


def make_reference_movie(source_path, target_url):
    with open(source_path, "rb") as f:
        data = f.read()

    ftyp_start, ftyp_size = _find_box(data, b"ftyp")
    if ftyp_start is None:
        logger.error("ftyp atom not found in %s", source_path)
        raise ValueError("Invalid .mov file: no ftyp atom")

    moov_start, moov_size = _find_box(data, b"moov")
    if moov_start is None:
        logger.error("moov atom not found in %s", source_path)
        raise ValueError("Invalid .mov file: no moov atom")

    ftyp = data[ftyp_start : ftyp_start + ftyp_size]
    moov = data[moov_start : moov_start + moov_size]

    modified_moov = _set_dref_url(moov, target_url)

    ref_data = ftyp + modified_moov
    logger.info(
        "Reference movie generated: %s → %s (%d bytes)",
        source_path,
        target_url,
        len(ref_data),
    )
    return ref_data
