from collections import defaultdict
from typing import Any

from .merkle import Merkle


def compare(merkle_1: Merkle, merkle_2: Merkle) -> dict[str, list[Any]]:
    """
    Return the matches and diff between two merkles
    """
    out: dict[str, list[Any]] = {
        "matches": [],
        "unmatched_1": [],
        "unmatched_2": [],
    }
    if merkle_1.digest == merkle_2.digest:
        out["matches"].append(([str(merkle_1.path)], [str(merkle_2.path)]))
    else:
        if hasattr(merkle_1, "children"):
            digest_to_paths_1 = defaultdict(list)
            for sm in merkle_1.children.values():
                digest_to_paths_1[sm.digest].append(sm.path)
            digest_set_1 = set(digest_to_paths_1.keys())
        if hasattr(merkle_2, "children"):
            digest_to_paths_2 = defaultdict(list)
            for sm in merkle_2.children.values():
                digest_to_paths_2[sm.digest].append(sm.path)
            digest_set_2 = set(digest_to_paths_2.keys())

        matching_digests = digest_set_1 & digest_set_2
        for digest in matching_digests:
            out["matches"].append(
                (
                    [str(p) for p in digest_to_paths_1[digest]],
                    [str(p) for p in digest_to_paths_2[digest]],
                )
            )
        unmatched_digests_1 = digest_set_1 - digest_set_2
        for digest in unmatched_digests_1:
            out["unmatched_1"].append([str(p) for p in digest_to_paths_1[digest]])
        unmatched_digests_2 = digest_set_2 - digest_set_1
        for digest in unmatched_digests_2:
            out["unmatched_2"].append([str(p) for p in digest_to_paths_2[digest]])
    return out
