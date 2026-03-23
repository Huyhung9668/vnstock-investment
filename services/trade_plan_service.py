from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.analysis_package import AnalysisPackage


DictStrAny = dict[str, Any]


@dataclass(slots=True)
class ScenarioBlock:
    title: str
    confidence: str
    confirmation_conditions: list[str]
    observation_triggers: list[str]
    invalidation_points: list[str]
    risks: list[str]


def render_trade_plan(package: AnalysisPackage) -> str:
    confidence = _derive_confidence(package)
    scenarios = _build_scenarios(package, confidence)

    sections = [
        _render_title(package),
        _render_input_summary(package, confidence),
        _render_data_quality(package, confidence),
        _render_scenario_section("Scenario 1: Tich cuc", scenarios[0]),
        _render_scenario_section("Scenario 2: Trung tinh", scenarios[1]),
        _render_scenario_section("Scenario 3: Tieu cuc", scenarios[2]),
        _render_missing_data_warnings(package),
        _render_conclusion(package, confidence),
    ]
    return "\n\n".join(sections).strip() + "\n"


def _render_title(package: AnalysisPackage) -> str:
    provider_name = _stringify(package.provider_metadata.get("provider_name"), default="unknown")
    generated_at = _format_datetime(package.generated_at)
    return "\n".join(
        [
            f"# Trade Plan: {package.symbol}",
            f"- Nguon du lieu: `{provider_name}`",
            f"- Thoi gian tao: `{generated_at}`",
        ]
    )


def _render_input_summary(package: AnalysisPackage, confidence: str) -> str:
    company_name = _stringify(
        package.company.get("name")
        or package.company.get("company_name")
        or package.company.get("short_name"),
        default="Chua co ten doanh nghiep",
    )
    company_lines = _format_key_value_lines(package.company, limit=4)
    price_lines = _format_key_value_lines(package.price_summary, limit=5)
    financial_state = _describe_optional_section("financial_summary", package.financial_summary)
    news_state = _describe_optional_section("news_summary", package.news_summary)
    breadth_state = _describe_optional_section("breadth_context", package.breadth_context)
    signal_lines = _format_dict_or_empty(package.signals, empty_message="Khong co signal cau truc duoc cung cap.")
    risk_lines = _format_dict_or_empty(package.risks, empty_message="Khong co risk cau truc duoc cung cap.")

    lines = [
        "## Tom tat du lieu dau vao",
        f"- Ma co phieu: `{package.symbol}`",
        f"- Doanh nghiep: {company_name}",
        f"- Muc do tin cay ban dau: **{confidence}**",
        f"- Financial summary: {financial_state}",
        f"- News summary: {news_state}",
        f"- Breadth context: {breadth_state}",
        "",
        "### Company Snapshot",
        *company_lines,
        "",
        "### Price Snapshot",
        *price_lines,
        "",
        "### Signals",
        *signal_lines,
        "",
        "### Risks Input",
        *risk_lines,
    ]
    return "\n".join(lines)


def _render_data_quality(package: AnalysisPackage, confidence: str) -> str:
    sections_quality = _extract_sections_quality(package.data_quality)
    quality_lines = _format_section_quality_lines(sections_quality)
    missing_text = _format_missing_sections_inline(package.missing_sections)

    lines = [
        "## Danh gia chat luong du lieu",
        f"- Muc do tin cay tong hop: **{confidence}**",
        f"- So section thieu: `{len(package.missing_sections)}`",
        f"- Section thieu: {missing_text}",
    ]

    provider_health = package.data_quality.get("provider_health")
    if isinstance(provider_health, dict):
        health_status = _stringify(provider_health.get("status"), default="unknown")
        lines.append(f"- Provider health: `{health_status}`")
        health_details = _format_key_value_lines(provider_health, limit=4, skip_keys={"status"})
        if health_details != ["- Khong co du lieu."]:
            lines.extend(health_details)

    lines.extend(
        [
            "",
            "### Section Quality",
            *quality_lines,
        ]
    )
    return "\n".join(lines)


