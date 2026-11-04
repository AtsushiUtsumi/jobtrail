from jobtrail.schemas.common import EmptyInput, PingOutput
from jobtrail.usecase.context import AppContext


def ping(ctx: AppContext, data: EmptyInput) -> PingOutput:
    """接続確認。DB まで疎通していれば status=ok を返す。"""
    with ctx.uow_factory() as uow:
        uow.check_connection()
    return PingOutput(status="ok", version="0.1.0")
