from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobtrail.domain.application.job_posting import JobPostingSnapshot
from jobtrail.domain.company.company import Company
from jobtrail.domain.company.company_source import AcquiredBy, CompanySource, SourceType
from jobtrail.domain.shared.errors import (
    ConflictError,
    ContentTooLargeError,
    DomainError,
    check_version,
)
from jobtrail.domain.shared.value_objects import (
    content_hash,
    ensure_text_size,
    normalize_company_name,
    normalize_url,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("株式会社アクメ", "アクメ"),
        ("アクメ株式会社", "(株)アクメ"),
        ("ＡＣＭＥ　Inc", "acme inc"),
    ],
)
def test_company_names_are_normalized(left: str, right: str) -> None:
    assert normalize_company_name(left) == normalize_company_name(right)


def test_url_normalization_ignores_case_slash_and_fragment() -> None:
    assert normalize_url("HTTPS://Example.com/jobs/#top") == "https://example.com/jobs"


def test_query_is_kept_in_url() -> None:
    assert normalize_url("https://example.com/a?page=2") == "https://example.com/a?page=2"


def test_text_size_limit() -> None:
    ensure_text_size("a" * 10, 10)
    with pytest.raises(ContentTooLargeError) as info:
        ensure_text_size("a" * 11, 10)
    assert info.value.details == {"actual": 11, "limit": 10}
    assert "分割" in info.value.hint


def test_check_version() -> None:
    check_version(3, None)
    check_version(3, 3)
    with pytest.raises(ConflictError) as info:
        check_version(3, 2)
    assert info.value.details["current_version"] == 3


def company() -> Company:
    return Company.register("株式会社アクメ", "https://acme.example/", 3, "", NOW)


def test_delete_and_restore() -> None:
    target = company()
    target.delete(NOW)
    assert target.is_deleted
    target.restore(NOW)
    assert not target.is_deleted


def test_deleted_company_cannot_be_updated_or_deleted_again() -> None:
    target = company()
    target.delete(NOW)
    for action in (lambda: target.update(NOW, memo="x"), lambda: target.delete(NOW)):
        with pytest.raises(DomainError) as info:
            action()
        assert info.value.code == "COMPANY_DELETED"


def test_restore_requires_deleted() -> None:
    with pytest.raises(DomainError) as info:
        company().restore(NOW)
    assert info.value.code == "COMPANY_NOT_DELETED"


def test_update_renormalizes_name_and_url() -> None:
    target = company()
    target.update(NOW, name="有限会社ベータ", url=None)
    assert target.normalized_name == "ベータ"
    assert target.normalized_url is None


def test_source_revision_increments_from_previous() -> None:
    first = CompanySource.capture(
        uuid4(), SourceType.ABOUT, "u", "本文", "", {}, AcquiredBy.USER_PASTE, NOW, None
    )
    second = CompanySource.capture(
        uuid4(), SourceType.ABOUT, "u", "本文2", "", {}, AcquiredBy.USER_PASTE, NOW, first
    )
    assert (first.revision, second.revision) == (1, 2)
    assert first.is_same_content("本文")
    assert not first.is_same_content("本文2")
    assert first.content_hash == content_hash("本文")


def test_job_posting_revision_and_summary() -> None:
    first = JobPostingSnapshot.capture(uuid4(), None, "本文", NOW, None, summary="")
    second = JobPostingSnapshot.capture(uuid4(), None, "変更", NOW, first, summary="")
    assert second.revision == 2
    first.update_summary("要約")
    assert first.summary == "要約"
    assert first.raw_text == "本文"