def _render_scenario_section(header: str, scenario: ScenarioBlock) -> str:
    lines = [
        f"## {header}",
        f"- Muc do tin cay kich ban: **{scenario.confidence}**",
        "",
        "### Dieu kien xac nhan",
        *_render_bullets(scenario.confirmation_conditions),
        "",
        "### Trigger quan sat",
        *_render_bullets(scenario.observation_triggers),
        "",
        "### Invalidation",
        *_render_bullets(scenario.invalidation_points),
        "",
        "### Rui ro",
        *_render_bullets(scenario.risks),
    ]
    return "\n".join(lines)


def _render_missing_data_warnings(package: AnalysisPackage) -> str:
    warnings = _build_missing_data_warnings(package)
    lines = [
        "## Canh bao thieu du lieu",
        *_render_bullets(warnings),
    ]
    return "\n".join(lines)


def _render_conclusion(package: AnalysisPackage, confidence: str) -> str:
    company_name = _stringify(
        package.company.get("name")
        or package.company.get("company_name")
        or package.company.get("short_name"),
        default=package.symbol,
    )
    conclusion_lines = [
        f"- Trade plan cho `{package.symbol}` ({company_name}) duoc xay dung tren structured data hien co va dang o muc do tin cay **{confidence}**.",
        "- Uu tien theo doi cac dieu kien xac nhan va trigger quan sat truoc khi nang muc do cam ket trong ke hoach.",
        "- Neu xuat hien du lieu tai chinh, tin tuc, hoac breadth day du hon, nen cap nhat lai danh gia de giam do lech do du lieu thieu.",
        "- Day la tai lieu tham khao phan tich tinh huong, khong phai khang dinh hanh dong tai chinh tuyet doi.",
    ]
    return "\n".join(["## Ket luan trung lap", *conclusion_lines])


def _build_scenarios(package: AnalysisPackage, confidence: str) -> list[ScenarioBlock]:
    signal_items = _summarize_dict_items(package.signals, fallback="Khong co signal cau truc de ho tro xac nhan.")
    risk_items = _summarize_dict_items(package.risks, fallback="Khong co risk cau truc bo sung.")
    breadth_note = _breadth_confirmation_note(package)
    missing_note = _missing_data_note(package)

    positive = ScenarioBlock(
        title="Tich cuc",
        confidence=confidence,
        confirmation_conditions=[
            _combine_text(
                "Gia va price summary duy tri cau truc on dinh hoac cai thien so voi du lieu hien co.",
                signal_items[0],
            ),
            _combine_text(
                "Signals neu co tiep tuc cung co cho huong di tich cuc thay vi suy yeu ngan han.",
                breadth_note,
            ),
            missing_note,
        ],
        observation_triggers=[
            "Theo doi thay doi trong price_summary, dac biet cac muc dong cua, bien dong, thanh khoan hoac cac cot moc duoc cung cap.",
            "Quan sat xem co them xac nhan tu tin tuc, tai chinh, hoac breadth de tang do chat che cua kich ban.",
            signal_items[1],
        ],
        invalidation_points=[
            "Kich ban tich cuc mat hieu luc neu du lieu gia moi cho thay suy yeu ro rang so voi tong quan hien tai.",
            "Signals chuyen tu trang thai ho tro sang mau thuan voi nhan dinh tich cuc.",
            risk_items[0],
        ],
        risks=[
            risk_items[0],
            risk_items[1],
            "Neu thieu breadth confirmation, do lan toa cua nhan dinh tich cuc co the khong duoc xac nhan boi thi truong rong hon.",
        ],
    )

    neutral = ScenarioBlock(
        title="Trung tinh",
        confidence=confidence,
        confirmation_conditions=[
            "Gia van dao dong trong vung chua cho thay su mo rong xu huong ro rang.",
            "Signals khong dong thuan manh theo mot huong cu the, hoac don gian la dang trong trang thai trung lap.",
            _combine_text("Khong co thay doi lon tu cac du lieu bo sung.", missing_note),
        ],
        observation_triggers=[
            "Theo doi su thay doi cua price summary de phat hien kha nang chuyen sang kich ban tich cuc hoac tieu cuc.",
            "Quan sat xem data_quality co duoc cai thien hay khong khi bo sung financial, news, breadth.",
            breadth_note,
        ],
        invalidation_points=[
            "Kich ban trung tinh khong con phu hop neu gia thoat ra khoi trang thai can bang mot cach ro rang.",
            "Tin tuc moi, tai chinh moi, hoac bien dong breadth lam thay doi nen xac suat cua cac kich ban con lai.",
            risk_items[0],
        ],
        risks=[
            "Trang thai trung tinh de bi pha vo khi thong tin moi xuat hien trong luc du lieu nen con thieu.",
            risk_items[1],
            "Neu confidence thap, kich ban trung tinh chi nen duoc xem la vung cho xac nhan them.",
        ],
    )

    negative = ScenarioBlock(
        title="Tieu cuc",
        confidence=confidence,
        confirmation_conditions=[
            "Price summary moi cho thay dau hieu suy yeu tiep dien, mat can bang, hoac thanh khoan khong ho tro.",
            "Signals neu co chuyen sang trang thai canh bao hoac khong con ho tro cho ky vong tich cuc.",
            _combine_text("Risk factors bat dau duoc xac nhan boi du lieu moi.", breadth_note),
        ],
        observation_triggers=[
            "Theo doi cac cap nhat gia de xem ap luc giam co tiep tuc duoc duy tri hay chi la nhieu dong ngau nhien.",
            "Quan sat xem news summary co xuat hien thong tin bat loi hoac tai chinh bo sung lam xau di bo canh.",
            risk_items[0],
        ],
        invalidation_points=[
            "Kich ban tieu cuc bi suy yeu neu du lieu gia nhanh chong hoi phuc va co xac nhan tu signal hoac breadth.",
            "Tin tuc va du lieu bo sung sau do cho thay ap luc hien tai chi mang tinh ngan han.",
            missing_note,
        ],
        risks=[
            "Du lieu thieu co the lam phong dai nhan dinh tieu cuc neu chua co xac nhan cheo.",
            risk_items[0],
            risk_items[1],
        ],
    )

    return [positive, neutral, negative]


