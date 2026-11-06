"""テーブル定義と imperative mapping。domain は SQLAlchemy を知らない。"""

from dataclasses import asdict
from enum import Enum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import registry, relationship

from jobtrail.domain.application.application import Application
from jobtrail.domain.application.job_posting import JobPostingSnapshot
from jobtrail.domain.application.stage import Stage, StageResult, StageType
from jobtrail.domain.application.value_objects import ApplicationChannel, Outcome, SalaryRange
from jobtrail.domain.company.company import Company
from jobtrail.domain.company.company_source import AcquiredBy, CompanySource, SourceType
from jobtrail.domain.document.document import Document, DocumentKind, DocumentVersion
from jobtrail.domain.skill_profile.submission import Submission, SubmissionKind

mapper_registry = registry(
    metadata=sa.MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
)
metadata = mapper_registry.metadata

Timestamptz = sa.DateTime(timezone=True)


def _enum(enum_type: type[Enum]) -> sa.Enum:
    return sa.Enum(
        enum_type,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
    )


class SalaryRangeType(sa.types.TypeDecorator[SalaryRange]):
    impl = JSONB
    cache_ok = True

    def process_bind_param(
        self, value: SalaryRange | None, dialect: sa.Dialect
    ) -> dict[str, Any] | None:
        return asdict(value) if value is not None else None

    def process_result_value(
        self, value: dict[str, Any] | None, dialect: sa.Dialect
    ) -> SalaryRange | None:
        return SalaryRange(**value) if value is not None else None


companies = sa.Table(
    "companies",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("normalized_name", sa.Text, nullable=False),
    sa.Column("url", sa.Text),
    sa.Column("normalized_url", sa.Text),
    sa.Column("memo", sa.Text, nullable=False),
    sa.Column("created_at", Timestamptz, nullable=False),
    sa.Column("updated_at", Timestamptz, nullable=False),
    sa.Column("deleted_at", Timestamptz),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Index(
        "ux_companies_normalized_name",
        "normalized_name",
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    ),
    sa.Index(
        "ux_companies_normalized_url",
        "normalized_url",
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND normalized_url IS NOT NULL"),
    ),
)

company_sources = sa.Table(
    "company_sources",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("company_id", sa.Uuid, sa.ForeignKey("companies.id"), nullable=False),
    sa.Column("source_type", _enum(SourceType), nullable=False),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("fetched_at", Timestamptz, nullable=False),
    sa.Column("content_hash", sa.String(64), nullable=False),
    sa.Column("raw_text", sa.Text, nullable=False),
    sa.Column("summary", sa.Text, nullable=False),
    sa.Column("extracted_fields", JSONB, nullable=False),
    sa.Column("acquired_by", _enum(AcquiredBy), nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.UniqueConstraint("company_id", "url", "revision"),
)

applications = sa.Table(
    "applications",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("company_id", sa.Uuid, sa.ForeignKey("companies.id"), nullable=False, index=True),
    sa.Column("position", sa.Text, nullable=False),
    sa.Column("channel", _enum(ApplicationChannel), nullable=False),
    sa.Column("agent_name", sa.Text),
    sa.Column("applied_at", Timestamptz),
    sa.Column("outcome", _enum(Outcome), nullable=False),
    sa.Column("submitted_document_version_id", sa.Uuid, sa.ForeignKey("document_versions.id")),
    sa.Column("priority", sa.Integer, nullable=False),
    sa.Column("memo", sa.Text, nullable=False),
    sa.Column("created_at", Timestamptz, nullable=False),
    sa.Column("updated_at", Timestamptz, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
)

stages = sa.Table(
    "stages",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("application_id", sa.Uuid, sa.ForeignKey("applications.id"), nullable=False),
    sa.Column("position", sa.Integer, nullable=False),
    sa.Column("type", _enum(StageType), nullable=False),
    sa.Column("label", sa.Text),
    sa.Column("scheduled_at", Timestamptz),
    sa.Column("result", _enum(StageResult), nullable=False),
    sa.Column("memo", sa.Text, nullable=False),
    sa.Column("created_at", Timestamptz, nullable=False),
    sa.Column("result_recorded_at", Timestamptz),
    sa.UniqueConstraint("application_id", "position"),
)

job_postings = sa.Table(
    "job_postings",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("application_id", sa.Uuid, sa.ForeignKey("applications.id"), nullable=False),
    sa.Column("url", sa.Text),
    sa.Column("fetched_at", Timestamptz, nullable=False),
    sa.Column("content_hash", sa.String(64), nullable=False),
    sa.Column("raw_text", sa.Text, nullable=False),
    sa.Column("summary", sa.Text, nullable=False),
    sa.Column("salary_range", SalaryRangeType),
    sa.Column("location", sa.Text),
    sa.Column("employment_type", sa.Text),
    sa.Column("remote_policy", sa.Text),
    sa.Column("tech_stack", JSONB, nullable=False),
    sa.Column("required", JSONB, nullable=False),
    sa.Column("preferred", JSONB, nullable=False),
    sa.Column("extra", JSONB, nullable=False),
    sa.Column("acquired_by", _enum(AcquiredBy), nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.UniqueConstraint("application_id", "revision"),
)

documents = sa.Table(
    "documents",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("kind", _enum(DocumentKind), nullable=False),
    sa.Column("created_at", Timestamptz, nullable=False),
)

document_versions = sa.Table(
    "document_versions",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("document_id", sa.Uuid, sa.ForeignKey("documents.id"), nullable=False),
    sa.Column("number", sa.Integer, nullable=False),
    sa.Column("body", sa.Text, nullable=False),
    sa.Column("created_at", Timestamptz, nullable=False),
    sa.Column("note", sa.Text, nullable=False),
    sa.UniqueConstraint("document_id", "number"),
)

skill_profiles = sa.Table(
    "skill_profiles",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("data", JSONB, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("updated_at", Timestamptz),
)

submissions = sa.Table(
    "submissions",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True),
    sa.Column("application_id", sa.Uuid, sa.ForeignKey("applications.id"), nullable=False),
    sa.Column("submitted_at", Timestamptz, nullable=False),
    sa.Column("kind", _enum(SubmissionKind), nullable=False),
    sa.Column("template_file_name", sa.Text),
    sa.Column("received_at", Timestamptz),
    sa.Column("snapshot", JSONB, nullable=False),
    sa.Column("document_version_id", sa.Uuid, sa.ForeignKey("document_versions.id")),
    sa.Column("memo", sa.Text, nullable=False),
)

_mapped = False


def start_mappers() -> None:
    global _mapped
    if _mapped:
        return
    _mapped = True
    mapper_registry.map_imperatively(Company, companies, version_id_col=companies.c.version)
    mapper_registry.map_imperatively(CompanySource, company_sources)
    mapper_registry.map_imperatively(Stage, stages)
    mapper_registry.map_imperatively(
        Application,
        applications,
        version_id_col=applications.c.version,
        properties={
            "stages": relationship(
                Stage,
                order_by=stages.c.position,
                cascade="all, delete-orphan",
                lazy="selectin",
            )
        },
    )
    mapper_registry.map_imperatively(JobPostingSnapshot, job_postings)
    mapper_registry.map_imperatively(DocumentVersion, document_versions)
    mapper_registry.map_imperatively(
        Document,
        documents,
        properties={
            "versions": relationship(
                DocumentVersion,
                order_by=document_versions.c.number,
                cascade="all, delete-orphan",
                lazy="selectin",
            )
        },
    )
    mapper_registry.map_imperatively(Submission, submissions)
