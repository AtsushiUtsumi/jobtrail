"""MCP ツールの説明に足す、Claude 向けの使い方の指針。"""

from jobtrail.usecase.registry import UseCase

SERVER_INSTRUCTIONS = """\
jobtrail は転職活動のデータを保持するサーバーです。要約・抽出・Web 取得は Claude 側で行い、
結果を保存してください。ID が分からないときは find_companies / find_applications / list_documents
で名前から特定します。日時はタイムゾーン付きの ISO 8601 で渡してください。
エラーは code / message / hint / details の JSON で返るので、hint に従って修正し再試行してください。
"""

GUIDANCE: dict[str, str] = {
    "register_company": "登録前に必ず find_companies で既存の企業を検索してください。",
    "find_companies": "社名から company_id を解決するために使います。",
    "find_applications": "志望度順に見るときは sort=priority_desc を指定します。",
    "get_pipeline": "各列を志望度順に見るときは sort=priority_desc を指定します。",
    "add_application": (
        "先に find_companies で検索し、見つかれば company_id を、"
        "見つからなければ new_company を渡してください。"
        "DUPLICATE_COMPANY が返ったら details.existing_id を company_id に使います。"
    ),
    "apply": "求人を保存しただけの段階は検討中です。実際に応募した時点で呼びます。",
    "advance_stage": "直前の Stage の結果が未確定なら、先に record_stage_result を呼びます。",
    "record_stage_result": "memo も同時に残せます。不合格・辞退の後は Stage を編集できません。",
    "close_application": "見送り（passed_over）は検討中の応募にのみ指定できます。",
    "save_company_source": (
        "raw_text は事実、summary は解釈として分けて保存します。"
        "口コミ・評判は source_type=review とし、他の種別の要約に混ぜないでください。"
        "本文が大きすぎる場合は分割して保存します。"
    ),
    "save_job_posting": "応募が無ければ先に add_application で検討中の応募を作ります。",
    "import_skill_profile": "既存のスキルシートを読み取り、構造化して渡してください。",
    "record_submission": (
        "Excel などの様式への記入は Claude 側で行い、提出した事実と内容だけをここに記録します。"
        "匿名化して提出した場合は、提出した内容を snapshot に渡します。"
    ),
    "get_skill_profile": (
        "disclosure が private の案件は社外の提出物に使わないでください。"
        "anonymized は anonymized_name で表記します。"
    ),
    "update_stage_memo": "面接で聞かれたことはここに記録します。終了した応募では使えません。",
}


def describe(use_case: UseCase) -> str:
    guidance = GUIDANCE.get(use_case.name)
    return f"{use_case.description}\n\n{guidance}" if guidance else use_case.description