def _derive_confidence(package: AnalysisPackage) -> str:
    penalty = 0
    missing_count = len(package.missing_sections)
    penalty += missing_count

    sections_quality = _extract_sections_quality(package.data_quality)
    for quality in sections_quality.values():
        status = _stringify(quality.get("status"), default="unknown").lower()
        if status == "error":
            penalty += 2
        elif status == "missing":
            penalty += 1

    provider_health = package.data_quality.get("provider_health")
    if isinstance(provider_health, dict):
        provider_status = _stringify(provider_health.get("status"), default="unknown").lower()
        if provider_status not in {"ok", "healthy", "ready"}:
            penalty += 1

    if penalty >= 5:
        return "Thap"
    if penalty >= 2:
        return "Trung binh"
    return "Trung binh cao"


def _extract_sections_quality(data_quality: DictStrAny) -> dict[str, DictStrAny]:
    raw_sections = data_quality.get("sections")
    if not isinstance(raw_sections, dict):
        return {}

    normalized: dict[str, DictStrAny] = {}
    for key in sorted(raw_sections):
        value = raw_sections.get(key)
        if isinstance(value, dict):
            normalized[key] = dict(value)
    return normalized


def _format_section_quality_lines(sections_quality: dict[str, DictStrAny]) -> list[str]:
    if not sections_quality:
        return ["- Khong co thong tin data_quality chi tiet."]

    lines: list[str] = []
    for section_name in sorted(sections_quality):
        quality = sections_quality[section_name]
        status = _stringify(quality.get("status"), default="unknown")
        present = _stringify(quality.get("present"), default="unknown")
        parts = [f"- `{section_name}`: status=`{status}`, present=`{present}`"]

        error_type = quality.get("error_type")
        if error_type is not None:
            parts.append(f"error_type=`{_stringify(error_type, default='unknown')}`")

        record_count = quality.get("record_count")
        if record_count is not None:
            parts.append(f"record_count=`{_stringify(record_count, default='0')}`")

        lines.append(", ".join(parts))
    return lines


