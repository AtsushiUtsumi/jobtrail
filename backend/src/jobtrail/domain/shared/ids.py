"""集約をまたぐ参照に使う ID。"""

from uuid import UUID, uuid4

type CompanyId = UUID
type CompanySourceId = UUID
type ApplicationId = UUID
type StageId = UUID
type JobPostingId = UUID
type DocumentId = UUID
type DocumentVersionId = UUID
type SubmissionId = UUID


def new_id() -> UUID:
    return uuid4()
