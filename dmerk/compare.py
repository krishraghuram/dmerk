import collections
import itertools


def _get_digest_to_paths_map(merkle):
    digest_to_paths = collections.defaultdict(list)
    for k, v in merkle.items():
        digest_to_paths[v["_digest"]].append(k)
    return digest_to_paths


def _get_digest_set(merkle):
    return set([v["_digest"] for v in merkle.values()])


def _get_children_merkle(merkle, digest_to_paths, digest_set):
    children_merkle = {}
    for digest in digest_set:
        for path in digest_to_paths[digest]:
            if merkle[path]["_type"] == "directory":
                children_merkle.update(merkle[path]["_children"])
    return children_merkle


def _get_unmatched_merkle(merkle, digest_to_paths, exclusive_digests):
    unmatched_merkle = {}
    for digest in exclusive_digests:
        for path in digest_to_paths[digest]:
            unmatched_merkle.update({path: merkle[path]})
    return unmatched_merkle


def _get_unmatched_files(matching_paths, unmatched_merkle):
    unmatched_files = []
    for k, v in unmatched_merkle.items():
        if v["_type"] == "file":
            # Ensure that unmatched_file k is not already present in matching_paths
            # Also ensure that no parent directory of unmatched file k is present in matching_paths
            if len(set(itertools.chain(k.parents, [k])) & set(matching_paths)) == 0:
                unmatched_files.append(k)
        elif v["_type"] == "directory":
            unmatched_files.extend(_get_unmatched_files(matching_paths, v["_children"]))
    return unmatched_files


def compare(
    merkle_1,
    merkle_2,
    unmatched_parent_merkle_1=None,
    unmatched_parent_merkle_2=None,
    matches=None,
):
    """
    Compare two directory merkle trees and return the matches and diffs
    TODO:
        currently only returning matches, return the diffs also
        (which files/dirs have been created, modified, moved or deleted)
    """
    if unmatched_parent_merkle_1 is None:
        unmatched_parent_merkle_1 = {}
    if unmatched_parent_merkle_2 is None:
        unmatched_parent_merkle_2 = {}
    if matches is None:
        matches = []
    digest_to_paths_1 = _get_digest_to_paths_map(unmatched_parent_merkle_1 | merkle_1)
    digest_to_paths_2 = _get_digest_to_paths_map(unmatched_parent_merkle_2 | merkle_2)
    digest_set_1 = _get_digest_set(unmatched_parent_merkle_1 | merkle_1)
    digest_set_2 = _get_digest_set(unmatched_parent_merkle_2 | merkle_2)
    matching_digests = digest_set_1 & digest_set_2
    exclusive_digests_1 = digest_set_1 - matching_digests
    exclusive_digests_2 = digest_set_2 - matching_digests
    matches.extend(
        [
            (digest_to_paths_1[digest], digest_to_paths_2[digest])
            for digest in matching_digests
        ]
    )
    unmatched_merkle_1 = _get_unmatched_merkle(
        unmatched_parent_merkle_1 | merkle_1, digest_to_paths_1, exclusive_digests_1
    )
    unmatched_merkle_2 = _get_unmatched_merkle(
        unmatched_parent_merkle_2 | merkle_2, digest_to_paths_2, exclusive_digests_2
    )
    children_merkle_1 = _get_children_merkle(
        merkle_1,
        digest_to_paths_1,
        exclusive_digests_1 - _get_digest_set(unmatched_parent_merkle_1),
    )
    children_merkle_2 = _get_children_merkle(
        merkle_2,
        digest_to_paths_2,
        exclusive_digests_2 - _get_digest_set(unmatched_parent_merkle_2),
    )
    if len(children_merkle_1) > 0 and len(children_merkle_2) > 0:
        children_matches, unmatched_files_1, unmatched_files_2 = compare(
            children_merkle_1,
            children_merkle_2,
            unmatched_merkle_1,
            unmatched_merkle_2,
            matches,
        )
        matches.extend(children_matches)
    else:
        # Compute unmatched files only at recursion base case (the lowermost level in the merkle tree traversal)
        # This is because at higher levels, we might have unmatched files, but those could get matched when we go down to lower levels
        unmatched_files_1 = _get_unmatched_files(
            list(itertools.chain(*[match[0] for match in matches])), unmatched_merkle_1
        )
        unmatched_files_2 = _get_unmatched_files(
            list(itertools.chain(*[match[1] for match in matches])), unmatched_merkle_2
        )
    return matches, unmatched_files_1, unmatched_files_2
