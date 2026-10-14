"""Layer loader for TITAN PRO V78.

Why not plain imports?  The V8..V78 layers deliberately *wrap* module-level names
(analyze_asset, update_cache, v55_desk_snapshot, ...) and read each other through
globals().  Separate module namespaces would silently break that contract, so every
layer file is compiled with its real filename (clean tracebacks) and executed, in
order, into ONE shared namespace.

The loader also records WHICH layer (re)bound each wrapped name, so the V53 / V55 /
V56 / V62 / V78 chains are explicit and inspectable (GET /api/v77/layers + /api/v78/*).
"""
from __future__ import annotations

import __future__ as _fut
import sys
import time
import types
from pathlib import Path

LAYER_ORDER = [
    "core/bootstrap_storage",
    "core/logging_safety_keys",
    "core/defaults_helpers",
    "core/confidence_v8",
    "data/storage_sqlite",
    "data/market_http",
    "decision/technicals_core",
    "decision/neural_synapse_v9",
    "decision/signal_grade_v10",
    "decision/decision_core_v3",
    "decision/ai_layer",
    "analysis/asset_analysis",
    "analysis/professional_edge_suite",
    "analysis/adaptive_intelligence",
    "engine/paper_forecast_metrics",
    "engine/backtest_walkforward",
    "engine/live_engine",
    "engine/cache_command_center",
    "engine/advanced_metrics",
    "engine/performance_snapshot",
    "engine/enterprise_audit_validation",
    "web/flask_app",
    "intel/v10_5_cognitive_nexus",
    "intel/v21_trust_max",
    "intel/v22_opportunity",
    "intel/v29_evidence_fusion",
    "intel/v30_deep_consensus",
    "intel/v31_canonical_decision",
    "intel/v32_performance_learning",
    "web/routes_startup",
    "governors/v29_3_central_governor",
    "governors/v29_5_edge_lab",
    "governors/v31_advanced_edge_suite",
    "governors/v34_adaptive_trust",
    "governors/v35_live_price_levels",
    "governors/v36_quantum_resonance",
    "governors/v40_five_hard_fixes",
    "governors/v42_integrity_seal",
    "governors/v43_unified_evidence",
    "governors/v44_error_learning",
    "governors/v45_validated_decisions",
    "governors/selftest_v35_v36",
    "governors/v46_honest_performance",
    "governors/v47_swing_edge",
    "governors/v48_short_swing_router",
    "governors/v49_short_swing_governor",
    "governors/v60_edge_router",
    "desk/v52_professional_core",
    "desk/v53_decision_dna",
    "desk/v54_replay_telegram",
    "desk/v55_signal_desk",
    "desk/v56_unified_desk",
    "desk/v56_2_governed_learning",
    "ui/v63_glass_v59_skin",
    "ui/v75_deep_coin_analysis",
    "analytics/v61_fast_scan",
    "analytics/v62_full_analytics",
    "analytics/v62_1_quality_patch",
    "analytics/v64_forecast_patterns",
    "analytics/v68_shadow_ledger",
    "analytics/v69_probability_cone",
    "analytics/v70_market_regime",
    "analytics/v71_pattern_validation",
    "platform/v72_pwa",
    "platform/v72_security_backup",
    "unified/v76_unified_pipeline",
    "hardening/v77_security",
    "hardening/v77_trace",
    "hardening/v77_diagnostics",
    "analytics/v78_realistic_forecast",
    "intel/v78_opportunity_funnel",
    "ui/v78_personalization",
    "hardening/v78_evaluation_dashboard",
    "hardening/v78_1_deep_activation",
    "hardening/v79_5_calibration_learning_queue",
    "hardening/v79_6_six_pillars",
    "hardening/v79_7_enterprise_contract",
    "hardening/v79_8_enterprise_infra",
    "hardening/v79_9_service_architecture",
    "hardening/v80_advanced_platform",
    "entry/main_entry",
]

LAYER_DIR = Path(__file__).resolve().parent / "layers"

# Shared namespace every layer executes into.
_NS: dict = {
    "__name__": "titan_runtime",
    "__file__": str(Path(__file__).resolve()),
    "__package__": None,
    "__builtins__": __builtins__,
}
# Honour the same future flags the layer sources declare.
for _f in (
    _fut.annotations,
    getattr(_fut, "generator_stop", None),
    getattr(_fut, "unicode_literals", None),
):
    if _f is not None:
        _NS[_f.__name__] = _f

_LAYER_BINDINGS: dict[str, str] = {}
_LOADED: list[str] = []
_LOAD_MS: dict[str, float] = {}


def _exec_layer(name: str) -> None:
    path = LAYER_DIR / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"TITAN layer missing: {path}")
    src = path.read_text(encoding="utf-8")
    code = compile(src, str(path), "exec")
    before = set(_NS.keys())
    t0 = time.perf_counter()
    exec(code, _NS)
    elapsed = (time.perf_counter() - t0) * 1000.0
    after = set(_NS.keys())
    for k in after - before:
        if not k.startswith("_"):
            _LAYER_BINDINGS[k] = name
    _LOADED.append(name)
    _LOAD_MS[name] = elapsed


def load(runtime_path: str | None = None, as_main: bool = False, stop_before: str | None = None) -> dict:
    """Load every layer into the shared namespace and optionally start the server."""
    global LAYER_DIR
    if runtime_path:
        LAYER_DIR = Path(runtime_path).resolve().parent / "layers"

    t_all = time.perf_counter()
    for name in LAYER_ORDER:
        if stop_before and name == stop_before:
            break
        path = LAYER_DIR / f"{name}.py"
        if not path.is_file():
            raise FileNotFoundError(f"TITAN layer missing: {path}")
        try:
            src = path.read_text(encoding="utf-8")
            code = compile(src, str(path), "exec")
            before = set(_NS.keys())
            t0 = time.perf_counter()
            exec(code, _NS)
            elapsed = (time.perf_counter() - t0) * 1000.0
            after = set(_NS.keys())
            for k in after - before:
                if not k.startswith("_"):
                    _LAYER_BINDINGS[k] = name
            _LOADED.append(name)
            _LOAD_MS[name] = elapsed
        except Exception as exc:
            raise RuntimeError(f"Failed loading layer {name}: {exc}") from exc

    total_ms = (time.perf_counter() - t_all) * 1000.0
    _NS["_TITAN_LAYER_BINDINGS"] = dict(_LAYER_BINDINGS)
    _NS["_TITAN_LOADED_LAYERS"] = list(_LOADED)
    _NS["_TITAN_LOAD_MS"] = dict(_LOAD_MS)
    _NS["_TITAN_LOAD_TOTAL_MS"] = total_ms

    if as_main:
        # Prefer the Flask entry if present
        start = _NS.get("start_server") or _NS.get("main") or _NS.get("run")
        if callable(start):
            start()
        else:
            # Fallback: try waitress / flask app object
            app = _NS.get("app")
            if app is not None:
                host = __import__("os").environ.get("TITAN_HOST", "127.0.0.1")
                port = int(__import__("os").environ.get("TITAN_PORT", "8080"))
                try:
                    from waitress import serve
                    serve(app, host=host, port=port)
                except Exception:
                    app.run(host=host, port=port, threaded=True, use_reloader=False)
    return _NS


if __name__ == "__main__":
    load(as_main=True)
