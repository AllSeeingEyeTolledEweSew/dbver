# Copyright (c) 2022 AllSeeingEyeTolledEweSew
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.


import pytest

import dbver


@pytest.mark.parametrize(
    ("from_version", "to_version", "breaking"),
    (
        # upgrades from zero are nonbreaking
        (0, 2_000_000, False),
        (0, 0, False),
        # backwards changes are breaking
        (2_000_000, 0, True),
        (1_001_000, 1_000_000, True),
        # forward major changes are breaking
        (1_000_000, 2_000_000, True),
        (1_999_999, 2_000_000, True),
        # forward minor/patch changes are nonbreaking
        (1_000_000, 1_000_001, False),
        (1_000_000, 1_001_000, False),
        (1_000_000, 1_999_999, False),
    ),
)
def test_breaking(from_version: int, to_version: int, breaking: bool) -> None:
    assert dbver.semver_is_breaking(from_version, to_version) is breaking
    if breaking:
        with pytest.raises(dbver.VersionError):
            dbver.semver_check_breaking(from_version, to_version)
    else:
        dbver.semver_check_breaking(from_version, to_version)