def _build_missing_data_warnings(package: AnalysisPackage) -> list[str]:
    warnings: list[str] = []

    if package.missing_sections:
        warnings.append(
            f"Ke hoach hien tai dang duoc xay dung voi du lieu chua day du. Section thieu: {_format_missing_sections_inline(package.missing_sections)}."
        )
    else:
        warnings.append("Khong ghi nhan section thieu bat buoc trong goi du lieu hien tai.")

    if "financial_summary" in package.missing_sections:
        warnings.append("Thieu `financial_summary`, vi vay danh gia suc khoe nen tang doanh nghiep chua day du.")
    if "news_summary" in package.missing_sections:
        warnings.append("Thieu `news_summary`, vi vay rui ro su kien va tin tuc ngan han chua duoc phan anh day du.")
    if "breadth_context" in package.missing_sections:
        warnings.append("Thieu `breadth_context`, vi vay chua co breadth confirmation cho boi canh thi truong rong hon.")

    if not package.signals:
        warnings.append("`signals` dang trong, do do phan xac nhan theo huong ky thuat hoac tong hop hien con han che.")
    if not package.risks:
        warnings.append("`risks` dang trong, do do can tiep tuc bo sung danh sach rui ro cu the de can bang goc nhin.")

    return warnings


def _describe_optional_section(section_name: str, value: DictStrAny | None) -> str:
    if value is None:
        return f"thieu ({section_name})"
    if not value:
        return f"co nhung rong ({section_name})"
    return f"co du lieu ({section_name})"


def _breadth_confirmation_note(package: AnalysisPackage) -> str:
    if package.breadth_context:
        return "Breadth context dang co mat, co the dung de doi chieu do lan toa neu cac cap nhat sau tiep tuc dong thuan."
    return "Hien thieu breadth confirmation, can than trong khi dien giai suc manh cua kich ban."


def _missing_data_note(package: AnalysisPackage) -> str:
    if not package.missing_sections:
        return "Bo du lieu hien tai khong ghi nhan section thieu."
    missing_text = _format_missing_sections_inline(package.missing_sections)
    return f"Ke hoach nay dang dua tren bo du lieu chua day du: {missing_text}."


def _format_missing_sections_inline(missing_sections: list[str]) -> str:
    if not missing_sections:
        return "khong co"
    return ", ".join(f"`{item}`" for item in sorted(set(missing_sections)))


def _format_key_value_lines(
    payload: DictStrAny,
    *,
    limit: int,
    skip_keys: set[str] | None = None,
) -> list[str]:
    if not payload:
        return ["- Khong co du lieu."]

    excluded = skip_keys or set()
    lines: list[str] = []
    for key in sorted(payload):
        if key in excluded:
            continue
        value = payload[key]
        lines.append(f"- `{key}`: {_format_scalar(value)}")
        if len(lines) >= limit:
            break

    return lines or ["- Khong co du lieu."]


def _format_dict_or_empty(payload: DictStrAny, *, empty_message: str) -> list[str]:
    if not payload:
        return [f"- {empty_message}"]
    return [f"- `{key}`: {_format_scalar(payload[key])}" for key in sorted(payload)]


def _summarize_dict_items(payload: DictStrAny, *, fallback: str) -> list[str]:
    if not payload:
        return [fallback, fallback]

    items = [f"`{key}`={_format_scalar(payload[key])}" for key in sorted(payload)]
    if len(items) == 1:
        return [f"Tin hieu/noi dung hien co: {items[0]}.", f"Tiep tuc theo doi {items[0]}."]
    return [
        f"Tin hieu/noi dung hien co: {items[0]}; {items[1]}.",
        f"Tiep tuc theo doi cac bien: {items[0]}; {items[1]}.",
    ]


def _render_bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _combine_text(left: str, right: str) -> str:
    return f"{left} {right}".strip()


def _format_datetime(value: datetime) -> str:
    return value.isoformat()


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, (int, str)):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return ", ".join(_format_scalar(item) for item in value[:4]) or "[]"
    if isinstance(value, dict):
        keys = ", ".join(sorted(str(key) for key in value.keys())[:4])
        return f"dict({keys})" if keys else "dict()"
    return str(value)


def _stringify(value: Any, *, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip()
        return text if text else default
    return str(value)
